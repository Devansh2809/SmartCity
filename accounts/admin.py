from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'phone', 'department', 'is_staff']
    list_filter = ['role', 'department', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Smart City Profile', {'fields': ('role', 'phone', 'department')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Smart City Profile', {'fields': ('role', 'phone', 'department')}),
    )
