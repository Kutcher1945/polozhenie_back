from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import Card101ViewSet, OperationCardViewSet, FireRankViewSet

router = DefaultRouter()
router.register(
    prefix='operation-card', viewset=OperationCardViewSet, basename='operation-card'
)
router.register(
    prefix='fire-rank', viewset=FireRankViewSet, basename='fire-rank'
)
router.register(
    prefix='card101', viewset=Card101ViewSet, basename='card101'
)

urlpatterns = router.urls
