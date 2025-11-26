# Generated manually to add default report templates

from django.db import migrations


def create_default_templates(apps, schema_editor):
    """Create the 4 default report templates"""
    ReportTemplate = apps.get_model('reports', 'ReportTemplate')

    templates = [
        {
            'name': 'Executive Dashboard',
            'description': 'High-level summary of AI visibility metrics, brand mentions, and sentiment analysis for executive stakeholders.',
            'sections': [
                'Executive Summary',
                'AI Visibility Score',
                'Brand Mentions Overview',
                'Sentiment Analysis',
                'Platform Distribution',
                'Key Insights',
                'Recommendations'
            ],
            'is_active': True
        },
        {
            'name': 'Detailed Analytics',
            'description': 'Comprehensive analytics report with detailed breakdowns of mentions, sentiment trends, competitor analysis, and topic performance.',
            'sections': [
                'Overview',
                'Mention Analysis',
                'Sentiment Trends',
                'Topic Performance',
                'Keyword Rankings',
                'Competitor Comparison',
                'Platform Breakdown',
                'Citation Analysis',
                'Historical Trends',
                'Actionable Insights'
            ],
            'is_active': True
        },
        {
            'name': 'Competitor Focus',
            'description': 'In-depth comparison of your brand against competitors across AI platforms, including share of voice and visibility gaps.',
            'sections': [
                'Competitive Overview',
                'Share of Voice',
                'Visibility Comparison',
                'Mention Frequency',
                'Sentiment Comparison',
                'Platform Performance',
                'Content Gap Analysis',
                'Competitive Positioning',
                'Strategic Recommendations'
            ],
            'is_active': True
        },
        {
            'name': 'Content Strategy',
            'description': 'Analysis of how your content is being referenced and cited by AI platforms, with optimization recommendations.',
            'sections': [
                'Content Overview',
                'Citation Analysis',
                'Top Performing Content',
                'Topic Coverage',
                'Keyword Performance',
                'Content Gaps',
                'AI Platform Citations',
                'Optimization Opportunities',
                'Content Recommendations'
            ],
            'is_active': True
        }
    ]

    for template_data in templates:
        ReportTemplate.objects.create(**template_data)


def remove_default_templates(apps, schema_editor):
    """Remove the default templates (for rollback)"""
    ReportTemplate = apps.get_model('reports', 'ReportTemplate')
    ReportTemplate.objects.filter(name__in=[
        'Executive Dashboard',
        'Detailed Analytics',
        'Competitor Focus',
        'Content Strategy'
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_templates, remove_default_templates),
    ]
