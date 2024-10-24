from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import CityDistrict, Microsectors

class CityDistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = CityDistrict
        fields = ['id', 'name_ru', 'name_kz']  # Add any other fields you need


class MicrosectorsGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Microsectors
        geo_field = "boundary"  # Specify the Geo field
        fields = '__all__'
