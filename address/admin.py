from django.contrib import admin
from .models import CityDistrictAkim, CityDistrict, LivingZones, Microsectors
from django.contrib.gis import admin
from leaflet.admin import LeafletGeoAdmin

@admin.register(Microsectors)
class MicrosectorsAdmin(LeafletGeoAdmin):
    list_display = ['name_ru', 'name_kz', 'line_color', 'fill_color', 'opacity', 'is_deleted', 'created_at', 'updated_at']
    search_fields = ['name_ru', 'name_kz']
    list_filter = ['is_deleted', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    # Use fieldsets to organize fields in the admin
    fieldsets = (
        (None, {
            'fields': ('name_ru', 'name_kz', 'line_color', 'fill_color', 'opacity', 'boundary')
        }),
        ('Metadata', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
        }),
    )

    # Override to prevent editing of 'is_deleted'
    def get_readonly_fields(self, request, obj=None):
        if obj:  # If editing an existing object
            return ['is_deleted', 'created_at', 'updated_at']
        else:
            return ['is_deleted', 'created_at', 'updated_at']

    # Customize Leaflet map settings (optional)


# CityDistrictAkim Admin Configuration
@admin.register(CityDistrictAkim)
class CityDistrictAkimAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_kz', 'akim_img', 'date_of_appointment', 'date_of_dismissal', 'created_at', 'updated_at')
    search_fields = ('name_ru', 'name_kz')
    list_filter = ('date_of_appointment', 'date_of_dismissal')
    ordering = ('name_ru',)

# CityDistrict Admin Configuration
@admin.register(CityDistrict)
class CityDistrictAdmin(LeafletGeoAdmin):
    list_display = ('name_ru', 'name_kz', 'response_name_ru', 'response_name_kz', 'gerb_img', 'akim', 'created_at', 'updated_at')
    search_fields = ('name_ru', 'name_kz')
    list_filter = ('created_at', 'updated_at')
    ordering = ('name_ru',)
    list_select_related = ('akim',)  # Prefetch related Akim details for performance optimization


@admin.register(LivingZones)
class LivingZonesAdmin(LeafletGeoAdmin):
    list_display = ('name_ru', 'name_kz', 'line_color', 'fill_color', 'opacity', 'is_deleted', 'created_at', 'updated_at')
    search_fields = ('name_ru', 'name_kz')
    list_filter = ('is_deleted', 'created_at', 'updated_at')