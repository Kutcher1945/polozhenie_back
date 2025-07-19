from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileViewSet, csrf_cookie_view

router = DefaultRouter()
router.register(r'auth', UserViewSet, basename='user')
router.register(r'user-profile', UserProfileViewSet, basename='user-profile')

urlpatterns = [
    path('csrf-cookie/', csrf_cookie_view, name='csrf-cookie'),  # ✅ Explicit CSRF cookie route
    path('', include(router.urls)),
]