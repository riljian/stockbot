import datetime
import time
import logging
from functools import reduce

import requests
import pandas as pd
from retrying import retry

logger = logging.getLogger(__name__)


class Crawler:
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_TIMEOUT = 60000
    DEFAULT_USER_AGENT = (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6)'
        ' AppleWebKit/537.36 (KHTML, like Gecko)'
        ' Chrome/86.0.4240.183'
        ' Safari/537.36'
    )
    DEFAULT_TIMEOUT_BETWEEN_SUCCESSFUL_REQUESTS = 15

    __previous_response = None

    def __init__(self, **kwargs):
        self._user_agent = kwargs.get('user_agent', self.DEFAULT_USER_AGENT)
        self._retry_count = kwargs.get('retry_count', self.DEFAULT_RETRY_COUNT)
        self._retry_timeout = \
            kwargs.get('retry_timeout', self.DEFAULT_RETRY_TIMEOUT)
        self._timeout_between_successful_requests = \
            kwargs.get('timeout_between_successful_requests',
                       self.DEFAULT_TIMEOUT_BETWEEN_SUCCESSFUL_REQUESTS)

    @property
    def user_agent(self):
        return self._user_agent

    @property
    def retry_count(self):
        return self._retry_count

    @property
    def retry_timeout(self):
        return self._retry_timeout

    @property
    def timeout_between_successful_requests(self):
        return self._timeout_between_successful_requests

    @classmethod
    def set_previous_response(cls, value):
        cls.__previous_response = value

    def request(self, *args, **kwargs) -> requests.Response:
        headers = {
            'User-Agent': self.user_agent,
            **kwargs.get('headers', {})
        }

        @retry(stop_max_attempt_number=self.retry_count, wait_fixed=self.retry_timeout)
        def wrapped_request():
            return requests.request(*args, **kwargs, headers=headers)

        if self.__previous_response:
            logger.debug('timeout between successful requests: %d seconds...',
                         self.timeout_between_successful_requests)
            time.sleep(self.timeout_between_successful_requests)

        response = wrapped_request()
        self.set_previous_response(response)
        return response


class ExchangeCrawler(Crawler):

    def get_daily_summary(self, date: datetime.date) -> pd.DataFrame:
        pass


class TwseCrawler(ExchangeCrawler):
    ORIGIN = 'https://www.twse.com.tw'

    @classmethod
    def get_parsing_offset(cls, date):
        if date <= datetime.datetime.strptime('20110729Z', '%Y%m%d%z'):
            return -2, 1
        return -1, 2

    @classmethod
    def process_daily_summary_response(cls, response, date) -> pd.DataFrame:
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

    def get_daily_summary(self, date: datetime.datetime) -> pd.DataFrame:
        path = '/en/exchangeReport/MI_INDEX'
        url = f'{self.ORIGIN}{path}'
        params = {
            'response': 'html',
            'date': date.strftime('%Y%m%d'),
            'type': 'ALLBUT0999',
        }
        response = self.request(url=url, method='get', params=params)
        return self.process_daily_summary_response(response, date)

    def load_stock_candidates_by_partial_code(self, partial_code) -> dict:
        path = '/zh/api/codeQuery'
        url = f'{self.ORIGIN}{path}'
        params = {
            'query': partial_code,
            '_': str(int(datetime.datetime.now().timestamp() * 1000))
        }
        response = self.request(url=url, method='get', params=params)
        suggestions = response.json()['suggestions']

        def reducer(acc, suggestion):
            try:
                suggestion_code, suggestion_name = suggestion.split('\t')
                acc[suggestion_code] = suggestion_name
            except ValueError:
                # `show more result` would be un-splittable
                pass
            return acc

        return reduce(reducer, suggestions, {})

    def get_stock_name(self, code) -> str:
        candidates = self.load_stock_candidates_by_partial_code(code)
        return candidates[code]
