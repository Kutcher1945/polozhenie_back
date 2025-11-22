from rest_framework import serializers
from .models import Clinics, Country, Region, City, District, Microdistrict


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name_ru', 'name_kz', 'code']


class RegionSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = Region
        fields = ['id', 'name_ru', 'name_kz', 'country']


class CitySerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name_ru', 'name_kz', 'region']


class DistrictSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = District
        fields = ['id', 'name_ru', 'name_kz', 'city']


class MicrodistrictSerializer(serializers.ModelSerializer):
    district = DistrictSerializer(read_only=True)

    class Meta:
        model = Microdistrict
        fields = ['id', 'name_ru', 'name_kz', 'district']


class ClinicsListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка клиник (краткая информация)"""
    city_name = serializers.CharField(source='city.name_ru', read_only=True, default=None)
    district_name = serializers.CharField(source='district.name_ru', read_only=True, default=None)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = Clinics
        fields = [
            'id',
            'name',
            'description',
            'address',
            'city_name',
            'district_name',
            'rating',
            'review_count',
            'working_hours',
            'phones',
            'categories',
            'latitude',
            'longitude',
            'gis2_url',
        ]

    def get_latitude(self, obj):
        if obj.location:
            return obj.location.y
        return None

    def get_longitude(self, obj):
        if obj.location:
            return obj.location.x
        return None


class ClinicsDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о клинике"""
    country = CountrySerializer(read_only=True)
    region = RegionSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    microdistrict = MicrodistrictSerializer(read_only=True)

    class Meta:
        model = Clinics
        fields = [
            'id',
            'name',
            'description',
            'address',
            'address_comment',
            'postal_code',
            'country',
            'region',
            'city',
            'district',
            'microdistrict',
            'administrative_area',
            'working_hours',
            'time_zone',
            'rating',
            'review_count',
            'phones',
            'emails',
            'websites',
            'whatsapp',
            'instagram',
            'categories',
            'gis2_url',
        ]
