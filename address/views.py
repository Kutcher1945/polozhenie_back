from rest_framework import viewsets
from rest_framework.response import Response
from .models import CityDistrict, Microsectors
from .serializers import CityDistrictSerializer, MicrosectorsGeoSerializer  # You need to create a serializer


class CityDistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A simple ViewSet for viewing CityDistricts.
    """
    queryset = CityDistrict.objects.all()
    serializer_class = CityDistrictSerializer


class MicrosectorsGeoViewSet(viewsets.ModelViewSet):
    queryset = Microsectors.objects.all()
    serializer_class = MicrosectorsGeoSerializer
