from dateutil.tz import gettz

import pandas as pd

from stocks.helpers import analyzer as analyzers


class Operator:

    @property
    def analyzer(self):
        return self._analyzer

    @property
    def exchange(self):
        return self.analyzer.exchange

    @property
    def brokerage(self):
        return self.exchange.brokerage

    def get_day_trade_candidates(self, date) -> pd.DataFrame:
        pass


class TwseOperator(Operator):

    def __init__(self):
        self._analyzer = analyzers.TwseAnalyzer()

    def get_day_trade_candidates(self, date) -> pd.DataFrame:
        analyzer = self._analyzer

        pruned_date = pd.to_datetime(date.strftime('%Y/%m/%d'), utc=True)
        if pruned_date not in analyzer.calendar.opens:
            return pd.DataFrame()

        prev_trading_close = analyzer.calendar.previous_close(date)

        df = analyzer.get_stocks()

        volume_filter, volume_result = \
            analyzer.get_trade_volume_filter(df, prev_trading_close, min_volume=50000000)
        price_filter, price_result = \
            analyzer.get_price_filter(df, prev_trading_close, min_price=5.0, max_price=30.0)
        price_change_rate_filter, price_change_rate_result = \
            analyzer.get_price_change_rate_filter(df, prev_trading_close, min_change_rate=0.04, days=1)

        result = pd.concat([df, volume_result, price_result, price_change_rate_result], axis=1)
        return result[volume_filter & price_filter & price_change_rate_filter]
