from django.db import migrations


def fill_missing_stock_description(apps, schema_editor):
    Stock = apps.get_model('stocks', 'Stock')
    for stock in Stock.objects.filter(description__isnull=True):
        exchange = stock.exchange
        stock.description = exchange.get_stock_name(stock.code)
        stock.save()


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_missing_stock_description)
    ]
