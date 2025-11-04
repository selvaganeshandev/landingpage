from django.contrib import admin
from .models import Competitor, CompetitorAnalytics, CompetitorPrompt


@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'total_mentions', 'visibility_score', 'sentiment_score', 'share_of_voice_percentage', 'created_at']
    list_filter = ['domain']
    search_fields = ['name', 'url', 'domain__name']
    readonly_fields = ['created_at', 'modified_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('domain', 'name', 'url', 'created_by')
        }),
        ('Metrics', {
            'fields': ('total_mentions', 'visibility_score', 'sentiment_score', 'average_position', 'share_of_voice_percentage', 'trend_percentage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at')
        }),
    )


@admin.register(CompetitorAnalytics)
class CompetitorAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'platform', 'total_mentions', 'position', 'sentiment_score', 'timestamp']
    list_filter = ['platform', 'timestamp', 'competitor']
    search_fields = ['competitor__name']
    readonly_fields = ['created_at']


@admin.register(CompetitorPrompt)
class CompetitorPromptAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'prompt_text_short', 'total_mentions', 'position', 'your_mentions', 'created_at']
    list_filter = ['competitor']
    search_fields = ['prompt_text', 'competitor__name']
    readonly_fields = ['created_at', 'modified_at']
    
    def prompt_text_short(self, obj):
        return obj.prompt_text[:50] + '...' if len(obj.prompt_text) > 50 else obj.prompt_text
    prompt_text_short.short_description = 'Prompt'

