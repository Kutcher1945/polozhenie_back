from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import CityDistrict, Microsectors, LivingZones

class CityDistrictSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = CityDistrict
        geo_field = "geometry"  # Specify the Geo field for geometry
        fields = ['id', 'name_kz', 'name_ru', 'akim', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Structure the response to match GeoJSON format with custom properties
        data['type'] = "Feature"
        data['properties'] = {
            "№": instance.id,  # Field "№" will be populated with the `id` field
            "Наиме": instance.name_ru,  # "Наиме" represents the Russian name field
            "Район": instance.akim.name_ru if instance.akim else None,  # Assuming `akim` has a `name` attribute
            "x": instance.marker.x if instance.marker else None,
            "y": instance.marker.y if instance.marker else None,
        }
        data['geometry'] = {
            "type": "Point",
            "coordinates": [instance.marker.x, instance.marker.y] if instance.marker else [None, None],
        }
        return data


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