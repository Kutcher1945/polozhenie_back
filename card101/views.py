from rest_framework import viewsets
from .models.operation_card import OperationCard
from .models.card101 import Card101
from .models.fire_rank import FireRank
from .serializers import Card101Serializer, OperationCardSerializer

class OperationCardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OperationCard.objects.filter(is_deleted=False)
    serializer_class = OperationCardSerializer
    permission_classes = []  # Add your permissions here


class Card101ViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Card101.objects.all()
    serializer_class = Card101Serializer
    permission_classes = []  # Add your permissions here


class FireRankViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FireRank.objects.all()
    serializer_class = Card101Serializer
    permission_classes = []  # Add your permissions here