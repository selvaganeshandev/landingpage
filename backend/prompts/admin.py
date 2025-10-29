from django.contrib import admin
from .models import PromptGroup, Prompt, PromptAnalytics


@admin.register(PromptGroup)
class PromptGroupAdmin(admin.ModelAdmin):
    list_display = [
        'group_id', 'domain', 'organisation', 'total_mentions', 
        'total_citations', 'average_position', 'track_status', 'is_published', 'created_at'
    ]
    list_filter = ['organisation', 'track_status', 'is_published', 'created_at']
    search_fields = ['group_id', 'domain__name', 'organisation__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['group_id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('group_id', 'domain', 'organisation')
        }),
        ('Metrics', {
            'fields': ('total_mentions', 'total_citations', 'average_position')
        }),
        ('Status & Publishing', {
            'fields': ('track_status', 'track_message', 'tracked_at', 'is_published')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = [
        'prompt_short', 'group', 'domain', 'track_status', 'type', 
        'tracked_at', 'created_at'
    ]
    list_filter = ['track_status', 'type', 'organisation', 'created_at']
    search_fields = ['prompt', 'group__group_id', 'domain__name', 'organisation__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['prompt']
    
    def prompt_short(self, obj):
        return obj.prompt[:50] + '...' if len(obj.prompt) > 50 else obj.prompt
    prompt_short.short_description = 'Prompt'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('prompt', 'group', 'domain', 'organisation')
        }),
        ('Status & Type', {
            'fields': ('track_status', 'type')
        }),
        ('Tracking', {
            'fields': ('tracked_at', 'track_message')
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
        'sentiment', 'sentiment_score', 'position', 'track_status', 'is_published', 'views', 'shares', 'created_at'
    ]
    list_filter = ['sentiment', 'platform', 'is_mention', 'track_status', 'is_published', 'organisation', 'created_at']
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
        ('Engagement', {
            'fields': ('views', 'shares', 'engagement_score')
        }),
        ('Sentiment Analysis', {
            'fields': ('sentiment', 'sentiment_score', 'context_summary', 'citations')
        }),
        ('Status & Publishing', {
            'fields': ('track_status', 'track_message', 'tracked_at', 'is_published')
        }),
        ('Advanced Analytics', {
            'fields': ('competitor_mentions', 'key_topics', 'position_history'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )