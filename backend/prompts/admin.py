from django.contrib import admin
from .models import PromptCluster, Prompt, PromptAnalytics


@admin.register(PromptCluster)
class PromptClusterAdmin(admin.ModelAdmin):
    list_display = [
        'cluster_id', 'domain', 'organisation', 'total_mentions', 
        'total_citations', 'average_position', 'created_at'
    ]
    list_filter = ['organisation', 'created_at']
    search_fields = ['cluster_id', 'domain__name', 'organisation__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['cluster_id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('cluster_id', 'domain', 'organisation')
        }),
        ('Metrics', {
            'fields': ('total_mentions', 'total_citations', 'average_position')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = [
        'prompt_short', 'cluster', 'domain', 'track_status', 'type', 
        'last_tracked_at', 'created_at'
    ]
    list_filter = ['track_status', 'type', 'organisation', 'created_at']
    search_fields = ['prompt', 'cluster__cluster_id', 'domain__name', 'organisation__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['prompt']
    
    def prompt_short(self, obj):
        return obj.prompt[:50] + '...' if len(obj.prompt) > 50 else obj.prompt
    prompt_short.short_description = 'Prompt'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('prompt', 'cluster', 'domain', 'organisation')
        }),
        ('Status & Type', {
            'fields': ('track_status', 'type')
        }),
        ('Tracking', {
            'fields': ('last_tracked_at', 'track_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PromptAnalytics)
class PromptAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'prompt_short', 'platform', 'domain', 'is_mention', 'total_mentions', 
        'sentiment', 'sentiment_score', 'position', 'created_at'
    ]
    list_filter = ['sentiment', 'platform', 'is_mention', 'organisation', 'created_at']
    search_fields = ['prompt__prompt', 'platform', 'domain__name', 'organisation__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['-created_at']
    
    def prompt_short(self, obj):
        return obj.prompt.prompt[:30] + '...' if len(obj.prompt.prompt) > 30 else obj.prompt.prompt
    prompt_short.short_description = 'Prompt'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('prompt', 'domain', 'organisation', 'platform', 'is_mention')
        }),
        ('Metrics', {
            'fields': ('total_mentions', 'total_citations', 'position')
        }),
        ('Sentiment Analysis', {
            'fields': ('sentiment', 'sentiment_score', 'context_summary', 'citations')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )