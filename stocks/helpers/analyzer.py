import logging
from typing import Tuple

import pandas as pd
from pandas.tseries.frequencies import to_offset
import talib
from dateutil.tz import gettz
from django.db import models

from stocks.models import DailySummary, Exchange, Stock

logger = logging.getLogger(__name__)


class Analyzer:

    def __init__(self, exchange):
        self._exchange = exchange

    @property
    def calendar(self):
        return self.exchange.calendar

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
    def get_is_interval_over_a_day(interval):
        return to_offset(interval) >= to_offset('1D')

    @staticmethod
    def ticks_to_kbars(ticks: pd.DataFrame, interval='1Min'):
        kbars = pd.DataFrame()

        kbars['open'] = ticks['close'].resample(interval).first()
        kbars['close'] = ticks['close'].resample(interval).last()
        kbars['high'] = ticks['close'].resample(interval).max()
        kbars['low'] = ticks['close'].resample(interval).min()
        kbars['volume'] = ticks['volume'].resample(interval).sum()

        return kbars.dropna()

    def daily_summaries_to_kbars(self, daily_summaries, interval='1D'):
        timezone = self.exchange.brokerage.TIMEZONE
        kbars = pd.DataFrame()
        summaries = pd.DataFrame.from_records(data=daily_summaries)
        summaries['ts'] = pd.to_datetime(summaries['date']).dt.tz_localize(timezone)
        summaries = summaries.set_index(['ts'])

        kbars['open'] = summaries['opening_price'].resample(interval).first()
        kbars['close'] = summaries['closing_price'].resample(interval).last()
        kbars['high'] = summaries['highest_price'].resample(interval).max()
        kbars['low'] = summaries['lowest_price'].resample(interval).min()
        kbars['volume'] = summaries['trade_volume'].resample(interval).sum()

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
        return {
            'open': pd.to_datetime(date.strftime('%Y-%m-%dT09:00:00')).tz_localize(timezone),
            'close': pd.to_datetime(date.strftime('%Y-%m-%dT13:30:00')).tz_localize(timezone),
        }

    def get_kbars(self, stock, from_ts, to_ts, interval='1Min'):
        brokerage = self.exchange.brokerage

        ticks = pd.DataFrame()
        if self.get_is_interval_over_a_day(interval):
            daily_summaries = (stock.daily_summaries
                               .filter(date__gte=from_ts, date__lte=to_ts)
                               .values('date', 'trade_volume', 'opening_price', 'closing_price',
                                       'highest_price', 'lowest_price'))
            return self.daily_summaries_to_kbars(daily_summaries, interval=interval)
        else:
            for date in pd.date_range(from_ts, to_ts, freq='D'):
                duration = self.get_date_open_duration(date)
                ticks = ticks.append(brokerage.get_ticks(stock, duration['open'], duration['close']))
            return self.ticks_to_kbars(ticks, interval=interval)

    def get_technical_indicator_filled_kbars(self, stock, from_ts, to_ts, interval='1Min'):
        calendar = self.calendar
        date_only_from_ts = from_ts.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.get_is_interval_over_a_day(interval):
            # FIXME: remove magic number
            kbar_from_ts = calendar.opens[:date_only_from_ts][-80]
            data_filter_from_ts = date_only_from_ts
        else:
            kbar_from_ts = calendar.opens[:date_only_from_ts][-1]
            data_filter_from_ts = from_ts
        kbars = self.get_kbars(stock, kbar_from_ts, to_ts, interval=interval)

        rsi_series = talib.RSI(kbars['close'], timeperiod=14).rename('rsi')
        macd, macd_signal, macd_hist = talib.MACD(kbars['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        macd_series = macd.rename('macd')
        macd_signal_series = macd_signal.rename('macd_signal')
        macd_hist_series = macd_hist.rename('macd_hist')

        total_series = [kbars, rsi_series, macd_series, macd_signal_series, macd_hist_series]
        result = pd.concat(total_series, axis='columns')[data_filter_from_ts:to_ts]
        return result.dropna()

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

        return fplt

    def save_plot(self, plot_title, kbars):
        fplt = self.setup_plot(plot_title, kbars)
        with open(f'{plot_title}.png', 'wb') as f:
            fplt.timer_callback(lambda: fplt.screenshot(f), 1, single_shot=True)
            fplt.show()

    def draw_plot(self, plot_title, kbars):
        fplt = self.setup_plot(plot_title, kbars)
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

    @staticmethod
    def get_amplitude_filter(df: pd.DataFrame, from_ts, to_ts, min_amplitude=0.0) -> Tuple[pd.Series, pd.Series]:
        raw = (DailySummary.objects
               .filter(date__gte=from_ts, date__lte=to_ts)
               .values('stock')
               .annotate(lowest_price=models.Min('lowest_price'),
                         highest_price=models.Max('highest_price')))
        summary = pd.DataFrame.from_records(data=raw)
        lowest_price_series = summary['lowest_price']
        highest_price_series = summary['highest_price']
        summary['amplitude'] = \
            (highest_price_series - lowest_price_series) / (highest_price_series + lowest_price_series)
        ordered_summary = df.join(summary.set_index('stock'), on='id')

        return ordered_summary['amplitude'] >= min_amplitude, ordered_summary['amplitude']

    def get_price_change_rate_filter(self, df: pd.DataFrame, date,
                                     min_change_rate=0.0, trading_days=1) -> Tuple[pd.Series, pd.Series]:
        # noinspection PyArgumentList
        base_date = self.calendar.opens[:date][-(trading_days + 1)]

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
                                      min_change_rate=0.0, trading_days=1) -> Tuple[pd.Series, pd.Series]:
        # noinspection PyArgumentList
        base_date = self.calendar.opens[:date][-(trading_days + 1)]

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

    def get_investor_continuous_buy_filter(self, df: pd.DataFrame, date,
                                           investors=('foreign_dealer', 'investment_trust', 'local_dealer_proprietary'),
                                           trading_days=3) -> Tuple[pd.Series, pd.Series]:
        last_n_days = self.calendar.opens[:date].tail(trading_days)
        data = DailySummary.objects.filter(date__in=last_n_days).values().order_by('stock', 'date')
        snapshot = pd.DataFrame.from_records(data=data)

        total_volume_key = 'investor_total_volume'
        for idx, investor in enumerate(investors):
            diff = snapshot[f'{investor}_buy_volume'] - snapshot[f'{investor}_sell_volume']
            snapshot[total_volume_key] = diff if idx == 0 else snapshot[total_volume_key] + diff
        snapshot['is_buy'] = snapshot[total_volume_key] > 0
        aggregate_map = {total_volume_key: 'sum', 'is_buy': 'all'}
        summary = snapshot[['stock_id', total_volume_key, 'is_buy']].groupby(snapshot['stock_id']).agg(aggregate_map)
        ordered_summary = df.join(summary, on='id')

        return ordered_summary['is_buy'] == True, ordered_summary[total_volume_key]

    def get_rsi_filter(self, df: pd.DataFrame, date, min_value=0.0, max_value=100.0) -> Tuple[pd.Series, pd.Series]:
        stocks = Stock.objects.filter(daily_summaries__date=date)
        snapshot = pd.DataFrame(columns=['stock_id', 'rsi'])
        for stock in stocks:
            duration = self.get_date_open_duration(date)
            kbars = self.get_technical_indicator_filled_kbars(stock, duration['open'], duration['close'], interval='1D')
            if kbars.empty:
                logger.warning(f'Stock {stock.code} is skipped in get_rsi_filter')
                continue
            snapshot = snapshot.append({'stock_id': stock.pk, 'rsi': kbars.reset_index().at[0, 'rsi']},
                                       ignore_index=True)
        summary = df.join(snapshot.set_index('stock_id'), on='id')

        return (summary['rsi'] >= min_value) & (summary['rsi'] <= max_value), summary['rsi']
