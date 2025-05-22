from rest_framework import serializers
from .models import HomeAppointment

class HomeAppointmentSerializer(serializers.ModelSerializer):
    doctor_first_name = serializers.CharField(source='doctor.first_name', read_only=True)
    doctor_last_name = serializers.CharField(source='doctor.last_name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)  # only for patient, if you have

    class Meta:
        model = HomeAppointment
        fields = [
            'id',
            'patient', 'patient_name',
            'doctor', 'doctor_first_name', 'doctor_last_name',
            'appointment_time', 'address',
            'status',
            'symptoms',
            'notes',
            'created_at'
        ]
        read_only_fields = ['created_at', 'patient']