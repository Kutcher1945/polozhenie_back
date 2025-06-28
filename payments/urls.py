from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payments.views import HomeAppointmentKaspiPaymentViewSet

router = DefaultRouter()
router.register(r"kaspi-payments", HomeAppointmentKaspiPaymentViewSet, basename="kaspi-home")

urlpatterns = [
    path("", include(router.urls)),
]
