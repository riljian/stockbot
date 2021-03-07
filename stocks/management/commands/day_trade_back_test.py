import logging

import pandas as pd
from django.core.management.base import BaseCommand

from stocks.helpers import backtest as backtests

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    FROM_KEY = 'from'
    TO_KEY = 'to'

    help = 'Day trade back test'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(f'--{self.FROM_KEY}', required=True)
        parser.add_argument(f'--{self.TO_KEY}', required=True)

    def handle(self, *args, **options):
        from_ts = pd.to_datetime(options.get(self.FROM_KEY))
        to_ts = pd.to_datetime(options.get(self.TO_KEY))

        backtest = backtests.TwseDayTradeBackTest()
        backtest.start(from_ts, to_ts)
