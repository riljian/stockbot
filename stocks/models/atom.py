import os
import datetime
from uuid import uuid4

from caseconverter import pascalcase
import pandas as pd
from django.db import models

from utils import AESEncoder
import stocks.helpers.crawler as crawlers
import stocks.helpers.brokerage as brokerages


class Exchange(models.Model):
    id = models.UUIDField(primary_key=True)
    code = models.CharField(max_length=10)  # 交易所代號
    calendar_code = \
        models.CharField(max_length=10, null=True)  # trading-calendars 交易所代號
    description = models.CharField(max_length=255, null=True)
    brokerage_user = models.CharField(max_length=255, null=True)  # 券商 API 帳號
    brokerage_password = \
        models.CharField(max_length=255, null=True)  # 券商 API 密碼

    encoder = AESEncoder(os.getenv('BROKERAGE_ACCOUNT_KEY'),
                         os.getenv('BROKERAGE_ACCOUNT_IV'))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code'], name='unique_exchange')
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.init_crawler()
        self._brokerage = None

    @property
    def crawler(self):
        return self._crawler

    @property
    def brokerage(self):
        if self._brokerage is None:
            self.init_brokerage()
        return self._brokerage

    @staticmethod
    def get_stock_crawler_class(code):
        return getattr(crawlers, pascalcase(f'{code} crawler'), None)

    @staticmethod
    def get_stock_brokerage_class(code):
        return getattr(brokerages, pascalcase(f'{code} brokerage'), None)

    def init_crawler(self):
        crawler_cls = self.get_stock_crawler_class(self.code)
        if crawler_cls is None:
            raise ValueError('crawler not found')
        self._crawler = crawler_cls()

    def init_brokerage(self):
        brokerage_cls = self.get_stock_brokerage_class(self.code)
        if brokerage_cls is None:
            raise ValueError('brokerage not found')
        brokerage_cls.init_adapter(account=self.retrieve_brokerage_account())
        self._brokerage = brokerage_cls()

    def setup_brokerage_account(self, user, password):
        self.brokerage_user = self.encoder.encrypt(user)
        self.brokerage_password = self.encoder.encrypt(password)
        self.save()

    def retrieve_brokerage_account(self):
        return {
            'user': self.encoder.decrypt(self.brokerage_user),
            'password': self.encoder.decrypt(self.brokerage_password),
        }

    def get_stock_name(self, code: str) -> str:
        stocks = Stock.objects.filter(exchange=self, code=code)
        if stocks.exists():
            stock = stocks[0]
            if stock.description is None:
                stock.description = self.crawler.get_stock_name(code)
                stock.save()
            return stock.description
        return self.crawler.get_stock_name(code)

    def get_daily_summary(self, date: datetime.date) -> pd.DataFrame:
        # TODO: fetch from database if available
        return self.crawler.get_daily_summary(date)


class StockCategory(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)  # 證券類別


class Stock(models.Model):
    id = models.UUIDField(primary_key=True)
    exchange = \
        models.ForeignKey(Exchange,
                          related_name='stocks', on_delete=models.CASCADE)
    code = models.CharField(max_length=10)  # 證券代號
    description = models.CharField(max_length=255, null=True)  # 證券名稱
    categories = \
        models.ManyToManyField(StockCategory, related_name='stocks')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['exchange', 'code'], name='unique_stock')
        ]

    @staticmethod
    def get_new_record(exchange: Exchange, code: str):
        return Stock(
            id=uuid4(),
            exchange=exchange,
            code=code,
            description=exchange.get_stock_name(code)
        )
