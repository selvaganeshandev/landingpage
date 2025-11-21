#!/usr/bin/env python
"""
Seed script to populate initial report templates.
Run this script to add the 4 predefined report templates to the database.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from reports.models import ReportTemplate


def seed_templates():
    """Create the 4 initial report templates"""

    templates = [
        {
            'name': 'Executive Dashboard',
            'description': 'High-level overview report designed for executives and stakeholders. Includes key metrics, trends, and strategic insights.',
            'sections': [
                'executive_summary',
                'key_metrics',
                'visibility_trends',
                'competitive_landscape',
                'strategic_recommendations'
            ]
        },
        {
            'name': 'Detailed Analytics',
            'description': 'Comprehensive analytics report with deep-dive into all metrics, prompt performance, and LLM response patterns.',
            'sections': [
                'overview',
                'prompt_performance',
                'llm_comparison',
                'sentiment_analysis',
                'content_themes',
                'temporal_trends',
                'recommendations'
            ]
        },
        {
            'name': 'Competitor Focus',
            'description': 'Competitor-centric report analyzing your position relative to competitors across different LLMs and prompts.',
            'sections': [
                'competitive_overview',
                'share_of_voice',
                'competitor_mentions',
                'sentiment_comparison',
                'gap_analysis',
                'opportunities'
            ]
        },
        {
            'name': 'Content Strategy',
            'description': 'Content optimization report identifying gaps, opportunities, and recommendations for improving LLM visibility.',
            'sections': [
                'content_gaps',
                'topic_coverage',
                'optimization_opportunities',
                'prompt_suggestions',
                'content_calendar',
                'action_items'
            ]
        }
    ]

    created_count = 0
    updated_count = 0

    for template_data in templates:
        template, created = ReportTemplate.objects.update_or_create(
            name=template_data['name'],
            defaults={
                'description': template_data['description'],
                'sections': template_data['sections'],
                'is_active': True
            }
        )

        if created:
            created_count += 1
            print(f"✓ Created template: {template.name}")
        else:
            updated_count += 1
            print(f"↻ Updated template: {template.name}")

    print(f"\nSeeding complete!")
    print(f"Created: {created_count} templates")
    print(f"Updated: {updated_count} templates")
    print(f"Total templates in database: {ReportTemplate.objects.filter(is_active=True).count()}")


if __name__ == '__main__':
    print("Seeding report templates...")
    print("-" * 50)
    seed_templates()
