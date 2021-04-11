import logging
import math
from uuid import uuid4

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import models

from stocks.models import DailySummary
from stocks.models.summary import ConservativeStrategyTestRecord
from stocks.helpers import analyzer as analyzers

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    FROM_KEY = 'from'
    TO_KEY = 'to'

    help = 'Conservative candidates back test'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(f'--{self.FROM_KEY}', required=True)
        parser.add_argument(f'--{self.TO_KEY}', required=True)

    def handle(self, *args, **options):
        testing_duration = {
            'from': pd.to_datetime(options.get(self.FROM_KEY), utc=True),
            'to': pd.to_datetime(options.get(self.TO_KEY), utc=True),
        }
        analyzer = analyzers.TwseAnalyzer()
        calendar = analyzer.calendar
        investors_options = ('foreign_dealer', 'investment_trust', 'local_dealer_proprietary')
        df = analyzer.get_stocks()
        for date in reversed(calendar.opens[testing_duration['from']:testing_duration['to']]):
            try:
                prev_trading_close = analyzer.calendar.previous_close(date)
                last_date = date + pd.DateOffset(days=30)
                macd_signal_filter, _ = analyzer.get_macd_signal_filter(df, prev_trading_close)
                try:
                    for trading_days in range(2, 10):
                        for investor_picker in range(1, int(math.pow(2, len(investors_options)))):
                            investors = []
                            for investor_idx, investor in enumerate(investors_options):
                                if (investor_picker & (1 << investor_idx)) != 0:
                                    investors.append(investor)
                            investor_continuous_buy_filter, _ = \
                                analyzer.get_investor_continuous_buy_filter(df,
                                                                            prev_trading_close,
                                                                            investors=investors,
                                                                            trading_days=trading_days)
                            picked_stocks = df[macd_signal_filter & investor_continuous_buy_filter]
                            for _, stock_row in picked_stocks.iterrows():
                                stock_id = stock_row['id']
                                highest_price = (DailySummary.objects
                                                 .filter(stock_id=stock_id, date__gte=date, date__lte=last_date)
                                                 .aggregate(models.Max('highest_price')))['highest_price__max']
                                ConservativeStrategyTestRecord.objects.create(
                                    id=uuid4(),
                                    date=date,
                                    stock_id=stock_id,
                                    investors=','.join(investors),
                                    continuous_days=trading_days,
                                    highest_in_30_days=highest_price,
                                )
                except Exception:
                    logger.exception(f'Exception occurred on {date.strftime("%Y%m%d")} after getting macd signal filter')
            except Exception:
                logger.exception(f'Exception occurred on {date.strftime("%Y%m%d")}')
            logger.info(f'Success {date.strftime("%Y%m%d")}')
