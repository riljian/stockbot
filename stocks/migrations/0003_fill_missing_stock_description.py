import logging

from django.db import migrations

from stocks.models.atom import Stock, Exchange

logger = logging.getLogger(__name__)


def fill_missing_stock_description(apps, schema_editor):
    candidates = {}

    for stock in Stock.objects.filter(description__isnull=True):
        exchange = stock.exchange
        stock_code = stock.code
        cached_stock_name = candidates.get(stock_code)
        if cached_stock_name:
            logger.debug('cache hit for %s(%s)', stock_code, cached_stock_name)
            stock.description = cached_stock_name
            stock.save()
            continue
        crawler_cls = Exchange.get_stock_crawler_class(exchange.code)
        crawler = crawler_cls()
        candidates = {
            **candidates,
            **crawler.load_stock_candidates_by_partial_code(stock_code[:2]),
        }
        logger.debug('cache miss for %s(%s)',
                     stock_code, candidates[stock_code])
        stock.description = candidates[stock_code]
        stock.save()


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0002_auto_20210116_0940'),
    ]

    operations = [
        migrations.RunPython(fill_missing_stock_description)
    ]
