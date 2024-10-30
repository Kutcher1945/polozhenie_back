from rest_framework.routers import DefaultRouter
from .views import CityDistrictViewSet, MicrosectorsGeoViewSet, LivingZonesViewSet

router = DefaultRouter()
router.register(
    prefix='city-districts', viewset=CityDistrictViewSet, basename='city-districts'
)
router.register(
    prefix='city-microsectors', viewset=MicrosectorsGeoViewSet, basename='city-microsectors'
)
router.register(
    prefix='city-living-zones', viewset=LivingZonesViewSet, basename='city-living-zones'
)

urlpatterns = router.urls