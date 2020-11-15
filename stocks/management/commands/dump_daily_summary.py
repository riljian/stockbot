import datetime
import logging
from uuid import uuid4
from typing import Sequence, Tuple, Mapping, Set, Optional
from functools import reduce

from django.db import models
from django.core.management.base import BaseCommand, CommandError

import numpy as np
import pandas as pd
from caseconverter import pascalcase
from trading_calendars import get_calendar

from stocks.models import Exchange, Stock, DailySummary
import stocks.helpers.crawler as crawlers


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    EXCHANGE_KEY = 'exchange'
    DATE_KEY = 'date'
    FROM_KEY = 'from'
    TO_KEY = 'to'
    TIMEOUT = 15

    help = 'Dump daily summary of a exchange'

    def add_arguments(self, parser):
        exchange_choices = [
            exchange.code for exchange in Exchange.objects.all()
        ]
        parser.add_argument(f'--{self.EXCHANGE_KEY}',
                            required=True, choices=exchange_choices)
        parser.add_argument(f'--{self.DATE_KEY}')
        parser.add_argument(f'--{self.FROM_KEY}')
        parser.add_argument(f'--{self.TO_KEY}')

    @staticmethod
    def parse_date(value: str) -> datetime.date:
        if value:
            try:
                return datetime.datetime.strptime(value, '%Y%m%d')
            except Exception as ex:
                raise CommandError('invalid date') from ex
        else:
            return datetime.date.today()

    @staticmethod
    def parse_exchange(value: str) -> Tuple[Exchange, crawlers.ExchangeCrawler]:
        crawler = getattr(crawlers, pascalcase(f'{value} crawler'))

        if crawler is None:
            raise CommandError('crawler not found')

        return Exchange.objects.get(code=value), crawler

    @staticmethod
    def fill_missing_stock(exchange: Exchange, stock_codes: Sequence[str]) -> None:
        existing_stock_codes = (Stock.objects
                                .filter(exchange=exchange, code__in=stock_codes)
                                .values_list('code', flat=True))

        missing_codes = set(stock_codes) - set(existing_stock_codes)
        if len(missing_codes) > 0:
            missing_stocks = map(
                lambda code: Stock(id=uuid4(), exchange=exchange, code=code), missing_codes)
            Stock.objects.bulk_create(missing_stocks)

    @staticmethod
    def get_stock_map(exchange: Exchange, stock_codes: Sequence[str]) -> Mapping[str, Stock]:
        return reduce(
            lambda acc, stock: {**acc, stock.code: stock},
            Stock.objects.filter(exchange=exchange, code__in=stock_codes),
            {}
        )

    @staticmethod
    def get_summary_existing_codes(exchange: Exchange, date: datetime.date) -> Set[str]:
        codes = (DailySummary.objects
                 .filter(
                     stock__exchange=exchange,
                     date=date,
                 )
                 .annotate(code=models.F('stock__code'))
                 .values_list('code', flat=True))
        return set(codes)

    @staticmethod
    def trans_summary_df_to_dict(exchange_summary_df: pd.DataFrame) -> dict:
        exchange_summary_dict = exchange_summary_df.to_dict(orient='index')

        def replace_nan_by_none(value):
            return None if np.isnan(value) else value

        def purify(stock_summary_dict):
            return {
                key: replace_nan_by_none(stock_summary_dict[key]) for key in stock_summary_dict
            }

        return {
            code: purify(exchange_summary_dict[code]) for code in exchange_summary_dict
        }

    @classmethod
    def dump_daily_summary(cls, exchange_code: str, date_text: Optional[str] = None) -> bool:
        exchange, crawler = cls.parse_exchange(exchange_code)
        date = cls.parse_date(date_text)

        if date not in get_calendar(exchange.calendar_code).opens:
            logger.info('%s: skipped', date_text)
            return True

        try:
            daily_exchange_summary_df = crawler.get_daily_summary(date)
            daily_exchange_summary = \
                cls.trans_summary_df_to_dict(daily_exchange_summary_df)
            stock_codes = daily_exchange_summary.keys()
            cls.fill_missing_stock(exchange, stock_codes)
            stock_map = cls.get_stock_map(exchange, stock_codes)
            summary_existing_codes = \
                cls.get_summary_existing_codes(exchange, date)

            summaries = []
            for code in set(stock_codes) - summary_existing_codes:
                daily_stock_summary = daily_exchange_summary[code]
                stock = stock_map[code]
                summaries.append(DailySummary(
                    id=uuid4(),
                    date=date,
                    stock=stock,
                    **daily_stock_summary,
                ))
            DailySummary.objects.bulk_create(summaries)

            logger.info('%s: success', date_text)
            return False
        except Exception:  # pylint: disable=broad-except
            logger.exception('%s: failed', date_text)
            return False

    def handle(self, *args, **options):
        exchange_code = options[self.EXCHANGE_KEY]
        date_text = options.get(self.DATE_KEY, None)
        from_date_text = options.get(self.FROM_KEY, None)
        to_date_text = options.get(self.TO_KEY, None)

        if from_date_text and to_date_text:
            for date in pd.date_range(from_date_text, to_date_text):
                date_text = date.strftime('%Y%m%d')
                skipped = self.dump_daily_summary(exchange_code, date_text)
                if not skipped:
                    # time.sleep(self.TIMEOUT)
                    # storing data into database costs 50 seconds
                    pass
        else:
            self.dump_daily_summary(exchange_code, date_text)
