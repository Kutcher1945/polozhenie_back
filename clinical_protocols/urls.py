"""
URL Configuration for Clinical Protocols API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClinicalProtocolViewSet, ClinicalProtocolContentViewSet

router = DefaultRouter()
router.register(r'protocols', ClinicalProtocolViewSet, basename='protocol')
router.register(r'protocol-content', ClinicalProtocolContentViewSet, basename='protocol-content')

urlpatterns = [
    path('', include(router.urls)),
]
