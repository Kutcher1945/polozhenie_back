from rest_framework import serializers
from .models.card101 import Card101
from .models.fire_rank import FireRank
from .models.operation_card import OperationCard
from address.models.district import CityDistrict
from address.serializers import CityDistrictSerializer

class OperationCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationCard
        fields = ['id', 'name_ru', 'name_kz', 'is_deleted', 'created_at', 'updated_at']


class FireRankSerializer(serializers.ModelSerializer):
    class Meta:
        model = FireRank
        fields = ['id', 'name_ru', 'name_kz']


class Card101Serializer(serializers.ModelSerializer):
    # Use the nested serializers for the foreign key fields
    operation_card = OperationCardSerializer(read_only=True)  # Show full operation card details
    district = CityDistrictSerializer(read_only=True)  # Show full district details
    fire_rank = FireRankSerializer(read_only=True)  # Show full fire rank details

    class Meta:
        model = Card101
        fields = '__all__'  # Or list the fields manually