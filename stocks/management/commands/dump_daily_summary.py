import datetime
import logging
from uuid import uuid4
from typing import Sequence, Mapping, Set
from functools import reduce

from django.db import models
from django.core.management.base import BaseCommand, CommandError

import numpy as np
import pandas as pd
from trading_calendars import get_calendar

from stocks.models import Exchange, Stock, DailySummary

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    EXCHANGE_KEY = 'exchange'
    DATE_FORMAT = '%Y%m%d'
    DATE_KEY = 'date'
    FROM_KEY = 'from'
    TO_KEY = 'to'
    TIMEOUT = 15

    help = 'Dump daily summary of a exchange'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__exchange = None

    def add_arguments(self, parser):
        exchange_choices = [
            exchange.code for exchange in Exchange.objects.all()
        ]
        parser.add_argument(f'--{self.EXCHANGE_KEY}',
                            required=True, choices=exchange_choices)
        parser.add_argument(f'--{self.DATE_KEY}')
        parser.add_argument(f'--{self.FROM_KEY}')
        parser.add_argument(f'--{self.TO_KEY}')

    @classmethod
    def parse_date(cls, value: str) -> datetime.date:
        try:
            return datetime.datetime.strptime(f'{value}Z', f'{cls.DATE_FORMAT}%z')
        except Exception as ex:
            raise CommandError('invalid date') from ex

    def fill_missing_stock(self, stock_codes: Sequence[str]) -> None:
        existing_stock_codes = (Stock.objects
                                .filter(exchange=self.__exchange, code__in=stock_codes)
                                .values_list('code', flat=True))

        missing_codes = set(stock_codes) - set(existing_stock_codes)
        if len(missing_codes) > 0:
            missing_stocks = map(
                lambda code: Stock.get_new_record(self.__exchange, code), missing_codes)
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
                 .filter(stock__exchange=exchange, date=date)
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

    def dump_daily_summary(self, exchange_code: str, date_text: str) -> None:
        logger.debug(
            '%s %s: start to dump daily summary', exchange_code, date_text)
        date = self.parse_date(date_text)

        if date not in get_calendar(self.__exchange.calendar_code).opens:
            logger.info('%s %s: skipped', exchange_code, date_text)
            return

        try:
            daily_exchange_summary_df = self.__exchange.get_daily_summary(date)
            daily_exchange_summary = self.trans_summary_df_to_dict(daily_exchange_summary_df)
            stock_codes = daily_exchange_summary.keys()
            self.fill_missing_stock(stock_codes)
            stock_map = self.get_stock_map(self.__exchange, stock_codes)
            summary_existing_codes = self.get_summary_existing_codes(self.__exchange, date)

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

            logger.info('%s %s: success', exchange_code, date_text)
        except Exception:  # pylint: disable=broad-except
            logger.exception('%s %s: failed', exchange_code, date_text)

    def handle(self, *args, **options):
        exchange_code = options[self.EXCHANGE_KEY]
        from_date_text = options.get(self.FROM_KEY)
        to_date_text = options.get(self.TO_KEY)

        self.__exchange = Exchange.objects.get(code=exchange_code)

        if from_date_text and to_date_text:
            for date in pd.date_range(from_date_text, to_date_text)[::-1]:
                date_text = date.strftime(self.DATE_FORMAT)
                self.dump_daily_summary(exchange_code, date_text)
        else:
            default_date = datetime.date.today().strftime(self.DATE_FORMAT)
            date_text = options.get(self.DATE_KEY, default_date)
            self.dump_daily_summary(exchange_code, date_text)
