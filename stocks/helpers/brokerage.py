from uuid import uuid4

import pandas as pd
import shioaji as sj


class Brokerage:
    TIMEZONE = None
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
            tick_cls = stock.ticks.model
            tick_raw = self._adapter.ticks(self.get_stock_meta(stock.code),
                                           from_ts.strftime('%Y-%m-%d'))
            df = pd.DataFrame({**tick_raw})
            df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(self.TIMEZONE)
            df = df[(df['ts'] >= from_ts) & (df['ts'] <= to_ts)]

            def mapper(tick):
                return tick_cls(id=uuid4(), stock=stock, **tick)

            ticks = list(map(mapper, df.to_dict('records')))
            chunk_size = 20000  # MySQL insertion failed: MySQL server has gone away
            for i in range(0, len(ticks), chunk_size):
                tick_cls.objects.bulk_create(ticks[i:i + chunk_size])

        return df.set_index('ts')
