from django.contrib import admin
from .models import HomeAppointment

@admin.register(HomeAppointment)
class HomeAppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "appointment_time", "status")
    list_filter = ("status", "appointment_time")
    search_fields = ("patient__username", "doctor__username")