from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HomeAppointmentViewSet

router = DefaultRouter()
router.register(r'appointments', HomeAppointmentViewSet, basename='appointments')

urlpatterns = [
    path('', include(router.urls)),
]