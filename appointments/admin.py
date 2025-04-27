from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "appointment_time", "status")
    list_filter = ("status", "appointment_time")
    search_fields = ("patient__username", "doctor__username")
