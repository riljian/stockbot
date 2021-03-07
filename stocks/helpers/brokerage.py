from uuid import uuid4

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

    def get_ticks(self, stock, from_ts, to_ts) -> pd.DataFrame:
        pass


class TwseBrokerage(Brokerage):
    TIMEZONE = 'Asia/Taipei'

    @classmethod
    def setup_adapter(cls, *args, **kwargs):
        account = kwargs['account']
        adapter = sj.Shioaji()
        adapter.login(account['user'], account['password'])
        cls._adapter = adapter

    def get_stock_meta(self, code):
        return self._adapter.Contracts.Stocks[code]

    def get_ticks(self, stock, from_ts, to_ts) -> pd.DataFrame:
        tick_keys = ('ts', 'close', 'volume', 'bid_price',
                     'bid_volume', 'ask_price', 'ask_volume')

        tick_qs = stock.ticks.filter(ts__gte=from_ts, ts__lte=to_ts)
        if tick_qs.exists():
            df = pd.DataFrame.from_records(data=tick_qs.values(*tick_keys).order_by('ts'))
            df['ts'] = df['ts'].dt.tz_convert(self.TIMEZONE)
        else:
            Tick = stock.ticks.model  # pylint: disable=invalid-name

            def mapper(tick):
                return Tick(id=uuid4(), stock=stock, **tick)
            tick_raw = self._adapter.ticks(self.get_stock_meta(stock.code),
                                           from_ts.strftime('%Y-%m-%d'))
            df = pd.DataFrame({**tick_raw})
            df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(self.TIMEZONE)
            df = df[(df['ts'] >= from_ts) & (df['ts'] <= to_ts)]
            Tick.objects.bulk_create(map(mapper, df.to_dict('records')))

        return df.set_index('ts')
