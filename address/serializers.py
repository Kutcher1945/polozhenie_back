from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import CityDistrict, Microsectors, LivingZones

class CityDistrictSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = CityDistrict
        geo_field = "geometry"  # Specify the Geo field for geometry
        fields = ['id', 'name_kz', 'name_ru', 'akim', 'created_at', 'updated_at']
    
    


class MicrosectorsGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Microsectors
        geo_field = "boundary"  # Specify the Geo field
        fields = '__all__'


class LivingZonesGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = LivingZones
        geo_field = "boundary"  # Specify the Geo field
        fields = '__all__'