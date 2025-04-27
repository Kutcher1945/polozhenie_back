from django.contrib import admin
from .models import User, CustomToken

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "first_name", "last_name", "is_active", "created_at", "role")
    search_fields = ("email", "phone", "first_name", "last_name")
    list_filter = ("is_active", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

@admin.register(CustomToken)
class CustomTokenAdmin(admin.ModelAdmin):
    list_display = ("key", "user", "created_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("key", "created_at")


