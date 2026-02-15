from django.contrib import admin
from django.utils.html import format_html
from .models import HealthQuestionnaire


@admin.register(HealthQuestionnaire)
class HealthQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("user_display", "sugar_level_display", "pressure_display", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__first_name", "user__last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "sugar_status_display", "pressure_status_display")
    autocomplete_fields = ("user",)

    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Показатели здоровья', {
            'fields': ('sugar_level', 'sugar_status_display', 'systolic_pressure', 'diastolic_pressure', 'pressure_status_display')
        }),
        ('Служебная информация', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" if obj.user.first_name else obj.user.email
    user_display.short_description = "Пользователь"

    def sugar_level_display(self, obj):
        status = obj.sugar_status
        status_colors = {
            'low': '#e74c3c',
            'normal': '#27ae60',
            'elevated': '#f39c12',
            'high': '#e74c3c'
        }
        status_labels = {
            'low': 'Низкий',
            'normal': 'Норма',
            'elevated': 'Повышенный',
            'high': 'Высокий'
        }
        color = status_colors.get(status, '#95a5a6')
        label = status_labels.get(status, 'Неизвестно')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} ммоль/л ({})</span>',
            color,
            obj.sugar_level,
            label
        )
    sugar_level_display.short_description = "Уровень сахара"

    def pressure_display(self, obj):
        status = obj.pressure_status
        status_colors = {
            'low': '#3498db',
            'normal': '#27ae60',
            'elevated': '#f39c12',
            'high': '#e74c3c'
        }
        status_labels = {
            'low': 'Низкое',
            'normal': 'Норма',
            'elevated': 'Повышенное',
            'high': 'Высокое'
        }
        color = status_colors.get(status, '#95a5a6')
        label = status_labels.get(status, 'Неизвестно')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{} мм рт. ст. ({})</span>',
            color,
            obj.systolic_pressure,
            obj.diastolic_pressure,
            label
        )
    pressure_display.short_description = "Давление"

    def sugar_status_display(self, obj):
        status = obj.sugar_status
        status_labels = {
            'low': 'Гипогликемия (низкий)',
            'normal': 'Норма',
            'elevated': 'Преддиабет (повышенный)',
            'high': 'Диабет (высокий)'
        }
        return status_labels.get(status, 'Неизвестно')
    sugar_status_display.short_description = "Статус уровня сахара"

    def pressure_status_display(self, obj):
        status = obj.pressure_status
        status_labels = {
            'low': 'Гипотония (низкое)',
            'normal': 'Норма',
            'elevated': 'Повышенное',
            'high': 'Гипертония (высокое)'
        }
        return status_labels.get(status, 'Неизвестно')
    pressure_status_display.short_description = "Статус давления"
