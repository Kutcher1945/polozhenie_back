from django.contrib import admin
from rest_framework.authtoken.models import Token
from .models import User, DoctorSpecialization, DoctorProfile, NurseSpecialization, NurseProfile, Clinic

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "first_name", "last_name", "is_active", "created_at", "role")
    search_fields = ("email", "phone", "first_name", "last_name")
    list_filter = ("is_active", "created_at", "role")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

# Standard DRF Token is already registered by rest_framework.authtoken
# No need to register it again

@admin.register(DoctorSpecialization)
class DoctorSpecializationAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_kz", "name_en", "created_at")
    search_fields = ("name_ru", "name_kz", "name_en")
    ordering = ("name_ru",)
    readonly_fields = ("created_at", "updated_at")

@admin.register(NurseSpecialization)
class NurseSpecializationAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_kz", "name_en", "created_at")
    search_fields = ("name_ru", "name_kz", "name_en")
    ordering = ("name_ru",)
    readonly_fields = ("created_at", "updated_at")

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "address", "created_at")
    search_fields = ("name", "phone", "address")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "years_of_experience", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ("specialization", "years_of_experience")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("clinics",)

@admin.register(NurseProfile)
class NurseProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "years_of_experience", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ("specialization", "years_of_experience")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("clinics",)


