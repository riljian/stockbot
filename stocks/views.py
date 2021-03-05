from typing import Tuple

import pandas as pd
from caseconverter import pascalcase

from rest_framework import viewsets, response, decorators

from stocks.models import Exchange, Stock
import stocks.helpers.analyzer as analyzers


class StockViewSet(viewsets.ViewSet):

    queryset = Stock.objects.all()

    @staticmethod
    def parse_exchange(value: str) -> Tuple[Exchange, analyzers.Analyzer]:
        analyzer_cls = getattr(analyzers, pascalcase(f'{value} analyzer'))

        if analyzer_cls is None:
            raise ValueError('analyzer not found')

        return Exchange.objects.get(code=value), analyzer_cls()

    @decorators.action(detail=False, methods=['get'])
    def day_trading_candidates(self, request):
        exchange_code = request.query_params.get('exchange')
        date = pd.to_datetime(request.query_params.get('date'), utc=True)
        _, analyzer = self.parse_exchange(exchange_code)
        candidates = analyzer.get_day_trading_candidates(date)
        data = candidates.where(~candidates.isnull(), None).to_dict('records')
        return response.Response({'data': data})
