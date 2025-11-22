from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin
from .models import Clinics, Country, Region, City, District, Microdistrict


@admin.register(Country)
class CountryAdmin(LeafletGeoAdmin):
    list_display = (
        "name_ru",
        "name_kz",
        "code",
        "is_deleted",
        "created_at",
    )
    list_filter = (
        "is_deleted",
    )
    search_fields = (
        "name_ru",
        "name_kz",
        "code",
    )
    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name_ru",
                "name_kz",
                "code",
                "is_deleted",
            ),
        }),
        ("Геолокация", {
            "fields": (
                "point",
                "geometry",
            ),
        }),
    )


@admin.register(Region)
class RegionAdmin(LeafletGeoAdmin):
    list_display = (
        "name_ru",
        "name_kz",
        "country",
        "is_deleted",
        "created_at",
    )
    list_filter = (
        "country",
        "is_deleted",
    )
    search_fields = (
        "name_ru",
        "name_kz",
    )
    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name_ru",
                "name_kz",
                "country",
                "is_deleted",
            ),
        }),
        ("Геолокация", {
            "fields": (
                "point",
                "geometry",
            ),
        }),
    )


@admin.register(City)
class CityAdmin(LeafletGeoAdmin):
    list_display = (
        "name_ru",
        "name_kz",
        "region",
        "is_deleted",
        "created_at",
    )
    list_filter = (
        "region",
        "region__country",
        "is_deleted",
    )
    search_fields = (
        "name_ru",
        "name_kz",
    )
    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name_ru",
                "name_kz",
                "region",
                "is_deleted",
            ),
        }),
        ("Геолокация", {
            "fields": (
                "point",
                "geometry",
            ),
        }),
    )


@admin.register(District)
class DistrictAdmin(LeafletGeoAdmin):
    list_display = (
        "name_ru",
        "name_kz",
        "city",
        "is_deleted",
        "created_at",
    )
    list_filter = (
        "city",
        "is_deleted",
    )
    search_fields = (
        "name_ru",
        "name_kz",
    )
    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name_ru",
                "name_kz",
                "city",
                "is_deleted",
            ),
        }),
        ("Геолокация", {
            "fields": (
                "point",
                "geometry",
            ),
        }),
    )


@admin.register(Microdistrict)
class MicrodistrictAdmin(LeafletGeoAdmin):
    list_display = (
        "name_ru",
        "name_kz",
        "district",
        "is_deleted",
        "created_at",
    )
    list_filter = (
        "district",
        "district__city",
        "is_deleted",
    )
    search_fields = (
        "name_ru",
        "name_kz",
    )
    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name_ru",
                "name_kz",
                "district",
                "is_deleted",
            ),
        }),
        ("Геолокация", {
            "fields": (
                "point",
                "geometry",
            ),
        }),
    )


@admin.register(Clinics)
class ClinicsAdmin(LeafletGeoAdmin):
    list_display = (
        "name",
        "city",
        "district",
        "rating",
        "review_count",
    )
    list_filter = (
        "city",
        "district",
        "country",
        "region",
    )
    search_fields = (
        "name",
        "address",
        "city",
        "district",
        "microdistrict",
        "categories",
    )

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name",
                "description",
            ),
        }),
        ("Адрес", {
            "fields": (
                "address",
                "address_comment",
                "postal_code",
                "microdistrict",
                "district",
                "city",
                "administrative_area",
                "region",
                "country",
            )
        }),
        ("Геолокация", {
            "fields": ("location",),
        }),
        ("Метаданные", {
            "fields": (
                "working_hours",
                "time_zone",
                "rating",
                "review_count",
            )
        }),
        ("Контакты", {
            "classes": ("collapse",),
            "fields": (
                "phones",
                "emails",
                "websites",
                "whatsapp",
            )
        }),
        ("Социальные сети", {
            "classes": ("collapse",),
            "fields": (
                "instagram",
                "twitter",
                "facebook",
                "vkontakte",
                "viber",
                "youtube",
                "skype",
            )
        }),
        ("Прочее", {
            "classes": ("collapse",),
            "fields": (
                "categories",
                "gis2_url",
            )
        }),
    )
