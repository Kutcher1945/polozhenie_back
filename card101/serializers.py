from rest_framework import serializers
from .models.card101 import Card101
from .models.fire_rank import FireRank
from .models.operation_card import OperationCard
from address.models.district import CityDistrict
from address.serializers import CityDistrictSerializer
from .models.fire_stations import FireStations

class OperationCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationCard
        fields = ['id', 'name_ru', 'name_kz', 'is_deleted', 'created_at', 'updated_at']


class FireRankSerializer(serializers.ModelSerializer):
    class Meta:
        model = FireRank
        fields = ['id', 'name_ru', 'name_kz']


class Card101Serializer(serializers.ModelSerializer):
    # These fields accept the IDs for operation_card, district, and fire_rank
    operation_card_id = serializers.PrimaryKeyRelatedField(queryset=OperationCard.objects.all(), source='operation_card', write_only=True)
    district_id = serializers.PrimaryKeyRelatedField(queryset=CityDistrict.objects.all(), source='district', write_only=True)
    fire_rank_id = serializers.PrimaryKeyRelatedField(queryset=FireRank.objects.all(), source='fire_rank', write_only=True)

    # Existing nested serializers for read-only views
    operation_card = OperationCardSerializer(read_only=True)
    district = CityDistrictSerializer(read_only=True)
    fire_rank = FireRankSerializer(read_only=True)

    class Meta:
        model = Card101
        fields = '__all__'


class FireStationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FireStations
        geo_field = "location"  # Specify the Geo field
        fields = [
            'id',
            'name_ru',
            'name_kz',
            'old_name_ru',
            'old_name_ru',
            'use_in_recommendations',
            'use_in_records',
            'district',
            'sort_order',
            'address',
            'location',
            'is_deleted',
            'created_at',
            'updated_at'
        ]
