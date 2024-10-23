from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, DjangoModelPermissions
from django.db.models import Q
from .models.operation_card import OperationCard
from .models.card101 import Card101
from .models.fire_rank import FireRank
from .serializers import Card101Serializer, OperationCardSerializer, FireRankSerializer
from common.helpers.pagination import CustomPagination

class OperationCardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OperationCard.objects.filter(is_deleted=False)
    serializer_class = OperationCardSerializer
    permission_classes = []  # Add your permissions here


class Card101ViewSet(viewsets.ModelViewSet):
    queryset = Card101.objects.all().order_by('-id')  # Ordering by id in descending order (latest first)
    serializer_class = Card101Serializer
    pagination_class = CustomPagination  # Custom pagination class
    permission_classes = []  # Example permissions

    # Custom action for searching
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        search_query = request.query_params.get('q', None)
        queryset = self.get_queryset()

        if search_query:
            queryset = queryset.filter(Q(address__icontains=search_query))  # Case-insensitive search

        page = self.paginate_queryset(queryset)  # Paginate the queryset
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class FireRankViewSet(viewsets.ModelViewSet):
    queryset = FireRank.objects.all()
    serializer_class = FireRankSerializer
    permission_classes = []  # Add your permissions here
