from django.contrib import admin
from .models import Topic, TopicAnalytics, TopicPrompt


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'total_mentions', 'visibility_score', 'sentiment_score', 'trend_percentage', 'created_at']
    list_filter = ['domain']
    search_fields = ['name', 'domain__name']
    readonly_fields = ['created_at', 'modified_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('domain', 'name', 'keyword_list', 'platform_list', 'created_by')
        }),
        ('Metrics', {
            'fields': ('total_mentions', 'visibility_score', 'sentiment_score', 'trend_percentage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at')
        }),
    )


@admin.register(TopicAnalytics)
class TopicAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['topic', 'total_mentions', 'visibility_score', 'sentiment_score', 'timestamp']
    list_filter = ['timestamp', 'topic']
    search_fields = ['topic__name']
    readonly_fields = ['created_at']


@admin.register(TopicPrompt)
class TopicPromptAdmin(admin.ModelAdmin):
    list_display = ['topic', 'prompt_text_short', 'relevance_score', 'search_volume', 'created_at']
    list_filter = ['search_volume', 'topic']
    search_fields = ['prompt_text', 'topic__name']
    readonly_fields = ['created_at']
    
    def prompt_text_short(self, obj):
        return obj.prompt_text[:50] + '...' if len(obj.prompt_text) > 50 else obj.prompt_text
    prompt_text_short.short_description = 'Prompt'

