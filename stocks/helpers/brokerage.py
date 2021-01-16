import os

import shioaji as sj


class Brokerage:

    def __init__(self):
        self._account = {
            'username': os.getenv('BROKERAGE_USER'),
            'password': os.getenv('BROKERAGE_PASSWORD'),
        }


class TwseBrokerage(Brokerage):

    def __init__(self):
        super().__init__()
        self._adapter = sj.Shioaji()
        self._adapter.login(
            self._account['username'], self._account['password'])

    def get_stock_name(self, code):
        return self._adapter.Contracts.Stocks[code].name
