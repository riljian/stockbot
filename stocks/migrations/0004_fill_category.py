from uuid import uuid4
import time
import logging

from django.db import migrations

from stocks.models.atom import Stock, Exchange, StockCategory
from stocks.helpers.brokerage import TwseBrokerage

logger = logging.getLogger(__name__)


def fill_category(apps, schema_editor):

    exchange = Exchange.objects.get(code='TWSE')
    brokerage: TwseBrokerage = exchange.brokerage

    timeout_counter = 0

    for stock in Stock.objects.filter(exchange=exchange):
        if timeout_counter % 400 == 0:
            time.sleep(5)
        timeout_counter += 1

        stock_meta = brokerage.get_stock_meta(stock.code)
        if stock_meta is None:
            logger.warning(f'stock {stock.code} meta unavailable')
            continue

        try:
            category = StockCategory.objects.get(name=stock_meta.category)
        except StockCategory.DoesNotExist:
            category = StockCategory.objects.create(
                id=uuid4(),
                name=stock_meta.category,
            )
        stock.categories.add(category)


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0003_fill_missing_stock_description'),
    ]

    operations = [
        migrations.RunPython(fill_category)
    ]
