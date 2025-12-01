from django.contrib import admin
from .models import GeneratedContent


@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'domain', 'status', 'article_type', 'source_type', 'created_at']
    list_filter = ['status', 'article_type', 'source_type', 'priority', 'created_at']
    search_fields = ['title', 'keywords', 'domain__name']
    readonly_fields = ['created_at', 'modified_at', 'model_used', 'generation_time_seconds', 
                      'prompt_tokens', 'completion_tokens', 'actual_word_count']
    fieldsets = (
        ('Basic Information', {
            'fields': ('domain', 'title', 'status', 'priority')
        }),
        ('Content', {
            'fields': ('content_html', 'content_json')
        }),
        ('Source Tracking', {
            'fields': ('source_type', 'source_id', 'source_reference')
        }),
        ('Generation Parameters', {
            'fields': ('article_type', 'keywords', 'tone', 'style', 'goal', 'audience', 'depth', 'word_count')
        }),
        ('Metadata', {
            'fields': ('scheduled_date', 'published_date', 'actual_word_count', 'model_used', 
                      'generation_time_seconds', 'prompt_tokens', 'completion_tokens')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at')
        }),
    )


