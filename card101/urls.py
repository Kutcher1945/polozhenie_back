from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import Card101ViewSet, OperationCardViewSet, FireRankViewSet, FireStationsViewSet

router = DefaultRouter()
router.register(
    prefix='operation-cards', viewset=OperationCardViewSet, basename='operation-cards'
)
router.register(
    prefix='fire-ranks', viewset=FireRankViewSet, basename='fire-ranks'
)
router.register(
    prefix='card101', viewset=Card101ViewSet, basename='card101'
)
router.register(
    prefix='fire-stations', viewset=FireStationsViewSet, basename='fire-stations'
)

urlpatterns = router.urls
