from django.contrib import admin
from .models import Domain


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'url', 'organisation', 'total_mentions', 'total_citations', 
        'visibility_score', 'sentiment_category', 'sentiment_score', 'created_at'
    ]
    list_filter = ['sentiment_category', 'organisation', 'created_at']
    search_fields = ['name', 'url', 'organisation__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'url', 'organisation')
        }),
        ('Metrics', {
            'fields': ('total_mentions', 'total_citations', 'visibility_score', 'average_position')
        }),
        ('Alerts & Sentiment', {
            'fields': ('active_alerts', 'sentiment_category', 'sentiment_score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )