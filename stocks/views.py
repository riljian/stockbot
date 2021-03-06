import logging

import pandas as pd
from caseconverter import pascalcase

from rest_framework import viewsets, response, decorators

from stocks.models import Stock
import stocks.helpers.operator as operators

logger = logging.getLogger(__name__)


class StockViewSet(viewsets.ViewSet):

    queryset = Stock.objects.all()

    @staticmethod
    def parse_operator(value: str) -> operators.Operator:
        operator_cls = getattr(operators, pascalcase(f'{value} operator'))

        if operator_cls is None:
            raise ValueError('operator not found')

        return operator_cls()

    @decorators.action(detail=False, methods=['get'])
    def day_trading_candidates(self, request):
        exchange_code = request.query_params.get('exchange')
        date = pd.to_datetime(request.query_params.get('date'), utc=True)
        operator = self.parse_operator(exchange_code)

        if date not in operator.analyzer.calendar.opens:
            logger.info('%s is closed on %s', exchange_code, date)
            return response.Response({'data': []})

        candidates = operator.get_day_trade_candidates(date)
        return response.Response({'data': candidates.mask(candidates.isnull(), None).to_dict('records')})
