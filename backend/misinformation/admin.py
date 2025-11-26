from django.contrib import admin
from .models import (
    MisinformationScan,
    CitationURL,
    CitationContent,
    MisinformationAlert,
    MisinformationAnalytics,
)


@admin.register(MisinformationScan)
class MisinformationScanAdmin(admin.ModelAdmin):
    list_display = ['id', 'domain', 'status', 'total_prompts_scanned', 'total_citations_found', 'total_alerts_generated', 'started_at', 'completed_at']
    list_filter = ['status', 'domain']
    search_fields = ['domain__name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(CitationURL)
class CitationURLAdmin(admin.ModelAdmin):
    list_display = ['id', 'url_truncated', 'domain', 'crawl_status', 'http_status_code', 'last_crawled_at']
    list_filter = ['crawl_status', 'is_crawlable', 'domain']
    search_fields = ['url', 'domain__name']
    readonly_fields = ['url_hash', 'created_at', 'modified_at']
    ordering = ['-created_at']

    def url_truncated(self, obj):
        return obj.url[:80] + '...' if len(obj.url) > 80 else obj.url
    url_truncated.short_description = 'URL'


@admin.register(CitationContent)
class CitationContentAdmin(admin.ModelAdmin):
    list_display = ['id', 'citation_url', 'page_title', 'publish_date', 'crawled_at']
    search_fields = ['page_title', 'citation_url__url']
    readonly_fields = ['content_hash', 'crawled_at']


@admin.register(MisinformationAlert)
class MisinformationAlertAdmin(admin.ModelAdmin):
    list_display = ['id', 'domain', 'alert_type', 'severity', 'status', 'created_at']
    list_filter = ['alert_type', 'severity', 'status', 'domain']
    search_fields = ['domain__name', 'llm_claim', 'explanation']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['-created_at']


@admin.register(MisinformationAnalytics)
class MisinformationAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['id', 'domain', 'date', 'total_detected', 'broken_links_count', 'misinformation_count', 'outdated_count']
    list_filter = ['domain', 'date']
    search_fields = ['domain__name']
    readonly_fields = ['created_at']
    ordering = ['-date']
