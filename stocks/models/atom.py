import datetime
from uuid import uuid4

from caseconverter import pascalcase
import pandas as pd
from django.db import models

import stocks.helpers.crawler as crawlers
import stocks.helpers.brokerage as brokerages


class Exchange(models.Model):
    id = models.UUIDField(primary_key=True)
    code = models.CharField(max_length=10)  # 交易所代號
    calendar_code = \
        models.CharField(max_length=10, null=True)  # trading-calendars 交易所代號
    description = models.CharField(max_length=255, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code'], name='unique_exchange')
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        crawler_cls = getattr(crawlers, pascalcase(f'{self.code} crawler'))
        if crawler_cls is None:
            raise ValueError('crawler not found')
        self._crawler = crawler_cls()

        brokerage_cls = \
            getattr(brokerages, pascalcase(f'{self.code} brokerage'))
        if brokerage_cls is None:
            raise ValueError('brokerage not found')
        self._brokerage = brokerage_cls()

    def get_stock_name(self, code: str) -> str:
        # TODO: fetch from database if available
        return self._brokerage.get_stock_name(code)

    def get_daily_summary(self, date: datetime.date) -> pd.DataFrame:
        # TODO: fetch from database if available
        return self._crawler.get_daily_summary(date)


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
