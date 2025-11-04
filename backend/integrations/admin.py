from django.contrib import admin
from .models import Integration


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ['domain', 'type', 'provider_id', 'status', 'last_sync_at', 'created_at']
    list_filter = ['type', 'status', 'domain']
    search_fields = ['domain__name', 'provider_id']
    readonly_fields = ['last_sync_at', 'created_at', 'modified_at']
    fieldsets = (
        ('Integration Details', {
            'fields': ('domain', 'type', 'provider_id', 'created_by')
        }),
        ('Credentials', {
            'fields': ('credentials',),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('status', 'last_sync_at', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at')
        }),
    )

