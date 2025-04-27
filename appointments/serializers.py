from rest_framework import serializers
from .models import Appointment

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'appointment_time', 'status', 'symptoms', 'notes', 'created_at'
        ]
        read_only_fields = ['created_at', 'patient']
