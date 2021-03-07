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
            self.setup(stock, from_ts, to_ts)
            ticks = self.load_ticks(stock, from_ts, to_ts)
            for _, tick_row in ticks.iterrows():
                self.react(stock, tick_row)

    def pick_stocks(self, from_ts) -> pd.DataFrame:
        pass

    def load_ticks(self, stock, from_ts, to_ts) -> pd.DataFrame:
        pass

    def react(self, stock, tick_row):
        pass

    def setup(self, stock, from_ts, to_ts):
        pass


class TwseDayTradeBackTest(BackTest):

    def __init__(self):
        super().__init__()
        self._kbars = {}
        self._operator = operators.TwseOperator()
        self._position = 0
        self._done = False

    def pick_stocks(self, from_ts) -> pd.DataFrame:
        return self._operator.get_day_trade_candidates(from_ts)

    def load_ticks(self, stock, from_ts, to_ts) -> pd.DataFrame:
        return self._operator.brokerage.get_ticks(stock, from_ts, to_ts)

    def setup(self, stock, from_ts, to_ts):
        operator = self._operator
        timezone = operator.brokerage.TIMEZONE
        brokerage = operator.brokerage
        analyzer = operator.analyzer
        curr_date = pd.to_datetime(from_ts.strftime('%Y/%m/%d'))
        prev_date = operator.analyzer.calendar.previous_close(curr_date).date()

        def get_ts_duration(date):
            return [
                pd.to_datetime(date.strftime('%Y-%m-%dT09:00:00')).tz_localize(timezone),
                pd.to_datetime(date.strftime('%Y-%m-%dT14:30:00')).tz_localize(timezone),
            ]

        curr_ticks = brokerage.get_ticks(stock, *get_ts_duration(curr_date))
        prev_ticks = brokerage.get_ticks(stock, *get_ts_duration(prev_date))
        ticks = prev_ticks.append(curr_ticks)
        kbars = analyzer.fill_technical_indicator(analyzer.ticks_to_kbars(ticks))
        self._kbars[stock.id] = kbars[from_ts:]

    def react(self, stock, tick_row):
        operator = self._operator
        timezone = operator.brokerage.TIMEZONE
        ts = tick_row.name
        price = tick_row['close']
        prev_kbars = self._kbars[stock.id][:ts]
        rsi = prev_kbars.iloc[len(prev_kbars.index) - 1]['rsi']
        if self._done:
            return
        elif self._position == 0 and rsi < 20:
            volume = tick_row['volume'] * 1000
            self.insert_record(ts=ts, stock=stock, price=price, volume=volume)
            self._position += volume
        elif self._position > 0 and (ts >= pd.to_datetime('2021-03-05T13:30:00').tz_localize(timezone) or rsi > 80):
            volume = -self._position
            self.insert_record(ts=ts, stock=stock, price=price, volume=volume)
            self._position += volume
            self._done = True
