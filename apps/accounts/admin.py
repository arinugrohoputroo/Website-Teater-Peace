from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StaffPermission


class StaffPermissionInline(admin.TabularInline):
    model = StaffPermission
    extra = 1


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'name', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email', 'name']
    ordering = ['username']
    inlines = [StaffPermissionInline]

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Info', {'fields': ('name', 'phone', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'email', 'name', 'role', 'password1', 'password2')}),
    )
