#!/usr/bin/env python
"""
Comprehensive Widget Audit Script
Tests all widgets, documents their purpose, and identifies issues
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from reports.services.widget_data_fetcher import WidgetDataFetcher
from reports.models import ReportTemplate
from domains.models import Domain
from authentication.models import Organisation
from datetime import timedelta
from django.utils import timezone
import json


def get_widget_description(widget_id):
    """Map widget IDs to human-readable descriptions"""
    descriptions = {
        # Mention Metrics
        'total-mentions-metric': 'Total count of brand mentions across all platforms',
        'mention-rate-metric': 'Percentage of prompts that resulted in mentions',
        'mention-growth-metric': 'Growth in mentions compared to previous period',
        'mention-growth-percent-metric': 'Percentage growth in mentions',
        'platform-coverage-metric': 'Number of platforms where brand is mentioned',
        
        # Citation Metrics
        'total-citations-metric': 'Total citations across all responses',
        'citation-rate-metric': 'Average citations per mention',
        'citation-density-metric': 'Average citations per response',
        'citation-growth-metric': 'Growth in citations vs previous period',
        'unique-sources-metric': 'Number of unique citation sources',
        'domain-citations-metric': 'Citations from your own domain',
        'valid-links-metric': 'Number of working citation URLs',
        'broken-links-metric': 'Number of broken citation links',
        'pending-citations-metric': 'Citations awaiting verification',
        'primary-sources-metric': 'Count of primary source citations',
        
        # Sentiment Metrics
        'avg-sentiment-metric': 'Average sentiment score across mentions',
        'positive-sentiment-metric': 'Percentage of positive sentiment mentions',
        'negative-sentiment-metric': 'Percentage of negative sentiment mentions',
        'sentiment-trend-metric': 'Change in sentiment vs previous period',
        
        # Visibility & Performance
        'visibility-metric': 'Overall visibility score across platforms',
        'visibility-trend-metric': 'Change in visibility score',
        'avg-position-metric': 'Average position in AI responses',
        'engagement-metric': 'Overall engagement score',
        'engagement-growth-metric': 'Growth in engagement score',
        
        # Competitive Metrics
        'share-metric': 'Your share of voice percentage',
        'market-position-metric': 'Your ranking among competitors',
        'competitor-gap-metric': 'Difference from top competitor',
        'competitors-metric': 'Number of competitors tracked',
        'market-share-trend-metric': 'Trend in market share',
        
        # Quality & Health
        'health-score-metric': 'Overall domain AI-friendliness score',
        'content-quality-metric': 'Content quality score based on engagement',
        'answer-coverage-metric': 'Percentage of prompts with answers',
        'topics-covered-metric': 'Number of topics with mentions',
        
        # Alerts & Issues
        'active-alerts-metric': 'Currently active misinformation alerts',
        'critical-issues-metric': 'High-severity issues requiring attention',
        'misinformation-cases-metric': 'Detected misinformation instances',
        
        # Platform Metrics
        'platform-coverage-quality-metric': 'Quality of platform coverage',
        'platform-consistency-score-metric': 'Consistency across platforms',
        'platform-health-score-metric': 'Platform-specific health metrics',
        
        # Prompts
        'total-prompts-metric': 'Total number of prompts tracked',
        'prompt-groups-metric': 'Total number of prompt groups',
        
        # Charts
        'mentions-chart': 'Line chart showing mentions over time',
        'platform-chart': 'Bar chart of mentions by platform',
        'sentiment-chart': 'Pie chart of sentiment distribution',
        'sentiment-trend-chart': 'Line chart of sentiment over time',
        'citation-trend-chart': 'Line chart of citations over time',
        'visibility-trend-chart': 'Line chart of visibility score changes',
        'share-of-voice-chart': 'Pie chart comparing share of voice',
        'competitor-comparison-chart': 'Bar chart comparing competitors',
        'citations-by-platform-chart': 'Bar chart of citations by platform',
        'topic-trends-chart': 'Line chart of topic mention trends',
        'platform-sentiment-breakdown-chart': 'Sentiment breakdown by platform',
        
        # Tables
        'competitors-table': 'Table showing competitor rankings and metrics',
        'topics-table': 'Table of top topics with mentions',
        'top-prompts-table': 'Table of best performing prompts',
        
        # Text
        'summary-text': 'Executive summary text section',
    }
    
    return descriptions.get(widget_id, f'Widget: {widget_id}')


def get_data_source(widget_id):
    """Explain how each widget retrieves data"""
    sources = {
        # Mentions
        'total-mentions-metric': 'PromptAnalytics.objects.filter(is_mention=True)',
        'mention-rate-metric': 'Mentions / Total Prompts * 100',
        'mention-growth-metric': 'Current mentions - Previous mentions',
        'platform-coverage-metric': 'Count of distinct platforms with mentions',
        
        # Citations
        'total-citations-metric': 'PromptAnalytics.objects.aggregate(Sum(total_citations))',
        'citation-rate-metric': 'Total Citations / Total Mentions',
        'citation-density-metric': 'Total Citations / Total Responses',
        'unique-sources-metric': 'Count distinct citation URLs',
        'domain-citations-metric': 'Citations where URL contains domain',
        'valid-links-metric': 'Count citations with valid HTTP responses',
        'broken-links-metric': 'Count citations with HTTP errors',
        'pending-citations-metric': 'Count citations not yet verified',
        
        # Sentiment
        'avg-sentiment-metric': 'PromptAnalytics.objects.aggregate(Avg(sentiment_score))',
        'positive-sentiment-metric': 'Count sentiment > 0 / Total * 100',
        'negative-sentiment-metric': 'Count sentiment < 0 / Total * 100',
        'sentiment-trend-metric': 'Current avg sentiment - Previous avg sentiment',
        
        # Visibility
        'visibility-metric': 'PromptAnalytics.objects.aggregate(Avg(visibility_score))',
        'avg-position-metric': 'PromptAnalytics.objects.aggregate(Avg(position))',
        'engagement-metric': 'Calculated from visibility + sentiment + citations',
        
        # Competitive
        'share-metric': 'Domain mentions / (Domain + Competitor mentions) * 100',
        'market-position-metric': 'Rank based on total mentions',
        'competitor-gap-metric': 'Top competitor mentions - Your mentions',
        'competitors-metric': 'Competitor.objects.count()',
        
        # Quality
        'health-score-metric': 'Weighted average of multiple quality metrics',
        'content-quality-metric': 'Based on sentiment, engagement, citations',
        'answer-coverage-metric': 'Mentions with responses / Total prompts * 100',
        'topics-covered-metric': 'Count distinct topics with mentions',
        
        # Alerts
        'active-alerts-metric': 'Alert.objects.filter(status=active)',
        'critical-issues-metric': 'Alert.objects.filter(severity=critical)',
        'misinformation-cases-metric': 'Alert.objects.filter(type=misinformation)',
        'broken-links-metric': 'Citation.objects.filter(status=broken)',
        
        # Charts
        'mentions-chart': 'PromptAnalytics grouped by date, count mentions',
        'platform-chart': 'PromptAnalytics grouped by platform, count mentions',
        'sentiment-chart': 'Distribution of positive/neutral/negative',
        'citation-trend-chart': 'Citations over time from PromptAnalytics',
        'visibility-trend-chart': 'Visibility scores over time',
        'share-of-voice-chart': 'Compare domain vs competitors mentions',
        'competitor-comparison-chart': 'Competitor metrics side by side',
        'citations-by-platform-chart': 'Citations grouped by platform',
        'topic-trends-chart': 'Topic mentions over time',
        
        # Tables
        'competitors-table': 'Competitor rankings with mentions, share %',
        'topics-table': 'Topics with mention counts and sentiment',
        'top-prompts-table': 'Prompts sorted by performance metrics',
    }
    
    return sources.get(widget_id, 'Custom data aggregation')


def audit_widget(fetcher, widget_id):
    """Test a single widget and return audit results"""
    try:
        data = fetcher.fetch_widget_data(widget_id)
        
        result = {
            'widget_id': widget_id,
            'status': 'SUCCESS',
            'type': data.get('type'),
            'label': data.get('label'),
            'description': get_widget_description(widget_id),
            'data_source': get_data_source(widget_id),
            'data_preview': None,
            'issues': []
        }
        
        # Extract data preview based on type
        if data.get('type') == 'metric':
            value = data.get('value', 0)
            growth = data.get('growth', 0)
            result['data_preview'] = f"Value: {value}, Growth: {growth}"
            
            # Check for issues
            if value == 0 and growth == 0:
                result['issues'].append('⚠️  Returns all zeros - may need sample data')
            
        elif data.get('type') == 'chart':
            chart_data = data.get('data', [])
            result['data_preview'] = f"{len(chart_data)} data points"
            
            if len(chart_data) == 0:
                result['issues'].append('❌ No data points - chart will be empty')
            elif all(point.get('value', 0) == 0 or point.get('mentions', 0) == 0 for point in chart_data):
                result['issues'].append('⚠️  All values are zero')
                
        elif data.get('type') == 'table':
            rows = data.get('rows', [])
            columns = data.get('columns', [])
            result['data_preview'] = f"{len(rows)} rows × {len(columns)} columns"
            
            if len(rows) == 0:
                result['issues'].append('❌ No data rows - table will be empty')
            
        return result
        
    except Exception as e:
        return {
            'widget_id': widget_id,
            'status': 'ERROR',
            'type': None,
            'label': None,
            'description': get_widget_description(widget_id),
            'data_source': get_data_source(widget_id),
            'data_preview': None,
            'issues': [f'❌ ERROR: {str(e)[:100]}']
        }


def main():
    print('=' * 100)
    print('COMPREHENSIVE WIDGET AUDIT')
    print('=' * 100)
    print()
    
    # Get domain and setup
    domain = Domain.objects.first()
    org = Organisation.objects.first()
    
    if not domain:
        print('❌ No domain found in database')
        return
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    fetcher = WidgetDataFetcher(domain, start_date, end_date, org)
    
    # Get all templates
    templates = ReportTemplate.objects.all().order_by('name')
    
    print(f'Found {templates.count()} report templates')
    print(f'Domain: {domain.name}')
    print(f'Date Range: {start_date.date()} to {end_date.date()}')
    print()
    
    # Collect all unique widget IDs
    all_widget_ids = set()
    template_widgets = {}
    
    for template in templates:
        widget_ids = []
        if template.grid_rows:
            for row in template.grid_rows:
                # Try both 'widgets' and 'slots' keys (frontend uses 'slots')
                widgets = row.get('widgets', []) or row.get('slots', [])
                for widget in widgets:
                    widget_id = widget.get('id')
                    if widget_id:
                        all_widget_ids.add(widget_id)
                        widget_ids.append(widget_id)
        template_widgets[template.name] = widget_ids
    
    print(f'Total Unique Widgets: {len(all_widget_ids)}')
    print()
    
    # Audit each template
    all_results = []
    
    for template_name, widget_ids in template_widgets.items():
        if not widget_ids:
            continue
            
        print('=' * 100)
        print(f'📊 {template_name}')
        print('=' * 100)
        print()
        
        for i, widget_id in enumerate(widget_ids, 1):
            print(f'[{i}/{len(widget_ids)}] Testing: {widget_id}')
            
            result = audit_widget(fetcher, widget_id)
            all_results.append(result)
            
            # Print result
            status_icon = '✅' if result['status'] == 'SUCCESS' else '❌'
            print(f'  {status_icon} Status: {result["status"]}')
            print(f'     Type: {result["type"]}')
            print(f'     Label: {result["label"]}')
            print(f'     Description: {result["description"]}')
            print(f'     Data Source: {result["data_source"]}')
            print(f'     Preview: {result["data_preview"]}')
            
            if result['issues']:
                for issue in result['issues']:
                    print(f'     {issue}')
            
            print()
        
        print()
    
    # Summary
    print('=' * 100)
    print('AUDIT SUMMARY')
    print('=' * 100)
    print()
    
    success_count = sum(1 for r in all_results if r['status'] == 'SUCCESS')
    error_count = sum(1 for r in all_results if r['status'] == 'ERROR')
    issue_count = sum(1 for r in all_results if r['issues'])
    
    print(f'Total Widgets Tested: {len(all_results)}')
    print(f'✅ Success: {success_count}')
    print(f'❌ Errors: {error_count}')
    print(f'⚠️  With Issues: {issue_count}')
    print()
    
    if error_count > 0:
        print('ERRORS:')
        for r in all_results:
            if r['status'] == 'ERROR':
                print(f'  ❌ {r["widget_id"]}: {r["issues"][0] if r["issues"] else "Unknown error"}')
        print()
    
    if issue_count > 0:
        print('ISSUES:')
        for r in all_results:
            if r['issues'] and r['status'] == 'SUCCESS':
                print(f'  ⚠️  {r["widget_id"]}:')
                for issue in r['issues']:
                    print(f'      {issue}')
        print()
    
    # Save detailed report
    report_file = 'widget_audit_report.json'
    with open(report_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f'📄 Detailed report saved to: {report_file}')
    print()
    print('=' * 100)


if __name__ == '__main__':
    main()

