"""
Views package - organized by user role

This provides backward compatibility while migrating to organized structure
"""

# ===== NEW STRUCTURE (organized by role) =====
from .auth import csrf_cookie_view, AuthViewSet
from .public import PublicViewSet
from .doctor import DoctorViewSet
from .nurse import NurseViewSet
from .profile import UserProfileViewSet
from .sessions import SessionViewSet
from .patient import PatientMedicalProfileViewSet
from .admin import (
    StaffViewSet,
    ClinicsViewSet,
    PatientsViewSet,
    ReportsViewSet,
    ScheduleViewSet,
)

# Map AuthViewSet to UserViewSet for backward compatibility
UserViewSet = AuthViewSet

# Expose everything at package level
__all__ = [
    # Functions
    'csrf_cookie_view',

    # New viewsets (organized by role)
    'AuthViewSet',
    'UserViewSet',  # Alias for backward compatibility
    'PublicViewSet',
    'DoctorViewSet',
    'NurseViewSet',

    # Profile and sessions viewsets
    'UserProfileViewSet',
    'SessionViewSet',
    'PatientMedicalProfileViewSet',

    # Admin viewsets
    'StaffViewSet',
    'ClinicsViewSet',
    'PatientsViewSet',
    'ReportsViewSet',
    'ScheduleViewSet',
]
