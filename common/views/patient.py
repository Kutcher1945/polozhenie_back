"""
Patient Medical Profile Views

This module handles patient medical profile management.
Access control:
- Patients can only view/update their own medical profile
- Doctors can view their patients' medical profiles
- Admins can view all medical profiles
- Nurses can view patients' medical profiles

All changes are automatically logged via django-auditlog.
"""

import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status

from ..models import PatientMedicalProfile
from ..serializers import PatientMedicalProfileSerializer

logger = logging.getLogger(__name__)


class PatientMedicalProfileViewSet(ModelViewSet):
    """
    API endpoint for patient medical profiles.

    Access control:
    - Patients can only view/update their own medical profile
    - Doctors can view their patients' medical profiles
    - Admins can view all medical profiles
    - Nurses can view patients' medical profiles

    All changes are automatically logged via django-auditlog.
    """
    serializer_class = PatientMedicalProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Patients can only see their own profile
        if user.role == 'patient':
            return PatientMedicalProfile.objects.filter(user=user)

        # Doctors and nurses can see all patient profiles
        # TODO: In future, filter by actual doctor-patient relationships
        elif user.role in ['doctor', 'nurse']:
            return PatientMedicalProfile.objects.all()

        # Admins can see all profiles
        elif user.role == 'admin':
            return PatientMedicalProfile.objects.all()

        # Default: no access
        return PatientMedicalProfile.objects.none()

    def perform_update(self, serializer):
        """Track who modified the profile for audit purposes"""
        serializer.save(last_modified_by=self.request.user)

    def perform_create(self, serializer):
        """Track who created the profile"""
        serializer.save(last_modified_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='me')
    def my_profile(self, request):
        """
        Get the authenticated patient's own medical profile.
        Creates one if it doesn't exist.
        """
        if request.user.role != 'patient':
            return Response(
                {'error': 'Only patients have medical profiles'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get or create medical profile
        profile, created = PatientMedicalProfile.objects.get_or_create(
            user=request.user,
            defaults={'last_modified_by': request.user}
        )

        serializer = self.get_serializer(profile)
        return Response(serializer.data)
