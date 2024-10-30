from rest_framework import viewsets
from rest_framework.response import Response
from django.db.models import Func
from django.contrib.gis.db.models import GeometryField  # Import the correct GeometryField
from .models import CityDistrict, Microsectors, LivingZones
from .serializers import CityDistrictSerializer, MicrosectorsGeoSerializer, LivingZonesGeoSerializer  # You need to create a serializer

class Simplify(Func):
    function = 'ST_Simplify'
    output_field = GeometryField()  # Use GeometryField from django.contrib.gis.db.models

class CityDistrictViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CityDistrict.objects.annotate(simplified_geometry=Simplify('geometry', 0.01))  # Adjust tolerance as needed
    serializer_class = CityDistrictSerializer


class LivingZonesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LivingZones.objects.annotate(simplified_geometry=Simplify('boundary', 0.01))  # Adjust tolerance as needed
    serializer_class = LivingZonesGeoSerializer


class MicrosectorsGeoViewSet(viewsets.ModelViewSet):
    queryset = Microsectors.objects.all()
    serializer_class = MicrosectorsGeoSerializer
