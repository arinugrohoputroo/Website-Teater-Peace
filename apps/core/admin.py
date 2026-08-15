from django.contrib import admin
from .models import EventConfig, AuditLog


@admin.register(EventConfig)
class EventConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description']
    search_fields = ['key', 'value']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'module', 'object_id']
    list_filter = ['module', 'action']
    search_fields = ['user__name', 'action', 'description']
    readonly_fields = ['user', 'action', 'module', 'object_id', 'description', 'metadata', 'ip_address', 'timestamp']
