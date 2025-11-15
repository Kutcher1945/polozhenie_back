from rest_framework import serializers
from .models import HomeAppointment

class HomeAppointmentSerializer(serializers.ModelSerializer):
    doctor_first_name = serializers.CharField(source='doctor.first_name', read_only=True)
    doctor_last_name = serializers.CharField(source='doctor.last_name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    patient_first_name = serializers.CharField(source='patient.first_name', read_only=True)
    patient_last_name = serializers.CharField(source='patient.last_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone_number', read_only=True)
    nurse_first_name = serializers.CharField(source='nurse.first_name', read_only=True)
    nurse_last_name = serializers.CharField(source='nurse.last_name', read_only=True)

    class Meta:
        model = HomeAppointment
        fields = [
            'id',
            'patient', 'patient_name', 'patient_first_name', 'patient_last_name', 'patient_phone',
            'doctor', 'doctor_first_name', 'doctor_last_name',
            'nurse', 'nurse_first_name', 'nurse_last_name',
            'appointment_time', 'address',
            'status',
            'symptoms',
            'notes',
            'created_at'
        ]
        read_only_fields = ['created_at', 'patient']