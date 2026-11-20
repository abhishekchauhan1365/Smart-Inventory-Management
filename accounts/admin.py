from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'is_active_staff', 'is_staff')
    list_filter = ('role', 'is_active_staff', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    fieldsets = UserAdmin.fieldsets + (
        ('Pharmacy System Details', {
            'fields': ('role', 'phone_number', 'qualification', 'is_active_staff')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Pharmacy System Details', {
            'fields': ('role', 'phone_number', 'qualification', 'is_active_staff')
        }),
    )
