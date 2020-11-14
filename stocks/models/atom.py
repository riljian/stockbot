from django.db import models


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
