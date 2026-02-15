from django.contrib import admin
from django.utils.html import format_html
from .models import TimeSlot, Consultation, AIRecommendationLog


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("doctor_display", "start_time", "end_time", "availability_display", "booking_status", "is_recurring", "created_at")
    search_fields = ("doctor__email", "doctor__first_name", "doctor__last_name")
    list_filter = ("is_available", "is_recurring", "recurrence_type", "created_at")
    ordering = ("-start_time",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("doctor",)

    fieldsets = (
        ('Основная информация', {
            'fields': ('doctor', 'start_time', 'end_time')
        }),
        ('Доступность', {
            'fields': ('is_available', 'max_consultations', 'booked_consultations')
        }),
        ('Настройки повторения', {
            'fields': ('is_recurring', 'recurrence_type', 'recurrence_end_date'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def doctor_display(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}"
    doctor_display.short_description = "Доктор"

    def availability_display(self, obj):
        if obj.is_available:
            return format_html('<span style="color: green;">✓ Доступен</span>')
        return format_html('<span style="color: red;">✗ Недоступен</span>')
    availability_display.short_description = "Доступность"

    def booking_status(self, obj):
        percentage = (obj.booked_consultations / obj.max_consultations * 100) if obj.max_consultations > 0 else 0
        color = '#27ae60' if percentage < 50 else '#f39c12' if percentage < 100 else '#e74c3c'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{} ({}%)</span>',
            color,
            obj.booked_consultations,
            obj.max_consultations,
            int(percentage)
        )
    booking_status.short_description = "Бронирование"


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("id", "patient_display", "doctor_display", "status_display", "urgency_display", "scheduled_at", "access_code", "created_at")
    list_filter = ("status", "is_urgent", "created_at", "scheduled_at")
    search_fields = ("patient__first_name", "patient__last_name", "patient__email",
                     "doctor__first_name", "doctor__last_name", "doctor__email",
                     "meeting_id", "access_code")
    ordering = ("-created_at",)
    readonly_fields = ("meeting_id", "access_code", "created_at", "updated_at", "started_at", "ended_at", "magic_link_used_at")
    autocomplete_fields = ("patient", "doctor", "timeslot", "ai_recommendation")

    fieldsets = (
        ('Основная информация', {
            'fields': ('patient', 'doctor', 'status', 'is_urgent')
        }),
        ('Планирование', {
            'fields': ('timeslot', 'scheduled_at', 'ai_recommendation')
        }),
        ('Доступ', {
            'fields': ('meeting_id', 'access_code', 'magic_link_used_at')
        }),
        ('Временные метки', {
            'fields': ('started_at', 'ended_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Медицинская информация', {
            'fields': ('complaints', 'anamnesis', 'diagnostics', 'diagnosis', 'treatment'),
            'classes': ('collapse',)
        }),
        ('Дополнительная информация', {
            'fields': ('session_notes', 'prescription', 'recommendations', 'transcription'),
            'classes': ('collapse',)
        }),
    )

    def patient_display(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    patient_display.short_description = "Пациент"

    def doctor_display(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}"
    doctor_display.short_description = "Доктор"

    def status_display(self, obj):
        status_colors = {
            'pending': '#f39c12',
            'ongoing': '#3498db',
            'completed': '#27ae60',
            'cancelled': '#95a5a6',
            'missed': '#e74c3c',
            'scheduled': '#9b59b6'
        }
        color = status_colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Статус"

    def urgency_display(self, obj):
        if obj.is_urgent:
            return format_html('<span style="color: #e74c3c; font-weight: bold;">⚠ Экстренная</span>')
        return format_html('<span style="color: #95a5a6;">Обычная</span>')
    urgency_display.short_description = "Экстренность"

    actions = ['mark_as_completed', 'mark_as_cancelled']

    def mark_as_completed(self, request, queryset):
        count = 0
        for consultation in queryset:
            consultation.end()
            count += 1
        self.message_user(request, f"{count} консультаций отмечено как завершённые.")
    mark_as_completed.short_description = "Отметить как завершённые"

    def mark_as_cancelled(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f"{count} консультаций отменено.")
    mark_as_cancelled.short_description = "Отметить как отменённые"


@admin.register(AIRecommendationLog)
class AIRecommendationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "recommended_specialty", "matched_doctor_display", "urgency_display", "fallback_display", "created_at")
    list_filter = ("urgency", "fallback_used", "created_at")
    search_fields = ("symptoms", "recommended_specialty", "specialty_not_found",
                     "matched_doctor__first_name", "matched_doctor__last_name", "matched_doctor__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("matched_doctor",)

    fieldsets = (
        ('Запрос пациента', {
            'fields': ('symptoms',)
        }),
        ('Рекомендации AI', {
            'fields': ('recommended_specialty', 'reason', 'urgency')
        }),
        ('Результат', {
            'fields': ('matched_doctor', 'fallback_used', 'specialty_not_found')
        }),
        ('Технические данные', {
            'fields': ('ai_raw_response', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def matched_doctor_display(self, obj):
        if obj.matched_doctor:
            return f"{obj.matched_doctor.first_name} {obj.matched_doctor.last_name}"
        return "-"
    matched_doctor_display.short_description = "Назначенный врач"

    def urgency_display(self, obj):
        if obj.urgency == 'urgent':
            return format_html('<span style="color: #e74c3c; font-weight: bold;">⚠ Экстренная</span>')
        return format_html('<span style="color: #27ae60;">Обычная</span>')
    urgency_display.short_description = "Экстренность"

    def fallback_display(self, obj):
        if obj.fallback_used:
            return format_html('<span style="color: #f39c12;">✓ Терапевт</span>')
        return format_html('<span style="color: #27ae60;">✓ Точное совпадение</span>')
    fallback_display.short_description = "Тип назначения"
