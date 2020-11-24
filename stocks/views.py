from typing import Tuple

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
        date_text = request.query_params.get('date')
        _, analyzer = self.parse_exchange(exchange_code)
        candidates = analyzer.get_day_trading_candidates(date_text)
        return response.Response({'data': candidates.values()})
