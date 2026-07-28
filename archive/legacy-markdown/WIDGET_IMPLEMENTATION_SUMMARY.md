# Widget Implementation Summary

## Overview
Implemented a complete widget-based custom report generation system that fetches real data from the database and generates PDF reports.

## What Was Built

### 1. Widget Data Fetcher Service (`backend/reports/services/widget_data_fetcher.py`)
A comprehensive service that maps widget IDs to database queries and returns real data.

**Implemented Widget Categories:**
- ✅ **Prompts** (5 widgets)
- ✅ **Citations** (4 widgets)
- ✅ **Topics** (3 widgets)
- ✅ **Share of Voice** (3 widgets)
- ✅ **Historical Trends** (4 widgets)

**Total: 19+ widgets implemented**

#### Prompts Widgets
1. `total-prompts-metric` - Total number of prompts
2. `active-prompts-metric` - Completed/active prompts
3. `prompt-groups-metric` - Total prompt groups
4. `prompts-by-platform-chart` - Bar chart of prompts by platform
5. `top-prompts-table` - Top performing prompts table

#### Citations Widgets
1. `total-citations-metric` - Total citations count with growth
2. `citation-rate-metric` - Citation rate percentage
3. `citation-density-metric` - Average citations per response
4. `citations-by-platform-chart` - Citations breakdown by platform

#### Topics Widgets
1. `total-topics-metric` - Total topics count
2. `topics-coverage-metric` - Percentage of keywords in topics
3. `topics-table` - Top topics with mentions and sentiment

#### Share of Voice Widgets
1. `share-metric` - Domain's share of voice percentage
2. `market-position-metric` - Domain's rank among competitors
3. `share-of-voice-chart` - Pie chart comparing domain vs competitors

#### Historical Trends Widgets
1. `mentions-chart` - Line chart of mentions over time
2. `visibility-trend-chart` - Visibility score trend
3. `sentiment-trend-chart` - Sentiment trend over time
4. `citation-trend-chart` - Citations trend over time

### 2. Updated Main Report Generator (`backend/reports/services/main.py`)

**Added Custom Template Support:**
- Detects if report uses custom template (`template_type='custom'`)
- Uses `WidgetDataFetcher` to fetch data for all widgets
- Passes template to PDF generator
- Falls back to predefined templates for backward compatibility
- **Excel/PowerPoint blocked** for custom templates (PDF only)

### 3. Enhanced PDF Generator (`backend/reports/services/pdf_generator.py`)

**Added 300+ lines of custom template rendering:**
- `_generate_custom_template()` - Main custom template renderer
- `_add_custom_header()` - Header with domain info and favicon
- `_render_grid_row()` - Renders grid layouts (single/double/triple/quad)
- `_render_widget()` - Widget type dispatcher
- `_render_metric_widget()` - Metric cards with value, growth, subtitle
- `_render_chart_widget()` - Chart dispatcher (line/bar/pie)
- `_create_line_chart()` - Line charts using ReportLab
- `_create_bar_chart()` - Bar charts using ReportLab
- `_create_pie_chart()` - Pie charts using ReportLab
- `_render_table_widget()` - Table rendering with headers

### 4. Database Schema Fixed
Fixed `report_templates` table missing columns:
- Added `template_type` column
- Added `grid_rows` column (JSONB)
- Added `organisation_id` column (FK)
- Added `created_by_id` column (FK)

## How It Works

### Data Flow

```
User creates custom template in builder
    ↓
Template saved with grid_rows JSON
    ↓
User generates report
    ↓
Backend: generate_report(report_id)
    ↓
Check if custom template
    ↓
YES: Use WidgetDataFetcher
    ├─ Loop through grid_rows
    ├─ For each widget, call fetch_widget_data(widget_id)
    ├─ Query database (Prompts, Analytics, Topics, Competitors)
    ├─ Calculate metrics (growth, rates, trends)
    ├─ Return structured data dict
    └─ Add _metadata with domain info
    ↓
Pass data + template to PDFReportGenerator
    ↓
PDF Generator: _generate_custom_template()
    ├─ Add header (domain name, template name, date range)
    ├─ Loop through grid_rows
    │   ├─ Determine grid type (single/double/triple/quad)
    │   ├─ For each widget in row:
    │   │   ├─ Get widget data from data dict
    │   │   ├─ Render based on type:
    │   │   │   ├─ Metric: Format value, show growth, subtitle
    │   │   │   ├─ Chart: Create ReportLab chart (line/bar/pie)
    │   │   │   └─ Table: Create table with headers and rows
    │   │   └─ Return ReportLab element
    │   └─ Layout widgets in grid (Table with columns)
    └─ Build PDF with footer
    ↓
Save PDF file to disk
    ↓
Return success
```

### Example Widget Data Structure

**Metric Widget:**
```python
{
    'type': 'metric',
    'value': 1547,
    'label': 'Total Mentions',
    'format': 'number',
    'growth': 24.5,
    'trend': 'up',
    'subtitle': 'vs last period'
}
```

**Chart Widget:**
```python
{
    'type': 'chart',
    'chart_type': 'line',
    'data': [
        {'date': '2025-01-01', 'value': 120},
        {'date': '2025-01-02', 'value': 135},
        # ...
    ],
    'x_axis': 'date',
    'y_axis': 'value',
    'label': 'Mentions Over Time'
}
```

**Table Widget:**
```python
{
    'type': 'table',
    'columns': ['Topic', 'Keywords', 'Mentions', 'Avg Sentiment'],
    'rows': [
        {'topic': 'AI Integration', 'keywords': 15, 'mentions': 234, 'sentiment': 0.75},
        {'topic': 'Product Features', 'keywords': 12, 'mentions': 189, 'sentiment': 0.68},
        # ...
    ]
}
```

## Database Queries Used

### Prompts Module
- `Prompt.objects.filter(group__domain=domain)`
- `PromptAnalytics.objects.filter(prompt__group__domain=domain, created_at__range)`
- Aggregations: `Count`, `Avg('sentiment_score')`

### Citations Module
- `PromptAnalytics.objects.exclude(Q(citations__isnull=True) | Q(citations=[]))`
- Count citations, calculate rates and density

### Topics Module
- `Topic.objects.filter(domain=domain)`
- `Keyword.objects.filter(domain=domain, topics__isnull=False)`
- Join with `PromptAnalytics` for mention counts

### Share of Voice Module
- `PromptAnalytics.objects.filter(is_mention=True)`
- `CompetitorAnalytics.objects.filter(competitor__domain=domain)`
- `Competitor.objects.filter(domain=domain).order_by('-total_mentions')`

### Historical Trends
- Daily aggregations using date ranges
- `created_at__gte` and `created_at__lt` for time slicing
- `Avg`, `Count` aggregations per day

## Features

### ✅ Implemented
- Custom template detection
- Widget data fetching with real database queries
- PDF generation with custom layouts
- Grid system (single/double/triple/quad columns)
- Metric cards with growth indicators
- Line, bar, and pie charts
- Tables with formatted data
- Growth calculations (vs previous period)
- Trend indicators (up/down/neutral)
- Proper formatting (number, percentage, decimal, ordinal)
- Domain header with favicon
- Date range in header

### 🚫 Not Yet Implemented
- Excel format for custom templates
- PowerPoint format for custom templates
- Widget configuration options (date ranges, filters)
- Real-time data refresh
- Widget preview with real data in builder

## Testing Checklist

To test the widget system:

1. ✅ **Database Schema** - Run the SQL fix script
2. ⏳ **Create Custom Template**
   - Go to `/reports/create-template`
   - Add grid rows
   - Drag widgets (prompts, citations, topics, share of voice, trends)
   - Save template
3. ⏳ **Generate Report**
   - Create scheduled report with custom template
   - Or use "Generate Now" with custom template
   - Select PDF format only
4. ⏳ **Verify PDF Output**
   - Check header has domain name and date range
   - Check all widgets render correctly
   - Check charts display data
   - Check tables have data
   - Check metrics show correct values
5. ⏳ **Test Different Widgets**
   - Test at least one from each category
   - Verify real data is fetched
   - Check growth calculations

## Files Created/Modified

### Created
- `backend/reports/services/widget_data_fetcher.py` (750+ lines)
- `fix_report_templates.sql` (database fix)
- `WIDGET_IMPLEMENTATION_SUMMARY.md` (this file)

### Modified
- `backend/reports/services/main.py` (~50 lines added)
- `backend/reports/services/pdf_generator.py` (~300 lines added)

## Known Limitations

1. **Charts are basic** - ReportLab charts are simple, no advanced styling
2. **No widget configuration** - All widgets use hardcoded date ranges
3. **PDF only** - Excel/PowerPoint not supported yet
4. **Limited to 10 rows** - Tables truncate to 10 rows to save space
5. **No error handling for missing data** - Assumes data exists
6. **Growth comparison** - Uses equal previous period, not custom periods

## Next Steps (If Needed)

1. Add error handling for missing data
2. Implement widget configuration (date ranges, filters)
3. Add more chart types (stacked bar, area, scatter)
4. Improve chart styling and legends
5. Add Excel/PowerPoint support for custom templates
6. Add widget preview with real data in builder
7. Add pagination for large tables
8. Add caching for frequently accessed data
9. Add async report generation (Celery tasks)
10. Add report scheduling for custom templates

## Usage Example

```python
# In Django shell
from reports.models import GeneratedReport, ReportTemplate
from domains.models import Domain
from authentication.models import Organisation
from datetime import timedelta
from django.utils import timezone

# Get a domain
domain = Domain.objects.first()
org = domain.organisation

# Get a custom template
template = ReportTemplate.objects.filter(
    template_type='custom',
    organisation=org
).first()

# Create a generated report
report = GeneratedReport.objects.create(
    organisation=org,
    domain=domain,
    name=f"{template.name} - {timezone.now().date()}",
    report_type=template.name,
    format='PDF',
    data_period_start=timezone.now().date() - timedelta(days=30),
    data_period_end=timezone.now().date(),
    scheduled_report=None  # Or link to a ScheduledReport
)

# Generate the report
from reports.services.main import generate_report
success = generate_report(report.id)

if success:
    report.refresh_from_db()
    print(f"Report generated: {report.file_path}")
else:
    print("Report generation failed")
```

## Summary

We've successfully built a complete widget-based report generation system that:
- ✅ Fetches real data from database
- ✅ Supports 19+ widgets across 5 categories
- ✅ Generates professional PDF reports
- ✅ Handles custom grid layouts
- ✅ Shows metrics with growth indicators
- ✅ Renders charts and tables
- ✅ Maintains backward compatibility with predefined templates

The system is ready for testing and can be extended with more widgets and formats as needed!
