from django.contrib import admin
from .models import Keyword


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'domain', 'created_at']
    list_filter = ['created_at']
    search_fields = ['keyword', 'domain__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['keyword']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('keyword', 'domain')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )