from django.contrib import admin
from .models import PromptGroup, Prompt, PromptAnalytics


@admin.register(PromptGroup)
class PromptGroupAdmin(admin.ModelAdmin):
    list_display = [
        'group_id', 'domain', 'total_mentions', 
        'total_citations', 'average_position', 'track_status', 'is_published', 'created_at'
    ]
    list_filter = ['domain', 'track_status', 'is_published', 'created_at']
    search_fields = ['group_id', 'domain__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['group_id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('group_id', 'domain')
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
        'prompt_short', 'group', 'domain_name', 'track_status', 'type', 
        'tracked_at', 'created_at'
    ]
    list_filter = ['track_status', 'type', 'created_at', 'group__domain']
    search_fields = ['prompt', 'group__group_id', 'group__domain__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['prompt']
    
    def domain_name(self, obj):
        return obj.group.domain.name if obj.group and obj.group.domain else ''
    domain_name.short_description = 'Domain'

    def prompt_short(self, obj):
        return obj.prompt[:50] + '...' if len(obj.prompt) > 50 else obj.prompt
    prompt_short.short_description = 'Prompt'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('prompt', 'group')
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
        'prompt_short', 'platform', 'domain_name', 'is_mention', 'total_mentions', 
        'sentiment_category', 'sentiment_score', 'position', 'track_status', 'is_published', 'views', 'shares', 'created_at'
    ]
    list_filter = ['sentiment_category', 'platform', 'is_mention', 'track_status', 'is_published', 'created_at', 'prompt__group__domain']
    search_fields = ['prompt__prompt', 'platform', 'prompt__group__domain__name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['-created_at']
    
    def domain_name(self, obj):
        try:
            return obj.prompt.group.domain.name
        except Exception:
            return ''
    domain_name.short_description = 'Domain'

    def prompt_short(self, obj):
        return obj.prompt.prompt[:30] + '...' if len(obj.prompt.prompt) > 30 else obj.prompt.prompt
    prompt_short.short_description = 'Prompt'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('prompt', 'platform', 'is_mention')
        }),
        ('Metrics', {
            'fields': ('total_mentions', 'total_citations', 'position')
        }),
        ('Engagement', {
            'fields': ('views', 'shares', 'engagement_score')
        }),
        ('Sentiment Analysis', {
            'fields': ('sentiment_category', 'sentiment_score', 'context_summary', 'citation_list')
        }),
        ('Status & Publishing', {
            'fields': ('track_status', 'track_message', 'tracked_at', 'is_published')
        }),
        ('Advanced Analytics', {
            'fields': ('competitor_mention_list', 'topic_list', 'position_history_list'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )