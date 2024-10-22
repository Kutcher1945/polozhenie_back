from rest_framework.routers import DefaultRouter
from .views import CityDistrictViewSet

router = DefaultRouter()
router.register(
    prefix='city-districts', viewset=CityDistrictViewSet, basename='city-districts'
)

urlpatterns = router.urls