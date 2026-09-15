from django.contrib import admin

from .models import Audit, AuditKeywordResult, AuditPageResult, AuditPromptResult


class AuditPromptResultInline(admin.TabularInline):
    model = AuditPromptResult
    extra = 0
    can_delete = False
    fields = ['prompt_index', 'platform', 'status', 'is_mention', 'is_cited', 'position', 'sentiment']
    readonly_fields = fields
    show_change_link = True


class AuditKeywordResultInline(admin.TabularInline):
    model = AuditKeywordResult
    extra = 0
    can_delete = False
    fields = ['keyword', 'search_volume', 'position', 'ranking_url']
    readonly_fields = fields


class AuditPageResultInline(admin.TabularInline):
    model = AuditPageResult
    extra = 0
    can_delete = False
    fields = ['url', 'fetched', 'word_count', 'schema_types', 'author', 'external_links', 'last_modified']
    readonly_fields = fields


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'host', 'brand_name', 'source', 'status', 'stage', 'progress',
        'geo_score', 'geo_stage', 'opens', 'claimed_domain', 'created_at',
    ]
    list_filter = ['status', 'source', 'geo_stage', 'country', 'created_at']
    search_fields = ['host', 'brand_name', 'requester_email', 'public_token']
    readonly_fields = [
        'public_token', 'opens', 'last_opened_at', 'created_at', 'modified_at', 'completed_at',
    ]
    ordering = ['-created_at']
    inlines = [AuditPromptResultInline, AuditKeywordResultInline, AuditPageResultInline]

    fieldsets = (
        ('Target', {
            'fields': ('host', 'website', 'country', 'source', 'public_token'),
        }),
        ('Requester', {
            'fields': ('requested_by', 'requester_email', 'requester_ip'),
        }),
        ('Pipeline', {
            'fields': ('status', 'stage', 'progress', 'stage_detail', 'config', 'error'),
        }),
        ('Profile', {
            'fields': ('brand_name', 'industry', 'competitors', 'tech_stack'),
        }),
        ('Scores', {
            'fields': (
                'geo_score', 'geo_stage', 'appearances', 'cited_runs', 'total_runs',
                'engines_preferred', 'engines_total', 'share_of_voice',
                'seo_visibility', 'keywords_top10', 'keywords_total',
            ),
        }),
        ('Publication & claim', {
            'fields': ('opens', 'last_opened_at', 'expires_at', 'claimed_at', 'claimed_by', 'claimed_domain'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'modified_at', 'completed_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(AuditPromptResult)
class AuditPromptResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'audit', 'prompt_index', 'platform', 'status', 'is_mention', 'is_cited', 'position']
    list_filter = ['platform', 'status', 'is_mention', 'is_cited']
    search_fields = ['prompt_text', 'audit__host']
    readonly_fields = ['created_at']


@admin.register(AuditKeywordResult)
class AuditKeywordResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'audit', 'keyword', 'search_volume', 'position']
    search_fields = ['keyword', 'audit__host']
    readonly_fields = ['created_at']
