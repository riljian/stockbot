import logging

import requests
import lxml.html

from django.db import migrations

from stocks.models import StockCategory

logger = logging.getLogger(__name__)


def fill_category_name(apps, schema_editor):

    twse_page_url = 'https://www.twse.com.tw/zh/page/trading/exchange/MI_INDEX.html'
    response = requests.request(url=twse_page_url, method='get')
    html = lxml.html.fromstring(response.text)
    option_xpath = '/html/body/div[1]/div[1]/div/div/main/div[2]/div/div/form/select/option'
    for option in html.xpath(option_xpath):
        brokerage_code, name = option.attrib['value'], option.text
        StockCategory.objects.filter(
            brokerage_code=brokerage_code).update(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0005_stockcategory_brokerage_code'),
    ]

    operations = [
        migrations.RunPython(fill_category_name)
    ]
