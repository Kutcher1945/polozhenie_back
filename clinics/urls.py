from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClinicsViewSet,
    CountryViewSet,
    RegionViewSet,
    CityViewSet,
    DistrictViewSet,
)

router = DefaultRouter()
router.register(r'clinics', ClinicsViewSet, basename='clinics')
router.register(r'countries', CountryViewSet, basename='countries')
router.register(r'regions', RegionViewSet, basename='regions')
router.register(r'cities', CityViewSet, basename='cities')
router.register(r'districts', DistrictViewSet, basename='districts')

urlpatterns = [
    path('', include(router.urls)),
]
