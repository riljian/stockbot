import logging

import pandas as pd
from trading_calendars import get_calendar

from django.db import models

from stocks.models import DailySummary, Exchange

logger = logging.getLogger(__name__)


class Analyzer:

    def __init__(self, exchange):
        self._exchange = exchange

    def get_day_trading_conditions(self) -> dict:
        pass

    def get_day_trading_candidates(self, date_text: str) -> models.QuerySet:
        calendar = get_calendar(self._exchange.calendar_code)
        date = pd.to_datetime(date_text, utc=True)
        if date not in calendar.opens:
            logger.info('%s is closed on %s', self._exchange.code, date)
            return DailySummary.objects.none()
        prev_trading_close = calendar.previous_close(date)
        prev_trading_date = prev_trading_close.date()
        base_trading_date = calendar.previous_close(prev_trading_close).date()
        base_closing_price = (DailySummary.objects
                              .filter(stock=models.OuterRef('stock'), date=base_trading_date)
                              .values('closing_price')[:1])
        return (DailySummary.objects
                .filter(date=prev_trading_date)
                .annotate(
                    base_closing_price=models.Subquery(base_closing_price),
                    stock_code=models.F('stock__code')
                )
                .annotate(change=models.F('closing_price') - models.F('base_closing_price'))
                .annotate(change_rate=models.F('change') / models.F('base_closing_price'))
                .filter(**self.get_day_trading_conditions()))


class TwseAnalyzer(Analyzer):

    def __init__(self):
        super().__init__(Exchange.objects.get(code='TWSE'))

    def get_day_trading_conditions(self):
        return {
            'closing_price__gte': 5,
            'closing_price__lte': 30,
            'change_rate__gte': 0.04,
            'trade_volume__gte': 50000000,
        }
