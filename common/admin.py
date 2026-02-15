from django.contrib import admin
from django.utils.html import format_html
from rest_framework.authtoken.models import Token
from .models import (
    User, DoctorSpecialization, DoctorProfile, NurseSpecialization,
    NurseProfile, AdminProfile, UserSession, PatientProfile, PatientMedicalProfile
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "full_name_display", "role_display", "is_active", "created_at")
    search_fields = ("email", "phone", "first_name", "last_name")
    list_filter = ("is_active", "role", "gender", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_seen")

    fieldsets = (
        ('Основная информация', {
            'fields': ('email', 'phone', 'password', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Персональные данные', {
            'fields': ('birth_date', 'gender', 'address', 'city', 'language'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at', 'last_seen', 'reset_code', 'reset_code_created_at'),
            'classes': ('collapse',)
        }),
        ('Права доступа', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
    )

    def full_name_display(self, obj):
        return f"{obj.first_name} {obj.last_name}" if obj.first_name and obj.last_name else "-"
    full_name_display.short_description = "ФИО"

    def role_display(self, obj):
        role_colors = {
            'patient': '#3498db',
            'doctor': '#27ae60',
            'nurse': '#e74c3c',
            'admin': '#9b59b6'
        }
        color = role_colors.get(obj.role, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_display.short_description = "Роль"


@admin.register(DoctorSpecialization)
class DoctorSpecializationAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_kz", "name_en", "created_at")
    search_fields = ("name_ru", "name_kz", "name_en")
    ordering = ("name_ru",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ('Названия специализации', {
            'fields': ('name_ru', 'name_kz', 'name_en')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NurseSpecialization)
class NurseSpecializationAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_kz", "name_en", "created_at")
    search_fields = ("name_ru", "name_kz", "name_en")
    ordering = ("name_ru",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ('Названия специализации', {
            'fields': ('name_ru', 'name_kz', 'name_en')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user_display", "specialization", "experience_display", "clinic", "availability_status_display", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "clinic__name")
    list_filter = ("specialization", "years_of_experience", "clinic", "availability_status")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("additional_clinics", "specializations")
    autocomplete_fields = ("user", "clinic", "specialization")

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'doctor_type', 'specialization', 'specializations', 'years_of_experience')
        }),
        ('Клиники', {
            'fields': ('clinic', 'additional_clinics')
        }),
        ('Доступность', {
            'fields': ('availability_status', 'availability_note')
        }),
        ('Цены и расписание', {
            'fields': ('offline_consultation_price', 'online_consultation_price',
                      'preferred_consultation_duration', 'work_schedule',
                      'online_work_schedule', 'offline_work_schedule'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_display.short_description = "Доктор"

    def experience_display(self, obj):
        return f"{obj.years_of_experience} лет" if obj.years_of_experience else "-"
    experience_display.short_description = "Опыт"

    def availability_status_display(self, obj):
        status_colors = {
            'available': '#27ae60',
            'busy': '#f39c12',
            'offline': '#95a5a6',
            'break': '#3498db'
        }
        color = status_colors.get(obj.availability_status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_availability_status_display() if obj.availability_status else 'Не указано'
        )
    availability_status_display.short_description = "Статус"


@admin.register(NurseProfile)
class NurseProfileAdmin(admin.ModelAdmin):
    list_display = ("user_display", "specialization", "experience_display", "clinic", "availability_status_display", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "clinic__name")
    list_filter = ("specialization", "years_of_experience", "clinic", "availability_status")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("additional_clinics", "specializations")
    autocomplete_fields = ("user", "clinic", "specialization")

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'nurse_type', 'specialization', 'specializations', 'years_of_experience')
        }),
        ('Клиники', {
            'fields': ('clinic', 'additional_clinics')
        }),
        ('Доступность', {
            'fields': ('availability_status', 'availability_note')
        }),
        ('Цены и расписание', {
            'fields': ('offline_consultation_price', 'online_consultation_price',
                      'preferred_consultation_duration', 'work_schedule',
                      'online_work_schedule', 'offline_work_schedule'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_display.short_description = "Медсестра"

    def experience_display(self, obj):
        return f"{obj.years_of_experience} лет" if obj.years_of_experience else "-"
    experience_display.short_description = "Опыт"

    def availability_status_display(self, obj):
        status_colors = {
            'available': '#27ae60',
            'busy': '#f39c12',
            'offline': '#95a5a6',
            'break': '#3498db'
        }
        color = status_colors.get(obj.availability_status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_availability_status_display() if obj.availability_status else 'Не указано'
        )
    availability_status_display.short_description = "Статус"


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user_display", "admin_type_display", "clinic", "can_manage_staff", "can_view_reports", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "clinic__name", "department")
    list_filter = ("admin_type", "can_manage_staff", "can_manage_patients", "can_view_reports", "clinic")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user", "clinic")

    fieldsets = (
        ('Информация о пользователе', {
            'fields': ('user', 'admin_type', 'clinic', 'department')
        }),
        ('Права доступа', {
            'fields': ('can_manage_staff', 'can_manage_patients', 'can_view_reports', 'can_manage_settings')
        }),
        ('Дополнительная информация', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_display.short_description = "Администратор"

    def admin_type_display(self, obj):
        type_colors = {
            'super': '#e74c3c',
            'clinic': '#3498db',
            'manager': '#27ae60'
        }
        color = type_colors.get(obj.admin_type, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_admin_type_display() if obj.admin_type else 'Не указано'
        )
    admin_type_display.short_description = "Тип"


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user_display", "device_name", "device_type", "ip_address", "last_activity", "is_revoked_display")
    search_fields = ("user__email", "user__first_name", "user__last_name", "device_name", "ip_address")
    list_filter = ("device_type", "is_revoked", "created_at", "last_activity")
    ordering = ("-last_activity",)
    readonly_fields = ("created_at", "updated_at", "last_activity", "revoked_at")

    fieldsets = (
        ('Информация о пользователе', {
            'fields': ('user', 'refresh_token_jti')
        }),
        ('Информация об устройстве', {
            'fields': ('device_name', 'device_type', 'user_agent', 'ip_address')
        }),
        ('Состояние сессии', {
            'fields': ('last_activity', 'is_revoked', 'revoked_at')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return obj.user.email
    user_display.short_description = "Пользователь"

    def is_revoked_display(self, obj):
        if obj.is_revoked:
            return format_html('<span style="color: red;">✗ Отозвана</span>')
        return format_html('<span style="color: green;">✓ Активна</span>')
    is_revoked_display.short_description = "Статус"

    actions = ['revoke_sessions']

    def revoke_sessions(self, request, queryset):
        for session in queryset:
            session.revoke()
        self.message_user(request, f"{queryset.count()} сессий было отозвано.")
    revoke_sessions.short_description = "Отозвать выбранные сессии"


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user_display", "clinic", "citizenship", "marital_status_display", "profession", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "profession", "emergency_contact_name")
    list_filter = ("marital_status", "citizenship", "clinic", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user", "clinic")

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'clinic')
        }),
        ('Персональная информация', {
            'fields': ('citizenship', 'marital_status', 'profession')
        }),
        ('Экстренный контакт', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship'),
            'classes': ('collapse',)
        }),
        ('Предпочтения', {
            'fields': ('preferred_language', 'communication_preferences'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_display.short_description = "Пациент"

    def marital_status_display(self, obj):
        return obj.get_marital_status_display() if obj.marital_status else "-"
    marital_status_display.short_description = "Семейное положение"


@admin.register(PatientMedicalProfile)
class PatientMedicalProfileAdmin(admin.ModelAdmin):
    list_display = ("user_display", "blood_type", "rhesus_factor", "fluorography_status_display", "immunization_status_display", "last_modified_by", "updated_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ("blood_type", "rhesus_factor", "fluorography_status", "immunization_status", "updated_at")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user", "last_modified_by")

    fieldsets = (
        ('Основная информация', {
            'fields': ('user',)
        }),
        ('Информация о крови', {
            'fields': ('blood_type', 'rhesus_factor')
        }),
        ('Флюорография', {
            'fields': ('fluorography_status', 'fluorography_date')
        }),
        ('Иммунизация', {
            'fields': ('immunization_status', 'immunization_date')
        }),
        ('Аудит', {
            'fields': ('last_modified_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_display.short_description = "Пациент"

    def fluorography_status_display(self, obj):
        status_colors = {
            'normal': '#27ae60',
            'abnormal': '#e74c3c',
            'pending': '#f39c12',
            'expired': '#95a5a6'
        }
        color = status_colors.get(obj.fluorography_status, '#95a5a6')
        display_text = obj.get_fluorography_status_display() if obj.fluorography_status else 'Не указано'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            display_text
        )
    fluorography_status_display.short_description = "Флюорография"

    def immunization_status_display(self, obj):
        status_colors = {
            'up_to_date': '#27ae60',
            'partial': '#f39c12',
            'expired': '#e74c3c',
            'none': '#95a5a6'
        }
        color = status_colors.get(obj.immunization_status, '#95a5a6')
        display_text = obj.get_immunization_status_display() if obj.immunization_status else 'Не указано'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            display_text
        )
    immunization_status_display.short_description = "Иммунизация"
