from django.contrib import admin
from .models import Alert, AlertRule, AlertNotification


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'domain', 'type', 'severity', 'status', 'created_at']
    list_filter = ['type', 'severity', 'status', 'domain']
    search_fields = ['title', 'message', 'domain__name']
    readonly_fields = ['created_at', 'modified_at']
    fieldsets = (
        ('Alert Information', {
            'fields': ('domain', 'type', 'severity', 'title', 'message', 'platform', 'metric')
        }),
        ('Status', {
            'fields': ('status', 'resolved_at', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at')
        }),
    )


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'enabled', 'detection_count', 'last_triggered_at']
    list_filter = ['enabled', 'domain']
    search_fields = ['name', 'description']
    readonly_fields = ['detection_count', 'last_triggered_at', 'created_at', 'modified_at']


@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = ['alert', 'channel', 'recipient', 'status', 'sent_at']
    list_filter = ['channel', 'status']
    search_fields = ['recipient', 'alert__title']
    readonly_fields = ['sent_at']

