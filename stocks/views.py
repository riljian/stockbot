import logging

import pandas as pd
from caseconverter import pascalcase

from rest_framework import viewsets, response, decorators
from rest_framework import serializers

from stocks.models import Stock
import stocks.helpers.operator as operators

logger = logging.getLogger(__name__)


class StockCategoryNameField(serializers.CharField):

    def to_representation(self, value):
        return value.name


class StockSerializer(serializers.ModelSerializer):
    categories = serializers.ListSerializer(child=StockCategoryNameField())

    class Meta:
        model = Stock
        fields = ('code', 'description', 'categories')


class StockViewSet(viewsets.ViewSet):
    queryset = Stock.objects.all()

    @staticmethod
    def parse_operator(value: str) -> operators.Operator:
        operator_cls = getattr(operators, pascalcase(f'{value} operator'))

        if operator_cls is None:
            raise ValueError('operator not found')

        return operator_cls()

    def retrieve(self, request, exchange_code, pk):
        stock = self.queryset.get(exchange__code=exchange_code, code=pk)
        serializer = StockSerializer(stock)
        return response.Response({'data': serializer.data})

    @decorators.action(detail=False, methods=['get'])
    def conservative_candidates(self, request, exchange_code):
        date = pd.to_datetime(request.query_params.get('date'), utc=True)
        operator = self.parse_operator(f'conservative {exchange_code}')

        candidates = operator.get_candidates(date)
        return response.Response({'data': candidates.mask(candidates.isnull(), None).to_dict('records')})

    @decorators.action(detail=False, methods=['get'])
    def day_trading_candidates(self, request, exchange_code):
        date = pd.to_datetime(request.query_params.get('date'), utc=True)
        operator = self.parse_operator(f'day trade {exchange_code}')

        if date not in operator.analyzer.calendar.opens:
            logger.info('%s is closed on %s', exchange_code, date)
            return response.Response({'data': []})

        candidates = operator.get_candidates(date)
        return response.Response({'data': candidates.mask(candidates.isnull(), None).to_dict('records')})
