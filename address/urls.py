from rest_framework.routers import DefaultRouter
from .views import CityDistrictViewSet, MicrosectorsGeoViewSet

router = DefaultRouter()
router.register(
    prefix='city-districts', viewset=CityDistrictViewSet, basename='city-districts'
)
router.register(
    prefix='city-microsectors', viewset=MicrosectorsGeoViewSet, basename='city-microsectors'
)

urlpatterns = router.urls