from django.contrib import admin
from .models import Keyword


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'domain', 'organisation', 'created_at']
    list_filter = ['organisation', 'created_at']
    search_fields = ['keyword', 'domain__name', 'organisation__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['keyword']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('keyword', 'domain', 'organisation')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )