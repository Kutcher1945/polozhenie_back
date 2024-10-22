from rest_framework import viewsets
from rest_framework.response import Response
from .models import CityDistrict
from .serializers import CityDistrictSerializer  # You need to create a serializer

class CityDistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A simple ViewSet for viewing CityDistricts.
    """
    queryset = CityDistrict.objects.all()
    serializer_class = CityDistrictSerializer
