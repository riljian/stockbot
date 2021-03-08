import logging

import pandas as pd
from django.db import migrations

from stocks.helpers import crawler as crawlers
from stocks.models import DailySummary

logger = logging.getLogger(__name__)


def fill_investor_summary(apps, schema_editor):
    from_date = pd.to_datetime('2004-02-11T00:00:00Z')
    to_date = pd.to_datetime('2021-03-08T00:00:00Z')
    crawler = crawlers.TwseCrawler()
    for date in pd.date_range(from_date, to_date, freq='D'):
        date_txt = date.strftime('%Y%m%d')
        try:
            df = crawler.get_daily_investor_summary(date)
            for stock_code, summary in df.iterrows():
                DailySummary.objects.filter(stock__code=stock_code, date=date).update(**summary)
            logger.info(f'Successful to fill investor summary on {date_txt}')
        except Exception:
            logger.exception(f'Failed to fill investor summary on {date_txt}')


class Migration(migrations.Migration):
    dependencies = [
        ('stocks', '0010_auto_20210308_1418'),
    ]

    operations = [
        migrations.RunPython(fill_investor_summary),
    ]
