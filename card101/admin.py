from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin
from .models.fire_rank import FireRank
from .models.card101 import Card101
from .models.operation_card import OperationCard
from .models.fire_stations import FireStations

@admin.register(Card101)
class Card101Admin(admin.ModelAdmin):
    list_display = ('object_name', 'address', 'district', 'fire_rank', 'created_at', 'updated_at')
    search_fields = ('object_name', 'address')


@admin.register(OperationCard)
class CardOperationCardAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_kz')
    search_fields = ('name_ru', 'name_kz')


@admin.register(FireRank)
class FireRankAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_kz')
    search_fields = ('name_ru', 'name_kz')



@admin.register(FireStations)
class FireStationsAdmin(LeafletGeoAdmin):
    list_display = ('name_ru', 'address', 'district', 'use_in_recommendations', 'use_in_records')
    search_fields = ('name_ru', 'address')
    list_filter = ('district', 'use_in_recommendations', 'use_in_records')
    ordering = ('sort_order',)