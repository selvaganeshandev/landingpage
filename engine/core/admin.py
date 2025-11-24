from django.contrib import admin
from .models import GeneratedContent


@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'domain', 'article_type', 'status', 'word_count', 'actual_word_count', 'priority', 'created_at']
    list_filter = ['status', 'article_type', 'priority', 'source_type', 'created_at']
    search_fields = ['title', 'keywords', 'source_reference']
    readonly_fields = ['actual_word_count', 'model_used', 'generation_time_seconds', 'prompt_tokens', 'completion_tokens', 'created_at', 'modified_at']

    fieldsets = (
        ('Content', {
            'fields': ('domain', 'title', 'content_html', 'content_json')
        }),
        ('Article Settings', {
            'fields': ('article_type', 'keywords', 'tone', 'style', 'goal', 'audience', 'depth', 'word_count', 'actual_word_count')
        }),
        ('Source Tracking', {
            'fields': ('source_type', 'source_id', 'source_reference')
        }),
        ('Status', {
            'fields': ('status', 'priority', 'scheduled_date', 'published_date')
        }),
        ('AI Metadata', {
            'fields': ('model_used', 'generation_time_seconds', 'prompt_tokens', 'completion_tokens')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at')
        }),
    )
