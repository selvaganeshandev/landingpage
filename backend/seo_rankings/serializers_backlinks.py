"""Serializers for the backlink profile page."""
from rest_framework import serializers

from .models import (
    SeoBacklinkSnapshot,
    SeoBacklinkItem,
    SeoBacklinkReferringDomain,
    SeoBacklinkAnchor,
    SeoBacklinkPage,
    SeoBacklinkHistoryPoint,
)


class SeoBacklinkSnapshotSerializer(serializers.ModelSerializer):
    """The profile header: totals, breakdowns, and refresh state.

    `stored_backlinks` is deliberately separate from `backlinks`: the latter is
    the true total from DataForSEO, the former is how many detail rows we
    actually kept. The page must not present 1,000 as the whole profile.
    """
    stored_backlinks = serializers.SerializerMethodField()
    dofollow_backlinks = serializers.SerializerMethodField()

    class Meta:
        model = SeoBacklinkSnapshot
        fields = [
            'id', 'status', 'is_truncated', 'error_message',
            'rank', 'backlinks', 'backlinks_spam_score',
            'broken_backlinks', 'broken_pages', 'crawled_pages',
            'internal_links_count', 'external_links_count',
            'referring_domains', 'referring_domains_nofollow',
            'referring_main_domains', 'referring_main_domains_nofollow',
            'referring_ips', 'referring_subnets',
            'referring_pages', 'referring_pages_nofollow',
            'first_seen', 'lost_date',
            'referring_links_tld', 'referring_links_types',
            'referring_links_attributes', 'referring_links_platform_types',
            'referring_links_semantic_locations', 'referring_links_countries',
            'target_info',
            'stored_backlinks', 'dofollow_backlinks',
            'started_at', 'completed_at', 'next_refresh_allowed_at',
        ]

    def get_stored_backlinks(self, obj):
        return obj.items.count()

    def get_dofollow_backlinks(self, obj):
        return obj.items.filter(dofollow=True).count()


class SeoBacklinkItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoBacklinkItem
        fields = [
            'id', 'domain_from', 'url_from', 'url_to', 'tld_from',
            'anchor', 'item_type', 'dofollow', 'is_new', 'is_lost',
            'is_broken', 'is_indirect_link',
            'rank', 'page_from_rank', 'domain_from_rank', 'backlink_spam_score',
            'page_from_title', 'page_from_language',
            'page_from_external_links', 'page_from_internal_links',
            'domain_from_country', 'semantic_location', 'attributes',
            'url_to_status_code', 'url_to_spam_score',
            'first_seen', 'last_seen',
        ]


class SeoBacklinkReferringDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoBacklinkReferringDomain
        fields = [
            'id', 'domain_name', 'rank', 'backlinks', 'backlinks_spam_score',
            'broken_backlinks', 'referring_pages', 'referring_domains',
            'country', 'is_new', 'is_lost', 'first_seen', 'lost_date',
        ]


class SeoBacklinkAnchorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoBacklinkAnchor
        fields = [
            'id', 'anchor', 'rank', 'backlinks', 'backlinks_spam_score',
            'referring_domains', 'referring_main_domains', 'referring_pages',
            'first_seen', 'lost_date',
        ]


class SeoBacklinkPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoBacklinkPage
        fields = [
            'id', 'page_url', 'rank', 'backlinks', 'referring_domains',
            'referring_main_domains', 'referring_pages', 'status_code',
            'first_seen',
        ]


class SeoBacklinkHistoryPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoBacklinkHistoryPoint
        fields = [
            'point_date', 'rank', 'backlinks',
            'new_backlinks', 'lost_backlinks',
            'new_referring_domains', 'lost_referring_domains',
            'referring_domains', 'referring_main_domains',
            'referring_pages', 'referring_ips',
            'broken_backlinks', 'broken_pages',
        ]
