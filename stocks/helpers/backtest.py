import logging
from uuid import uuid4

import pandas as pd

from stocks.helpers import operator as operators
from stocks.models import BackTestRecord, Stock

logger = logging.getLogger(__name__)


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
        action = 'Buy' if volume > 0 else 'Sell'
        logger.info(f'[{ts}] {action} {int(abs(volume))} {stock.code} at {price}')
        BackTestRecord.objects.create(id=uuid4(), no=self.__no, **kwargs)
        self.__records.append({**kwargs, 'stock': stock.id}, ignore_index=True)

    def start(self, from_ts, to_ts):
        stocks = self.pick_stocks(from_ts)
        if stocks.empty:
            logger.info('No stock picked')
        else:
            logger.info('Stock {} picked'.format(stocks['code'].to_list()))

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

    def start(self, from_date, to_date):
        for date in pd.date_range(from_date, to_date, freq='D'):
            logger.info('{} day trade back test'.format(date.strftime('%Y/%m/%d')))
            from_ts = date.replace(hour=9, minute=00, second=0, microsecond=0)
            to_ts = date.replace(hour=14, minute=30, second=0, microsecond=0)
            super().start(from_ts, to_ts)

    def pick_stocks(self, from_ts) -> pd.DataFrame:
        return self._operator.get_day_trade_candidates(from_ts)

    def load_ticks(self, stock, from_ts, to_ts) -> pd.DataFrame:
        return self._operator.brokerage.get_ticks(stock, from_ts, to_ts)

    def setup(self, stock, from_ts, to_ts):
        analyzer = self._operator.analyzer
        self._kbars[stock.id] = analyzer.get_technical_indicator_filled_kbars(stock, from_ts, to_ts)
        logger.info(f'Stock {stock.code} initialized')

    def react(self, stock, tick_row):
        analyzer = self._operator.analyzer
        ts = tick_row.name
        price = tick_row['close']
        kbars = self._kbars[stock.id][:ts]
        min_rsi = kbars.tail(3)['rsi'].min()
        max_rsi = kbars.tail(3)['rsi'].max()
        # final_in_ts = ts.replace(hour=11, minute=30, second=0, microsecond=0)
        final_out_ts = ts.replace(hour=13, minute=00, second=0, microsecond=0)
        is_in_timing, is_out_timing = False, False

        if len(kbars.index) > 1:
            prev_macd = kbars.iloc[-2]['macd_hist']
            curr_macd = kbars.iloc[-1]['macd_hist']
            is_in_timing = min_rsi < analyzer.MIN_RSI and (prev_macd < 0 < curr_macd)
            is_out_timing = max_rsi > analyzer.MAX_RSI and (curr_macd < 0 < prev_macd)

        if is_in_timing and ts < final_out_ts and self._position == 0:
            volume = tick_row['volume'] * 1000
            self.insert_record(ts=ts, stock=stock, price=price, volume=volume)
            self._position += volume
        elif self._position > 0 and (is_out_timing or ts >= final_out_ts):
            volume = -self._position
            self.insert_record(ts=ts, stock=stock, price=price, volume=volume)
            self._position += volume
