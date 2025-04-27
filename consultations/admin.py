from django.contrib import admin
from .models import Consultation

# Register your models here.
@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "status", "created_at", "started_at", "ended_at")
    list_filter = ("status", "created_at")
    search_fields = ("patient__first_name", "doctor__first_name", "meeting_id")