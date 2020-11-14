from django.db import models

from .atom import Stock


class DailySummary(models.Model):
    id = models.UUIDField(primary_key=True)
    date = models.DateField()
    stock = models.ForeignKey(
        Stock, related_name='daily_summaries', on_delete=models.CASCADE)
    trade_volume = models.IntegerField(null=True)  # 成交股數
    transaction = models.IntegerField(null=True)  # 成交筆數
    trade_value = models.BigIntegerField(null=True)  # 成交金額
    opening_price = models.FloatField(null=True)  # 開盤價
    highest_price = models.FloatField(null=True)  # 最高價
    lowest_price = models.FloatField(null=True)  # 最低價
    closing_price = models.FloatField(null=True)  # 收盤價
    last_best_bid_price = models.FloatField(null=True)  # 最後揭示買價
    last_best_bid_volume = models.IntegerField(null=True)  # 最後揭示買量
    last_best_ask_price = models.FloatField(null=True)  # 最後揭示賣價
    last_best_ask_volume = models.IntegerField(null=True)  # 最後揭示賣量
