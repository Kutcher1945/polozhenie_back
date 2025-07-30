from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsultationViewSet, csrf_token_view

router = DefaultRouter()
router.register(r'consultations', ConsultationViewSet, basename='consultations')

urlpatterns = [
    path('', include(router.urls)),
    path("csrf/", csrf_token_view, name="csrf_token_view"),
]
