import logging
from typing import Tuple

import pandas as pd
from caseconverter import pascalcase

from rest_framework import viewsets, response, decorators

from stocks.models import Exchange, Stock
import stocks.helpers.analyzer as analyzers

logger = logging.getLogger(__name__)


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
        exchange, analyzer = self.parse_exchange(exchange_code)

        if date not in analyzer.calendar.opens:
            logger.info('%s is closed on %s', exchange.code, date)
            return response.Response({'data': []})

        prev_trading_close = analyzer.calendar.previous_close(date)
        df = analyzer.get_stocks()
        volume_filter, volume_result = \
            analyzer.get_trade_volume_filter(df, prev_trading_close, min_volume=50000000)
        price_filter, price_result = \
            analyzer.get_price_filter(df, prev_trading_close, min_price=5.0, max_price=30.0)
        price_change_rate_filter, price_change_rate_result = \
            analyzer.get_price_change_rate_filter(df, prev_trading_close, min_change_rate=0.04, days=1)

        result = pd.concat([df, volume_result, price_result, price_change_rate_result], axis=1)
        candidates = result[volume_filter & price_filter & price_change_rate_filter]
        data = candidates.where(~candidates.isnull(), None).to_dict('records')
        return response.Response({'data': data})
