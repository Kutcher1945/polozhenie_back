from rest_framework import serializers
from .models import Consultation

class ConsultationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.first_name", read_only=True)
    patient_email = serializers.EmailField(source="patient.email", read_only=True)
    doctor_first_name = serializers.CharField(source="doctor.first_name", read_only=True)
    doctor_last_name = serializers.CharField(source="doctor.last_name", read_only=True)

    class Meta:
        model = Consultation
        fields = [
            "id", "patient", "doctor",
            "patient_name", "patient_email",
            "doctor_first_name", "doctor_last_name",  # ✅ Добавлено
            "meeting_id", "status", "started_at", "ended_at", "created_at"
        ]
        read_only_fields = ["started_at", "ended_at", "created_at"]