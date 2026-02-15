from django.contrib import admin
from django.utils.html import format_html
from .models import HomeAppointmentKaspiPayment


@admin.register(HomeAppointmentKaspiPayment)
class HomeAppointmentKaspiPaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "customer_display", "appointment_display", "amount_display", "status_display", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("payment_id", "mpp_payment_id", "customer__email", "customer__first_name", "customer__last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "payment_id")
    autocomplete_fields = ("appointment", "customer")

    fieldsets = (
        ('Основная информация', {
            'fields': ('appointment', 'customer', 'status')
        }),
        ('Платежная информация', {
            'fields': ('payment_id', 'mpp_payment_id', 'amount')
        }),
        ('Чеки', {
            'fields': ('receipt_url', 'receipt_pdf'),
            'classes': ('collapse',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def customer_display(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}" if obj.customer.first_name else obj.customer.email
    customer_display.short_description = "Клиент"

    def appointment_display(self, obj):
        return f"Вызов #{obj.appointment.id} на {obj.appointment.appointment_time.strftime('%d.%m.%Y %H:%M')}"
    appointment_display.short_description = "Вызов"

    def amount_display(self, obj):
        return format_html('<strong>{} ₸</strong>', obj.amount)
    amount_display.short_description = "Сумма"

    def status_display(self, obj):
        status_colors = {
            'pending': '#f39c12',
            'paid': '#27ae60',
            'cancelled': '#95a5a6',
            'failed': '#e74c3c'
        }
        color = status_colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Статус"

    actions = ['mark_as_paid', 'mark_as_cancelled']

    def mark_as_paid(self, request, queryset):
        count = queryset.update(status='paid')
        self.message_user(request, f"{count} платежей отмечено как оплаченные.")
    mark_as_paid.short_description = "Отметить как оплаченные"

    def mark_as_cancelled(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f"{count} платежей отменено.")
    mark_as_cancelled.short_description = "Отметить как отменённые"
