"""
Public endpoints accessible without authentication
"""
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from ..models import User


class PublicViewSet(ViewSet):
    """
    Public endpoints that don't require authentication
    """
    permission_classes = []

    @swagger_auto_schema(
        operation_description="Get available doctors",
        responses={200: "List of available doctors"},
    )
    @action(detail=False, methods=["get"], url_path="doctors/available")
    def get_available_doctors(self, request):
        """Fetch a list of available doctors (only those with availability_status='available')."""
        doctors = User.objects.filter(
            role="doctor",
            is_active=True,
            doctor_profile__availability_status='available'  # ✅ Only return available doctors
        ).select_related(
            'doctor_profile',
            'doctor_profile__clinic',
            'doctor_profile__clinic__city',
            'doctor_profile__specialization'
        )

        if not doctors.exists():
            return Response(
                {"error": "No available doctors found."},
                status=status.HTTP_404_NOT_FOUND
            )

        language = request.GET.get('lang', 'ru')

        doctor_list = []
        for doctor in doctors:
            doctor_profile = getattr(doctor, 'doctor_profile', None)

            if not doctor_profile:
                continue

            # Get specialization in requested language
            specialization = "Специальность не указана"
            if doctor_profile.specialization:
                if language == 'kz':
                    specialization = doctor_profile.specialization.name_kz
                elif language == 'en':
                    specialization = doctor_profile.specialization.name_en
                else:
                    specialization = doctor_profile.specialization.name_ru
            elif doctor_profile.doctor_type:
                specialization = doctor_profile.doctor_type

            # Get clinic information
            clinic_data = None
            if doctor_profile.clinic:
                clinic = doctor_profile.clinic
                clinic_data = {
                    "id": clinic.id,
                    "name": clinic.name,
                    "address": clinic.address or None,
                    "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                    "city": clinic.city.name_ru if clinic.city else None,
                }

            doctor_list.append({
                "id": doctor.id,
                "name": f"{doctor.first_name} {doctor.last_name}",
                "email": doctor.email,
                "doctor_type": specialization,
                "availability_status": doctor_profile.availability_status or 'offline',
                "availability_note": doctor_profile.availability_note or '',
                "language": doctor.language or 'ru',
                "years_of_experience": doctor_profile.years_of_experience,
                "online_consultation_price": str(doctor_profile.online_consultation_price) if doctor_profile.online_consultation_price else None,
                "work_schedule": doctor_profile.work_schedule,
                "clinic": clinic_data,
                "specialization": {
                    "id": doctor_profile.specialization.id if doctor_profile.specialization else None,
                    "name_ru": doctor_profile.specialization.name_ru if doctor_profile.specialization else None,
                    "name_kz": doctor_profile.specialization.name_kz if doctor_profile.specialization else None,
                    "name_en": doctor_profile.specialization.name_en if doctor_profile.specialization else None,
                } if doctor_profile.specialization else None
            })

        return Response({"doctors": doctor_list}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Get available nurses",
        responses={200: "List of available nurses"},
    )
    @action(detail=False, methods=["get"], url_path="nurses/available")
    def get_available_nurses(self, request):
        """Fetch a list of available nurses."""
        nurses = User.objects.filter(
            role="nurse",
            is_active=True
        ).select_related(
            'nurse_profile',
            'nurse_profile__clinic',
            'nurse_profile__clinic__city',
            'nurse_profile__specialization'
        )

        if not nurses.exists():
            return Response(
                {"error": "No available nurses found."},
                status=status.HTTP_404_NOT_FOUND
            )

        language = request.GET.get('lang', 'ru')

        nurse_list = []
        for nurse in nurses:
            nurse_profile = getattr(nurse, 'nurse_profile', None)

            if not nurse_profile:
                continue

            # Get specialization in requested language
            specialization = "Специальность не указана"
            if nurse_profile.specialization:
                if language == 'kz':
                    specialization = nurse_profile.specialization.name_kz
                elif language == 'en':
                    specialization = nurse_profile.specialization.name_en
                else:
                    specialization = nurse_profile.specialization.name_ru
            elif nurse_profile.nurse_type:
                specialization = nurse_profile.nurse_type

            # Get clinic information
            clinic_data = None
            if nurse_profile.clinic:
                clinic = nurse_profile.clinic
                clinic_data = {
                    "id": clinic.id,
                    "name": clinic.name,
                    "address": clinic.address or None,
                    "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                    "city": clinic.city.name_ru if clinic.city else None,
                }

            nurse_list.append({
                "id": nurse.id,
                "name": f"{nurse.first_name} {nurse.last_name}",
                "email": nurse.email,
                "nurse_type": specialization,
                "availability_status": nurse_profile.availability_status or 'offline',
                "availability_note": nurse_profile.availability_note or '',
                "clinic": clinic_data,
                "specialization": {
                    "id": nurse_profile.specialization.id if nurse_profile.specialization else None,
                    "name_ru": nurse_profile.specialization.name_ru if nurse_profile.specialization else None,
                    "name_kz": nurse_profile.specialization.name_kz if nurse_profile.specialization else None,
                    "name_en": nurse_profile.specialization.name_en if nurse_profile.specialization else None,
                } if nurse_profile.specialization else None
            })

        return Response({"nurses": nurse_list}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Get user profile field choices",
        responses={200: "List of field choices for user profile"},
    )
    @action(detail=False, methods=["get"], url_path="profile/choices")
    def get_profile_choices(self, request):
        """Get all available choices for user profile fields."""
        choices = {
            "gender_choices": [{"value": key, "label": value} for key, value in User.GENDER_CHOICES],
            "language_choices": [{"value": key, "label": value} for key, value in User.LANGUAGE_CHOICES],
            "marital_status_choices": [{"value": key, "label": value} for key, value in User.MARITAL_STATUS_CHOICES],
            "blood_type_choices": [{"value": key, "label": value} for key, value in User.BLOOD_TYPE_CHOICES],
            "role_choices": [{"value": key, "label": value} for key, value in User.ROLE_CHOICES],
        }
        return Response(choices, status=status.HTTP_200_OK)
