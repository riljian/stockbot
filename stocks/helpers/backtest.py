from uuid import uuid4

import pandas as pd

from stocks.helpers import operator as operators
from stocks.models import BackTestRecord, Stock


class BackTest:

    def __init__(self):
        self.__no = uuid4()
        self.__records = \
            pd.DataFrame(columns=['ts', 'stock', 'price', 'volume']).set_index(
                ['ts', 'stock'])

    def insert_record(self, **kwargs):
        volume = kwargs['volume']
        stock = kwargs['stock']
        ts = kwargs['ts']
        price = kwargs['price']
        action = 'buy' if volume > 0 else 'sell'
        print(f'[{ts}] {action} {abs(volume)} {stock.description} at {price}')
        BackTestRecord.objects.create(id=uuid4(), no=self.__no, **kwargs)
        self.__records.append({**kwargs, 'stock': stock.id}, ignore_index=True)

    def start(self, from_ts, to_ts):
        stocks = self.pick_stocks(from_ts)

        for _, stock_row in stocks.iterrows():
            stock = Stock.objects.get(id=stock_row['id'])
            ticks = self.load_ticks(stock, from_ts, to_ts)
            for _, tick_row in ticks.iterrows():
                self.react(stock, tick_row)

    def pick_stocks(self, from_ts) -> pd.DataFrame:
        pass

    def load_ticks(self, stock, from_ts, to_ts) -> pd.DataFrame:
        pass

    def react(self, stock, tick_row):
        pass


class TwseDayTradeBackTest(BackTest):

    def __init__(self):
        super().__init__()
        self._operator = operators.TwseOperator()
        self._position = 0
        self._done = False

    def pick_stocks(self, from_ts) -> pd.DataFrame:
        return self._operator.get_day_trade_candidates(from_ts)

    def load_ticks(self, stock, from_ts, to_ts) -> pd.DataFrame:
        return self._operator.brokerage.get_ticks(stock, from_ts, to_ts)

    def react(self, stock, tick_row):
        operator = self._operator
        timezone = operator.brokerage.TIMEZONE
        ts = tick_row.name
        price = tick_row['close']
        if self._done:
            return
        elif ts > pd.to_datetime('2021-03-05T09:30:00').tz_localize(timezone) and self._position == 0:
            volume = tick_row['volume'] * 1000
            self.insert_record(ts=ts, stock=stock, price=price, volume=volume)
            self._position += volume
        elif ts > pd.to_datetime('2021-03-05T13:00:00').tz_localize(timezone) and self._position > 0:
            volume = -self._position
            self.insert_record(ts=ts, stock=stock, price=price, volume=volume)
            self._position += volume
            self._done = True
