import shioaji as sj
import pandas as pd


class Brokerage:
    _adapter = None

    def __init__(self):
        if self._adapter is None:
            raise ValueError('should initialize adapter first')

    @classmethod
    def setup_adapter(cls, *args, **kwargs):
        pass

    @classmethod
    def init_adapter(cls, *args, **kwargs):
        if cls._adapter is None:
            cls.setup_adapter(*args, **kwargs)

    def get_stock_meta(self, code):
        pass

    def get_ticks(self, code, date) -> pd.DataFrame:
        pass


class TwseBrokerage(Brokerage):

    @classmethod
    def setup_adapter(cls, *args, **kwargs):
        account = kwargs['account']
        adapter = sj.Shioaji()
        adapter.login(account['user'], account['password'])
        cls._adapter = adapter

    def get_stock_meta(self, code):
        return self._adapter.Contracts.Stocks[code]

    def get_ticks(self, code, date) -> pd.DataFrame:
        tick_raw = self._adapter.ticks(self.get_stock_meta(code),
                                       date.strftime('%Y-%m-%d'))
        df = pd.DataFrame({**tick_raw})
        df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize('Asia/Taipei')
        return df
