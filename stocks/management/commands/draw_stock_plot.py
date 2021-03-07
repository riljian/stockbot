import logging

import pandas as pd
from django.core.management.base import BaseCommand

from stocks.helpers import analyzer as analyzers
from stocks.models import Stock, Exchange

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    EXCHANGE_KEY = 'exchange'
    STOCK_KEY = 'stock'
    FROM_KEY = 'from'
    TO_KEY = 'to'

    help = 'Draw stock plot'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        exchange_choices = [
            exchange.code for exchange in Exchange.objects.all()
        ]
        stock_choices = [
            stock.code for stock in Stock.objects.all()
        ]
        parser.add_argument(f'--{self.EXCHANGE_KEY}',
                            required=True, choices=exchange_choices)
        parser.add_argument(f'--{self.STOCK_KEY}',
                            required=True, choices=stock_choices)
        parser.add_argument(f'--{self.FROM_KEY}', required=True)
        parser.add_argument(f'--{self.TO_KEY}', required=True)

    def handle(self, *args, **options):
        exchange_code = options[self.EXCHANGE_KEY]
        stock_code = options[self.STOCK_KEY]
        from_ts = pd.to_datetime(options.get(self.FROM_KEY))
        to_ts = pd.to_datetime(options.get(self.TO_KEY))

        stock = Stock.objects.get(code=stock_code, exchange__code=exchange_code)
        analyzer = analyzers.TwseAnalyzer()
        kbars = analyzer.get_technical_indicator_filled_kbars(stock, from_ts, to_ts)
        analyzer.draw_plot(stock.description, kbars)
