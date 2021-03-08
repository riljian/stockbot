import logging
from typing import Tuple

import pandas as pd
import talib
from dateutil.tz import gettz
from trading_calendars import get_calendar

from stocks.models import DailySummary, Exchange

logger = logging.getLogger(__name__)


class Analyzer:

    def __init__(self, exchange):
        self._exchange = exchange
        self._calendar = get_calendar(exchange.calendar_code)

    @property
    def calendar(self):
        return self._calendar

    @property
    def exchange(self):
        return self._exchange

    def get_stocks(self) -> pd.DataFrame:
        pass

    def get_day_trading_candidates(self, date) -> pd.DataFrame:
        pass

    def get_technical_indicator_filled_kbars(self, stock, from_ts, to_ts) -> pd.DataFrame:
        pass

    @staticmethod
    def fill_technical_indicator(kbars):
        rsi_series = talib.RSI(kbars['close'], timeperiod=14).rename('rsi')
        macd, macd_signal, macd_hist = talib.MACD(kbars['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        macd_series = macd.rename('macd')
        macd_signal_series = macd_signal.rename('macd_signal')
        macd_hist_series = macd_hist.rename('macd_hist')
        return pd.concat([kbars, rsi_series, macd_series, macd_signal_series, macd_hist_series], axis=1)

    @staticmethod
    def ticks_to_kbars(ticks: pd.DataFrame, interval='1Min'):
        kbars = pd.DataFrame()

        kbars['open'] = ticks['close'].resample(interval).first()
        kbars['close'] = ticks['close'].resample(interval).last()
        kbars['high'] = ticks['close'].resample(interval).max()
        kbars['low'] = ticks['close'].resample(interval).min()
        kbars['volume'] = ticks['volume'].resample(interval).sum()

        return kbars.dropna()

    def save_plot(self, plot_title, kbars):
        pass

    def draw_plot(self, plot_title, kbars):
        pass


class TwseAnalyzer(Analyzer):
    MIN_RSI = 30
    MAX_RSI = 70

    def __init__(self):
        super().__init__(Exchange.objects.get(code='TWSE'))

    def get_stocks(self) -> pd.DataFrame:
        stocks = self._exchange.stocks.values('id', 'code', 'description')
        return pd.DataFrame.from_records(data=stocks)

    def get_date_open_duration(self, date):
        timezone = self._exchange.brokerage.TIMEZONE
        return [
            pd.to_datetime(date.strftime('%Y-%m-%dT09:00:00')).tz_localize(timezone),
            pd.to_datetime(date.strftime('%Y-%m-%dT14:30:00')).tz_localize(timezone),
        ]

    def get_technical_indicator_filled_kbars(self, stock, from_ts, to_ts):
        brokerage = self.exchange.brokerage

        prev_date = self.calendar.previous_close(from_ts).date()
        ticks = brokerage.get_ticks(stock, *self.get_date_open_duration(prev_date))

        for date in pd.date_range(from_ts, to_ts, freq='D'):
            ticks = ticks.append(brokerage.get_ticks(stock, *self.get_date_open_duration(date)))

        return self.fill_technical_indicator(self.ticks_to_kbars(ticks))[from_ts:to_ts]

    def setup_plot(self, plot_title, kbars):
        import finplot as fplt

        kbars = kbars.reset_index().rename(columns={'ts': 'time'})

        # adopt TWSE style
        fplt.display_timezone = gettz(self._exchange.brokerage.TIMEZONE)
        fplt.candle_bull_color = '#ef5350'
        fplt.candle_bull_body_color = fplt.candle_bull_color
        fplt.candle_bear_color = '#26a69a'
        fplt.volume_bull_color = '#f7a9a7'
        fplt.volume_bull_body_color = fplt.volume_bull_color
        fplt.volume_bear_color = '#92d2cc'

        main_ax, rsi_ax, macd_ax = fplt.create_plot(plot_title, rows=3)

        fplt.candlestick_ochl(kbars[['time', 'open', 'close', 'high', 'low']], ax=main_ax)
        fplt.volume_ocv(kbars[['time', 'open', 'close', 'volume']], ax=main_ax.overlay())

        fplt.plot(kbars['time'], kbars['rsi'], ax=rsi_ax, legend='RSI')
        fplt.set_y_range(0, 100, ax=rsi_ax)
        fplt.add_band(self.MIN_RSI, self.MAX_RSI, ax=rsi_ax)

        fplt.volume_ocv(kbars[['time', 'open', 'close', 'macd_hist']], ax=macd_ax, colorfunc=fplt.strength_colorfilter)
        fplt.plot(kbars['time'], kbars['macd'], ax=macd_ax, legend='MACD')
        fplt.plot(kbars['time'], kbars['macd_signal'], ax=macd_ax, legend='Signal')

    def save_plot(self, plot_title, kbars):
        import finplot as fplt

        self.setup_plot(plot_title, kbars)
        with open(f'{plot_title}.png', 'wb') as f:
            fplt.timer_callback(lambda: fplt.screenshot(f), 1, single_shot=True)
            fplt.show()

    def draw_plot(self, plot_title, kbars):
        import finplot as fplt

        self.setup_plot(plot_title, kbars)
        fplt.autoviewrestore()
        fplt.show()

    @staticmethod
    def get_price_filter(df: pd.DataFrame, date, min_price=0.0, max_price=999999.0) -> Tuple[pd.Series, pd.Series]:
        summary_qs = (DailySummary.objects
                      .filter(date=date)
                      .values('stock_id', 'closing_price'))
        snapshot = (pd.DataFrame
                    .from_records(data=summary_qs)
                    .rename(columns={'closing_price': 'price'}))
        summary = df.join(snapshot.set_index('stock_id'), on='id')

        return (summary['price'] >= min_price) & (summary['price'] <= max_price), summary['price']

    @staticmethod
    def get_trade_volume_filter(df: pd.DataFrame, date, min_volume=0) -> Tuple[pd.Series, pd.Series]:
        summary_qs = (DailySummary.objects
                      .filter(date=date)
                      .values('stock_id', 'trade_volume'))
        snapshot = pd.DataFrame.from_records(data=summary_qs)
        summary = df.join(snapshot.set_index('stock_id'), on='id')

        return summary['trade_volume'] >= min_volume, summary['trade_volume']

    def get_price_change_rate_filter(self, df: pd.DataFrame, date,
                                     min_change_rate=0.0, days=1) -> Tuple[pd.Series, pd.Series]:
        # noinspection PyArgumentList
        base_date = self._calendar.previous_close(date - pd.DateOffset(days=days - 1))

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

        change_rate_series = (summary['changed_price'] - summary['price']) / summary['price']
        change_rate_series.name = 'price_change_rate'
        change_rate_filter = change_rate_series > min_change_rate

        return change_rate_filter, change_rate_series

    def get_volume_change_rate_filter(self, df: pd.DataFrame, date,
                                      min_change_rate=0.0, days=1) -> Tuple[pd.Series, pd.Series]:
        # noinspection PyArgumentList
        base_date = self._calendar.previous_close(date - pd.DateOffset(days=days - 1))

        def get_summary_qs(d):
            return DailySummary.objects.filter(date=d).values('stock_id', 'trade_volume')

        snapshot = pd.DataFrame.from_records(data=get_summary_qs(base_date))
        changed_snapshot = (pd.DataFrame
                            .from_records(data=get_summary_qs(date))
                            .rename(columns={'trade_volume': 'changed_trade_volume'}))

        summary = df.join(snapshot.set_index('stock_id'), on='id')
        summary = summary.join(changed_snapshot.set_index('stock_id'), on='id')

        change_rate_series = (summary['changed_trade_volume'] - summary['trade_volume']) / summary['trade_volume']
        change_rate_series.name = 'volume_change_rate'
        change_rate_filter = change_rate_series > min_change_rate

        return change_rate_filter, change_rate_series
