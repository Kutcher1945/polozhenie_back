from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, UserProfileViewSet, StaffViewSet,
    ClinicsViewSet, PatientsViewSet, SessionViewSet, ReportsViewSet, ScheduleViewSet,
    PatientMedicalProfileViewSet, PublicViewSet, csrf_cookie_view
)

router = DefaultRouter()
router.register(r'auth', UserViewSet, basename='user')
router.register(r'user-profile', UserProfileViewSet, basename='user-profile')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'clinics', ClinicsViewSet, basename='clinics')
router.register(r'patients', PatientsViewSet, basename='patients')
router.register(r'sessions', SessionViewSet, basename='sessions')
router.register(r'reports', ReportsViewSet, basename='reports')
router.register(r'schedule', ScheduleViewSet, basename='schedule')
router.register(r'medical-profiles', PatientMedicalProfileViewSet, basename='medical-profile')
router.register(r'public', PublicViewSet, basename='public')  # ✅ Public endpoints

urlpatterns = [
    path('auth/csrf/', csrf_cookie_view, name='csrf-cookie'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),  # JWT refresh endpoint
    path('', include(router.urls)),
]