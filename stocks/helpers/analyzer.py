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

    def get_price_filter(self, df: pd.DataFrame, date, min_price=0.0, max_price=999999.0) -> pd.DataFrame:
        summary_qs = (DailySummary.objects
                      .filter(date=date)
                      .values('stock_id', 'closing_price'))
        snapshot = (pd.DataFrame
                    .from_records(data=summary_qs)
                    .rename(columns={'closing_price': 'price'}))
        summary = df.join(snapshot.set_index('stock_id'), on='id')

        return (summary['price'] >= min_price) & (summary['price'] <= max_price), summary['price']

    def get_trade_volume_filter(self, df: pd.DataFrame, date, min_volume=0) -> pd.DataFrame:
        summary_qs = (DailySummary.objects
                      .filter(date=date)
                      .values('stock_id', 'trade_volume'))
        snapshot = pd.DataFrame.from_records(data=summary_qs)
        summary = df.join(snapshot.set_index('stock_id'), on='id')

        return summary['trade_volume'] >= min_volume, summary['trade_volume']

    def get_price_change_rate_filter(self, df: pd.DataFrame, date, min_change_rate=0.0, days=1) -> pd.DataFrame:
        base_date = \
            self._calendar.previous_close(date - pd.DateOffset(days=days - 1))

        def get_summary_qs(d):
            return DailySummary.objects.filter(date=d).values('stock_id', 'closing_price')

        snapshot = (pd.DataFrame
                    .from_records(data=get_summary_qs(base_date))
                    .rename(columns={'closing_price': 'price'}))
        changed_snapshot = (pd.DataFrame
                            .from_records(data=get_summary_qs(date))
                            .rename(columns={'closing_price': 'changed_price'}))

        summary = df.join(snapshot.set_index('stock_id'), on='id')
        summary = summary.join(changed_snapshot.set_index('stock_id'), on='id')

        change_rate_series = \
            (summary['changed_price'] - summary['price']) / summary['price']
        change_rate_series.name = 'price_change_rate'
        change_rate_filter = change_rate_series > min_change_rate

        return change_rate_filter, change_rate_series

    def get_volume_change_rate_filter(self, df: pd.DataFrame, date, min_change_rate=0.0, days=1):
        base_date = \
            self._calendar.previous_close(date - pd.DateOffset(days=days - 1))

        def get_summary_qs(d):
            return DailySummary.objects.filter(date=d).values('stock_id', 'trade_volume')

        snapshot = pd.DataFrame.from_records(data=get_summary_qs(base_date))
        changed_snapshot = (pd.DataFrame
                            .from_records(data=get_summary_qs(date))
                            .rename(columns={'trade_volume': 'changed_trade_volume'}))

        summary = df.join(snapshot.set_index('stock_id'), on='id')
        summary = summary.join(changed_snapshot.set_index('stock_id'), on='id')

        change_rate_series = \
            (summary['changed_trade_volume'] - summary['trade_volume']) \
            / summary['trade_volume']
        change_rate_series.name = 'volume_change_rate'
        change_rate_filter = change_rate_series > min_change_rate

        return change_rate_filter, change_rate_series

    def get_day_trading_candidates(self, date) -> pd.DataFrame:
        calendar = self._calendar
        if date not in calendar.opens:
            logger.info('%s is closed on %s', self._exchange.code, date)
            return pd.DataFrame()

        prev_trading_close = self._calendar.previous_close(date)
        df = self.get_stocks()
        volume_filter, volume_result = self.get_trade_volume_filter(
            df, prev_trading_close, min_volume=50000000)
        price_filter, price_result = self.get_price_filter(
            df, prev_trading_close, min_price=5.0, max_price=30.0)
        price_change_rate_filter, price_change_rate_result = self.get_price_change_rate_filter(
            df, prev_trading_close, min_change_rate=0.04, days=1)

        result = pd.concat(
            [df, volume_result, price_result, price_change_rate_result], axis=1)

        return result[volume_filter & price_filter & price_change_rate_filter]
