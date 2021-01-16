import os

import shioaji as sj


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


class TwseBrokerage(Brokerage):

    @classmethod
    def setup_adapter(cls, *args, **kwargs):
        account = {
            'username': os.getenv('BROKERAGE_USER'),
            'password': os.getenv('BROKERAGE_PASSWORD'),
        }
        adapter = sj.Shioaji()
        adapter.login(account['username'], account['password'])
        cls._adapter = adapter

    def get_stock_name(self, code):
        return self._adapter.Contracts.Stocks[code].name
