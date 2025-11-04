from django.contrib import admin
from .models import SentimentAnalytics, ShareOfVoiceAnalytics


@admin.register(SentimentAnalytics)
class SentimentAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['domain', 'theme', 'positive_percentage', 'neutral_percentage', 
                    'negative_percentage', 'mention_count', 'platform', 'timestamp']
    list_filter = ['domain', 'theme', 'platform', 'timestamp']
    search_fields = ['domain__name', 'theme']
    readonly_fields = ['created_at']


@admin.register(ShareOfVoiceAnalytics)
class ShareOfVoiceAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['domain', 'brand_display', 'platform', 'share_percentage', 
                    'mention_count', 'market_position', 'timestamp']
    list_filter = ['domain', 'platform', 'timestamp']
    search_fields = ['domain__name', 'competitor__name']
    readonly_fields = ['created_at']
    
    def brand_display(self, obj):
        return obj.competitor.name if obj.competitor else f"{obj.domain.name} (You)"
    brand_display.short_description = 'Brand'

