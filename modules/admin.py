from django.contrib import admin
from .models import ModulesCategory, ModulesSubCategory

@admin.register(ModulesCategory)
class ModulesCategoryAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_kz', 'is_deleted', 'created_at', 'updated_at')
    search_fields = ('name_ru', 'name_kz')
    list_filter = ('is_deleted',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ModulesSubCategory)
class ModulesSubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_kz', 'module_category', 'is_deleted', 'created_at', 'updated_at')
    search_fields = ('name_ru', 'name_kz')
    list_filter = ('is_deleted', 'module_category')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['module_category']
