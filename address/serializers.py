from rest_framework import serializers
from .models import CityDistrict

class CityDistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = CityDistrict
        fields = ['id', 'name_ru', 'name_kz']  # Add any other fields you need
