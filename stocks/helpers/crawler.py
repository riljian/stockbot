import time
import datetime
from typing import Optional

import requests
import pandas as pd


class Crawler:
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_TIMEOUT = 60
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36'

    # TODO: integrate with retrying module
    @classmethod
    def retry_request(cls, *args, **kwargs) -> Optional[requests.Response]:
        headers = {
            'User-Agent': cls.DEFAULT_USER_AGENT,
            **kwargs.get('headers', {})
        }

        for _ in range(cls.DEFAULT_RETRY_COUNT):
            try:
                return requests.request(*args, **kwargs, headers=headers)
            except Exception:  # pylint: disable=broad-except
                time.sleep(cls.DEFAULT_RETRY_TIMEOUT)

        return None


class ExchangeCrawler(Crawler):

    def __init__(self, exchange):
        self._exchange = exchange

    def get_daily_summary(self, date: datetime.date) -> Optional[pd.DataFrame]:
        pass


class TwseCrawler(ExchangeCrawler):
    ORIGIN = 'https://www.twse.com.tw'

    @classmethod
    def get_parsing_offset(cls, date):
        if date <= datetime.datetime.strptime('20110729', '%Y%m%d'):
            return -2, 1
        return -1, 2

    @classmethod
    def process_daily_sumary_response(cls, response, date) -> pd.DataFrame:
        daily_quotes_table_index, target_columns_level = \
            cls.get_parsing_offset(date)
        rename_mapper = {
            'Security Code': 'code',
            'Trade Volume': 'trade_volume',
            'Transaction': 'transaction',
            'Trade Value': 'trade_value',
            'Opening Price': 'opening_price',
            'Highest Price': 'highest_price',
            'Lowest Price': 'lowest_price',
            'Closing Price': 'closing_price',
            'Last Best Bid Price': 'last_best_bid_price',
            'Last Best Bid Volume': 'last_best_bid_volume',
            'Last Best Ask Price': 'last_best_ask_price',
            'Last Best Ask Volume': 'last_best_ask_volume',
        }
        df = pd.read_html(response.text)[daily_quotes_table_index]
        df.columns = df.columns.get_level_values(target_columns_level)
        df.drop(['Dir(+/-)', 'Change', 'Price-Earning ratio'],
                inplace=True, axis='columns')
        df.rename(columns=rename_mapper, inplace=True)
        df.set_index(['code'], inplace=True)
        return df.apply(pd.to_numeric, errors='coerce')

    @classmethod
    def get_daily_summary(cls, date: datetime.date) -> Optional[pd.DataFrame]:
        path = '/en/exchangeReport/MI_INDEX'
        params = {
            'response': 'html',
            'date': date.strftime('%Y%m%d'),
            'type': 'ALLBUT0999',
        }
        response = cls.retry_request(
            url=f'{cls.ORIGIN}{path}', method='get', params=params)
        if response is None:
            return None
        return cls.process_daily_sumary_response(response, date)
