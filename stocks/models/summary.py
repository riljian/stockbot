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
    foreign_dealer_buy_volume = models.IntegerField(null=True)  # 外資買入
    foreign_dealer_sell_volume = models.IntegerField(null=True)  # 外資賣出
    investment_trust_buy_volume = models.IntegerField(null=True)  # 投信買入
    investment_trust_sell_volume = models.IntegerField(null=True)  # 投信賣出
    local_dealer_proprietary_buy_volume = models.IntegerField(null=True)  # 自營商(自有)買入
    local_dealer_proprietary_sell_volume = models.IntegerField(null=True)  # 自營商(自有)賣出
    local_dealer_hedge_buy_volume = models.IntegerField(null=True)  # 自營商(避險)買入
    local_dealer_hedge_sell_volume = models.IntegerField(null=True)  # 自營商(避險)賣出

    class Meta:
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['-date', 'stock']),
        ]


class BackTestRecord(models.Model):
    id = models.UUIDField(primary_key=True)
    no = models.UUIDField()
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    price = models.FloatField()
    volume = models.IntegerField()
    ts = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['no']),
            models.Index(fields=['no', 'stock']),
        ]
