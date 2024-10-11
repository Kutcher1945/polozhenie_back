from django.contrib import admin
from .models import CityDistrictAkim, CityDistrict

# CityDistrictAkim Admin Configuration
@admin.register(CityDistrictAkim)
class CityDistrictAkimAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_kz', 'akim_img', 'date_of_appointment', 'date_of_dismissal', 'created_at', 'updated_at')
    search_fields = ('name_ru', 'name_kz')
    list_filter = ('date_of_appointment', 'date_of_dismissal')
    ordering = ('name_ru',)

# CityDistrict Admin Configuration
@admin.register(CityDistrict)
class CityDistrictAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_kz', 'response_name_ru', 'response_name_kz', 'gerb_img', 'akim', 'created_at', 'updated_at')
    search_fields = ('name_ru', 'name_kz')
    list_filter = ('created_at', 'updated_at')
    ordering = ('name_ru',)
    list_select_related = ('akim',)  # Prefetch related Akim details for performance optimization
