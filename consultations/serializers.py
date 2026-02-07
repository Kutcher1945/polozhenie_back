from rest_framework import serializers
from .models import Consultation, TimeSlot, AIRecommendationLog
from common.models import User


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for doctor/patient info"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']


class TimeSlotSerializer(serializers.ModelSerializer):
    doctor = UserMinimalSerializer(read_only=True)
    available_spots = serializers.SerializerMethodField()
    can_book = serializers.SerializerMethodField()

    class Meta:
        model = TimeSlot
        fields = [
            'id', 'doctor', 'start_time', 'end_time',
            'is_available', 'max_consultations', 'booked_consultations',
            'available_spots', 'can_book', 'created_at'
        ]
        read_only_fields = ['created_at', 'booked_consultations']

    def get_available_spots(self, obj):
        return obj.max_consultations - obj.booked_consultations

    def get_can_book(self, obj):
        return obj.can_book()


class AIRecommendationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRecommendationLog
        fields = [
            'id', 'symptoms', 'recommended_specialty', 'reason',
            'urgency', 'matched_doctor', 'fallback_used',
            'specialty_not_found', 'created_at'
        ]


class ConsultationSerializer(serializers.ModelSerializer):
    # Patient information
    patient_name = serializers.CharField(source="patient.first_name", read_only=True)
    patient_email = serializers.EmailField(source="patient.email", read_only=True)
    patient_first_name = serializers.CharField(source="patient.first_name", read_only=True)
    patient_last_name = serializers.CharField(source="patient.last_name", read_only=True)

    # Doctor information
    doctor_first_name = serializers.CharField(source="doctor.first_name", read_only=True)
    doctor_last_name = serializers.CharField(source="doctor.last_name", read_only=True)
    doctor_email = serializers.EmailField(source="doctor.email", read_only=True)

    # Related objects
    timeslot = TimeSlotSerializer(read_only=True)
    ai_recommendation = AIRecommendationLogSerializer(read_only=True)

    # Computed fields
    is_scheduled_soon = serializers.SerializerMethodField()
    consultation_type = serializers.SerializerMethodField()

    class Meta:
        model = Consultation
        fields = [
            "id", "patient", "doctor",
            "patient_name", "patient_email", "patient_first_name", "patient_last_name",
            "doctor_first_name", "doctor_last_name", "doctor_email",
            "meeting_id", "access_code", "status", "is_urgent", "scheduled_at",
            "started_at", "ended_at", "created_at",
            "timeslot", "ai_recommendation",
            "is_scheduled_soon", "consultation_type",
            # Consultation form fields
            "complaints", "anamnesis", "diagnostics", "treatment", "diagnosis",
            # Additional consultation data
            "session_notes", "prescription", "recommendations", "transcription"
        ]
        read_only_fields = ["started_at", "ended_at", "created_at", "access_code"]

    def get_is_scheduled_soon(self, obj):
        return obj.is_scheduled_soon() if hasattr(obj, 'is_scheduled_soon') else False

    def get_consultation_type(self, obj):
        if obj.is_urgent:
            return "urgent"
        elif obj.timeslot:
            return "scheduled"
        else:
            return "immediate"