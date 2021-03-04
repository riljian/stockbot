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

    def get_stocks(self) -> pd.DataFrame:
        pass

    def get_day_trading_candidates(self, date) -> pd.DataFrame:
        pass


class TwseAnalyzer(Analyzer):

    def __init__(self):
        super().__init__(Exchange.objects.get(code='TWSE'))

    def get_stocks(self) -> pd.DataFrame:
        stocks = self._exchange.stocks.values('id', 'code', 'description')
        return pd.DataFrame.from_records(data=stocks)

    def filter_by_price(self, df: pd.DataFrame, date, min_price=0.0, max_price=999999.0) -> pd.DataFrame:
        stock_ids = (DailySummary.objects
                     .filter(date=date, closing_price__gte=min_price, closing_price__lte=max_price)
                     .values_list('stock_id', flat=True))

        return df[df['id'].map(lambda stock_id: stock_id in stock_ids)]

    def filter_by_trade_volume(self, df: pd.DataFrame, date, min_volume=0) -> pd.DataFrame:
        stock_ids = (DailySummary.objects
                     .filter(date=date, trade_volume__gte=min_volume)
                     .values_list('stock_id', flat=True))

        return df[df['id'].map(lambda stock_id: stock_id in stock_ids)]

    def filter_by_change_rate(self, df: pd.DataFrame, date, min_change_rate=0.0, days=1) -> pd.DataFrame:
        base_date = \
            self._calendar.previous_close(date - pd.DateOffset(days=days - 1))

        def get_summary_qs(d):
            return DailySummary.objects.filter(date=d).values('stock_id', 'closing_price')

        snapshot = pd.DataFrame.from_records(data=get_summary_qs(base_date))
        changed_snapshot = pd.DataFrame.from_records(data=get_summary_qs(date))
        summary = snapshot.join(changed_snapshot.set_index('stock_id'),
                                rsuffix='_changed',
                                on='stock_id')
        change_rate_series = \
            (summary['closing_price_changed'] - summary['closing_price']) \
            / summary['closing_price']
        change_rate_filter = change_rate_series > min_change_rate
        stock_ids = summary[change_rate_filter]['stock_id'].to_list()

        return df[df['id'].map(lambda stock_id: stock_id in stock_ids)]

    def get_day_trading_candidates(self, date) -> pd.DataFrame:
        calendar = self._calendar
        if date not in calendar.opens:
            logger.info('%s is closed on %s', self._exchange.code, date)
            return DailySummary.objects.none()

        prev_trading_close = self._calendar.previous_close(date)
        df = self.get_stocks()
        df = self.filter_by_trade_volume(
            df, prev_trading_close, min_volume=50000000)
        df = self.filter_by_price(
            df, prev_trading_close, min_price=5.0, max_price=30.0)
        df = self.filter_by_change_rate(
            df, prev_trading_close, min_change_rate=0.04, days=1)

        return df
