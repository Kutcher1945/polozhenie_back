from rest_framework import serializers
from .models.card101 import Card101
from .models.fire_rank import FireRank
from .models.operation_card import OperationCard

class OperationCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationCard
        fields = ['id', 'name_ru', 'name_kz', 'is_deleted', 'created_at', 'updated_at']


class Card101Serializer(serializers.ModelSerializer):
    operation_card = OperationCardSerializer(read_only=True)
    operation_card_id = serializers.PrimaryKeyRelatedField(queryset=OperationCard.objects.all(), write_only=True, source='operation_card')

    class Meta:
        model = Card101
        fields = [
            'id', 'address', 'longitude', 'latitude', 'object_name', 'operation_plan', 
            'constructive_features', 'operation_card', 'operation_card_id', 'year_of_construction', 
            'object_area', 'district', 'floors', 'fire_floor', 'applicant_name', 
            'applicant_phone', 'danger_to_people', 'additional_info', 'created_at', 'updated_at'
        ]

class FireRankSerializer(serializers.ModelSerializer):
    class Meta:
        model = FireRank
        fields = ['id', 'name_ru', 'name_kz']
