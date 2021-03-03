import logging

import pandas as pd
from trading_calendars import get_calendar

from django.db import models

from stocks.models import DailySummary, Exchange

logger = logging.getLogger(__name__)


class Analyzer:

    def __init__(self, exchange):
        self._exchange = exchange
        self._calendar = get_calendar(exchange.calendar_code)

    def get_stocks_with_price(self, date) -> pd.DataFrame:
        pass

    def get_day_trading_candidates(self, date) -> pd.DataFrame:
        pass


class TwseAnalyzer(Analyzer):

    def __init__(self):
        super().__init__(Exchange.objects.get(code='TWSE'))

    def get_stocks_with_price(self, date) -> pd.DataFrame:
        stocks = (DailySummary.objects
                  .filter(stock__in=self._exchange.stocks.all(), date=date)
                  .annotate(
                      code=models.F('stock__code'),
                      description=models.F('stock__description'),
                      price=models.F('closing_price'),
                  )
                  .values('stock_id', 'code', 'description', 'price', 'trade_volume'))
        return pd.DataFrame.from_records(data=stocks)

    def filter_by_price(self, df: pd.DataFrame, min_price=0.0, max_price=999999.0) -> pd.DataFrame:
        return df[(df['price'] > min_price) & (df['price'] < max_price)]

    def filter_by_trade_volume(self, df: pd.DataFrame, min_volume=0) -> pd.DataFrame:
        return df[df['trade_volume'] > min_volume]

    def filter_by_change_rate(self, df: pd.DataFrame, date, change_rate=0.0, days=1) -> pd.DataFrame:
        base_date = \
            self._calendar.previous_close(date - pd.DateOffset(days=days - 1))
        queryset = (DailySummary.objects
                    .filter(stock__in=df['stock_id'].to_list(), date=base_date)
                    .annotate(price=models.F('closing_price'))
                    .values('stock_id', 'price'))
        summary = pd.DataFrame.from_records(data=queryset)
        summary.rename(columns={'price': 'base_price'}, inplace=True)
        df = df.join(summary.set_index('stock_id'), on='stock_id')
        df['change'] = df['price'] - df['base_price']
        df['change_rate'] = df['change'] / df['base_price']
        return df[df['change_rate'] > change_rate]

    def get_day_trading_candidates(self, date) -> pd.DataFrame:
        calendar = self._calendar
        if date not in calendar.opens:
            logger.info('%s is closed on %s', self._exchange.code, date)
            return DailySummary.objects.none()

        prev_trading_close = self._calendar.previous_close(date)
        df = self.get_stocks_with_price(prev_trading_close)
        df = self.filter_by_trade_volume(df, min_volume=50000000)
        df = self.filter_by_price(df, min_price=5.0, max_price=30.0)
        df = self.filter_by_change_rate(
            df, prev_trading_close, change_rate=0.04, days=1)

        return df
