#!/usr/bin/env python
"""
Seed script to populate report templates for each category.
This creates pre-built templates that match the frontend widget categories.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from reports.models import ReportTemplate
from authentication.models import Organisation


def seed_category_templates():
    """Create report templates for each widget category"""
    
    # Get first organisation as default (or None for global templates)
    org = Organisation.objects.first()
    
    templates = [
        {
            'name': 'Information Metrics Report',
            'description': 'Comprehensive overview of key performance metrics including mentions, citations, sentiment, visibility, and growth indicators.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'total-mentions-metric', 'type': 'metric'},
                        {'id': 'total-citations-metric', 'type': 'metric'},
                        {'id': 'positive-sentiment-metric', 'type': 'metric'},
                        {'id': 'visibility-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'mention-rate-metric', 'type': 'metric'},
                        {'id': 'citation-rate-metric', 'type': 'metric'},
                        {'id': 'avg-sentiment-metric', 'type': 'metric'},
                        {'id': 'engagement-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'mention-growth-metric', 'type': 'metric'},
                        {'id': 'citation-growth-metric', 'type': 'metric'},
                        {'id': 'sentiment-trend-metric', 'type': 'metric'},
                        {'id': 'visibility-trend-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-4',
                    'type': 'double',
                    'widgets': [
                        {'id': 'mentions-chart', 'type': 'chart'},
                        {'id': 'sentiment-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
        {
            'name': 'Mention Report',
            'description': 'Detailed analysis of brand mentions across AI platforms, including trends, distribution, and performance metrics.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'triple',
                    'widgets': [
                        {'id': 'total-mentions-metric', 'type': 'metric'},
                        {'id': 'mention-rate-metric', 'type': 'metric'},
                        {'id': 'mention-growth-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'double',
                    'widgets': [
                        {'id': 'mentions-chart', 'type': 'chart'},
                        {'id': 'platform-chart', 'type': 'chart'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'triple',
                    'widgets': [
                        {'id': 'platform-coverage-metric', 'type': 'metric'},
                        {'id': 'avg-position-metric', 'type': 'metric'},
                        {'id': 'visibility-metric', 'type': 'metric'},
                    ]
                },
            ]
        },
        {
            'name': 'Competitors Report',
            'description': 'Competitive intelligence report showing your position versus competitors, share of voice analysis, and market trends.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'share-metric', 'type': 'metric'},
                        {'id': 'market-position-metric', 'type': 'metric'},
                        {'id': 'competitor-gap-metric', 'type': 'metric'},
                        {'id': 'competitors-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'single',
                    'widgets': [
                        {'id': 'competitors-table', 'type': 'table'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'double',
                    'widgets': [
                        {'id': 'share-of-voice-chart', 'type': 'chart'},
                        {'id': 'competitor-comparison-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
        {
            'name': 'Citations Report',
            'description': 'In-depth analysis of citation performance, source quality, link health, and citation trends over time.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'total-citations-metric', 'type': 'metric'},
                        {'id': 'citation-rate-metric', 'type': 'metric'},
                        {'id': 'unique-sources-metric', 'type': 'metric'},
                        {'id': 'domain-citations-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'citation-density-metric', 'type': 'metric'},
                        {'id': 'valid-links-metric', 'type': 'metric'},
                        {'id': 'broken-links-metric', 'type': 'metric'},
                        {'id': 'pending-citations-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'double',
                    'widgets': [
                        {'id': 'citation-trend-chart', 'type': 'chart'},
                        {'id': 'citations-by-platform-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
        {
            'name': 'Sentiment Analysis Report',
            'description': 'Comprehensive sentiment analysis showing positive, neutral, and negative sentiment trends across platforms and over time.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'avg-sentiment-metric', 'type': 'metric'},
                        {'id': 'positive-sentiment-metric', 'type': 'metric'},
                        {'id': 'negative-sentiment-metric', 'type': 'metric'},
                        {'id': 'sentiment-trend-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'double',
                    'widgets': [
                        {'id': 'sentiment-chart', 'type': 'chart'},
                        {'id': 'sentiment-trend-chart', 'type': 'chart'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'double',
                    'widgets': [
                        {'id': 'platform-sentiment-breakdown-chart', 'type': 'chart'},
                        {'id': 'competitor-comparison-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
        {
            'name': 'Platform Performance Report',
            'description': 'Platform-specific performance analysis showing mentions, citations, and sentiment across different AI platforms.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'platform-coverage-metric', 'type': 'metric'},
                        {'id': 'total-mentions-metric', 'type': 'metric'},
                        {'id': 'total-citations-metric', 'type': 'metric'},
                        {'id': 'avg-sentiment-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'double',
                    'widgets': [
                        {'id': 'platform-chart', 'type': 'chart'},
                        {'id': 'citations-by-platform-chart', 'type': 'chart'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'single',
                    'widgets': [
                        {'id': 'platform-sentiment-breakdown-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
        {
            'name': 'Content Topics Report',
            'description': 'Analysis of topics and content themes, showing which topics drive mentions and engagement.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'triple',
                    'widgets': [
                        {'id': 'topics-covered-metric', 'type': 'metric'},
                        {'id': 'total-mentions-metric', 'type': 'metric'},
                        {'id': 'content-quality-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'single',
                    'widgets': [
                        {'id': 'topics-table', 'type': 'table'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'double',
                    'widgets': [
                        {'id': 'topic-trends-chart', 'type': 'chart'},
                        {'id': 'sentiment-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
        {
            'name': 'Quality & Health Report',
            'description': 'Domain health assessment including content quality, answer coverage, alert status, and overall AI-friendliness.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'health-score-metric', 'type': 'metric'},
                        {'id': 'content-quality-metric', 'type': 'metric'},
                        {'id': 'answer-coverage-metric', 'type': 'metric'},
                        {'id': 'active-alerts-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'valid-links-metric', 'type': 'metric'},
                        {'id': 'broken-links-metric', 'type': 'metric'},
                        {'id': 'critical-issues-metric', 'type': 'metric'},
                        {'id': 'misinformation-cases-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'double',
                    'widgets': [
                        {'id': 'sentiment-trend-chart', 'type': 'chart'},
                        {'id': 'visibility-trend-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
        {
            'name': 'Growth Trends Report',
            'description': 'Historical trends and growth metrics showing momentum in mentions, citations, visibility, and engagement.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'mention-growth-percent-metric', 'type': 'metric'},
                        {'id': 'citation-growth-metric', 'type': 'metric'},
                        {'id': 'visibility-trend-metric', 'type': 'metric'},
                        {'id': 'engagement-growth-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'double',
                    'widgets': [
                        {'id': 'mentions-chart', 'type': 'chart'},
                        {'id': 'citation-trend-chart', 'type': 'chart'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'double',
                    'widgets': [
                        {'id': 'visibility-trend-chart', 'type': 'chart'},
                        {'id': 'sentiment-trend-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
        {
            'name': 'Executive Summary Report',
            'description': 'High-level executive dashboard with the most important metrics and trends for quick decision-making.',
            'template_type': 'custom',
            'organisation': org,
            'grid_rows': [
                {
                    'id': 'row-1',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'total-mentions-metric', 'type': 'metric'},
                        {'id': 'visibility-metric', 'type': 'metric'},
                        {'id': 'share-metric', 'type': 'metric'},
                        {'id': 'avg-sentiment-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-2',
                    'type': 'quad',
                    'widgets': [
                        {'id': 'mention-growth-metric', 'type': 'metric'},
                        {'id': 'market-position-metric', 'type': 'metric'},
                        {'id': 'total-citations-metric', 'type': 'metric'},
                        {'id': 'health-score-metric', 'type': 'metric'},
                    ]
                },
                {
                    'id': 'row-3',
                    'type': 'triple',
                    'widgets': [
                        {'id': 'mentions-chart', 'type': 'chart'},
                        {'id': 'share-of-voice-chart', 'type': 'chart'},
                        {'id': 'sentiment-chart', 'type': 'chart'},
                    ]
                },
            ]
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for template_data in templates:
        name = template_data['name']
        
        # Check if template already exists
        existing = ReportTemplate.objects.filter(name=name).first()
        
        if existing:
            # Update existing template
            for key, value in template_data.items():
                setattr(existing, key, value)
            existing.save()
            updated_count += 1
            print(f'✅ Updated: {name}')
        else:
            # Create new template
            ReportTemplate.objects.create(**template_data)
            created_count += 1
            print(f'✅ Created: {name}')
    
    print()
    print('=' * 80)
    print('SEEDING COMPLETE')
    print('=' * 80)
    print(f'Created: {created_count} templates')
    print(f'Updated: {updated_count} templates')
    print(f'Total: {created_count + updated_count} templates')
    print()
    print('Available Report Templates:')
    for i, template_data in enumerate(templates, 1):
        print(f'{i:2d}. {template_data["name"]}')
    print()


if __name__ == '__main__':
    print('=' * 80)
    print('SEEDING REPORT TEMPLATES FOR EACH CATEGORY')
    print('=' * 80)
    print()
    seed_category_templates()

