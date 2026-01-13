from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileViewSet, StaffViewSet, ClinicsViewSet, PatientsViewSet, csrf_cookie_view

router = DefaultRouter()
router.register(r'auth', UserViewSet, basename='user')
router.register(r'user-profile', UserProfileViewSet, basename='user-profile')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'clinics', ClinicsViewSet, basename='clinics')
router.register(r'patients', PatientsViewSet, basename='patients')

urlpatterns = [
    path('auth/csrf/', csrf_cookie_view, name='csrf-cookie'),  # 👈 consistent with /auth/ prefix
    path('', include(router.urls)),
]