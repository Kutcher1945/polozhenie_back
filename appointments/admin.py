from django.contrib import admin
from django.utils.html import format_html
from .models import HomeAppointment


@admin.register(HomeAppointment)
class HomeAppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient_display", "doctor_display", "nurse_display", "appointment_time", "status_display", "address", "created_at")
    list_filter = ("status", "appointment_time", "created_at")
    search_fields = ("patient__first_name", "patient__last_name", "patient__email",
                     "doctor__first_name", "doctor__last_name",
                     "nurse__first_name", "nurse__last_name",
                     "address", "symptoms")
    ordering = ("-appointment_time",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("patient", "doctor", "nurse")

    fieldsets = (
        ('Основная информация', {
            'fields': ('patient', 'doctor', 'nurse', 'appointment_time', 'status')
        }),
        ('Адрес вызова', {
            'fields': ('address', 'latitude', 'longitude')
        }),
        ('Медицинская информация', {
            'fields': ('symptoms', 'notes'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def patient_display(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    patient_display.short_description = "Пациент"

    def doctor_display(self, obj):
        if obj.doctor:
            return f"{obj.doctor.first_name} {obj.doctor.last_name}"
        return "-"
    doctor_display.short_description = "Врач"

    def nurse_display(self, obj):
        if obj.nurse:
            return f"{obj.nurse.first_name} {obj.nurse.last_name}"
        return "-"
    nurse_display.short_description = "Медсестра"

    def status_display(self, obj):
        status_colors = {
            'scheduled': '#f39c12',
            'assigned': '#3498db',
            'in_progress': '#9b59b6',
            'completed': '#27ae60',
            'cancelled': '#95a5a6'
        }
        color = status_colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Статус"

    actions = ['mark_as_completed', 'mark_as_cancelled']

    def mark_as_completed(self, request, queryset):
        count = queryset.update(status='completed')
        self.message_user(request, f"{count} вызовов отмечено как завершённые.")
    mark_as_completed.short_description = "Отметить как завершённые"

    def mark_as_cancelled(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f"{count} вызовов отменено.")
    mark_as_cancelled.short_description = "Отметить как отменённые"
