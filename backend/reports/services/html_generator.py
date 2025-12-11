"""
HTML Generator for Report Templates
Generates styled HTML for PDF conversion with exact color matching
"""
from typing import List, Dict, Any
from .svg_chart_generator import SVGChartGenerator


class HTMLReportGenerator:
    """Generates styled HTML for WeasyPrint PDF conversion"""

    # Color schemes matching frontend exactly - MORE VISIBLE gradients
    COLOR_SCHEMES = {
        'blue': {
            'gradient_start': 'rgba(59, 130, 246, 0.15)',
            'gradient_end': 'rgba(59, 130, 246, 0.05)',
            'border': '#93c5fd',
            'text': '#2563eb',
            'bg': '#eff6ff',
            'status_text': '#2563eb',
        },
        'purple': {
            'gradient_start': 'rgba(139, 92, 246, 0.15)',
            'gradient_end': 'rgba(139, 92, 246, 0.05)',
            'border': '#c4b5fd',
            'text': '#7c3aed',
            'bg': '#faf5ff',
            'status_text': '#7c3aed',
        },
        'green': {
            'gradient_start': 'rgba(34, 197, 94, 0.15)',
            'gradient_end': 'rgba(34, 197, 94, 0.05)',
            'border': '#86efac',
            'text': '#16a34a',
            'bg': '#f0fdf4',
            'status_text': '#16a34a',
        },
        'orange': {
            'gradient_start': 'rgba(249, 115, 22, 0.15)',
            'gradient_end': 'rgba(249, 115, 22, 0.05)',
            'border': '#fdba74',
            'text': '#ea580c',
            'bg': '#fff7ed',
            'status_text': '#ea580c',
        },
        'red': {
            'gradient_start': 'rgba(239, 68, 68, 0.15)',
            'gradient_end': 'rgba(239, 68, 68, 0.05)',
            'border': '#fca5a5',
            'text': '#dc2626',
            'bg': '#fef2f2',
            'status_text': '#dc2626',
        },
        'yellow': {
            'gradient_start': 'rgba(234, 179, 8, 0.15)',
            'gradient_end': 'rgba(234, 179, 8, 0.05)',
            'border': '#fde047',
            'text': '#ca8a04',
            'bg': '#fefce8',
            'status_text': '#ca8a04',
        },
    }

    def __init__(self, grid_rows: List[Dict], metadata: Dict[str, Any]):
        """
        Initialize HTML generator

        Args:
            grid_rows: List of grid row configurations
            metadata: Report metadata (domain, dates, etc.)
        """
        self.grid_rows = grid_rows
        self.metadata = metadata
        self.svg_generator = SVGChartGenerator()

    def generate(self, widget_data: Dict[str, Any]) -> str:
        """
        Generate complete HTML document

        Args:
            widget_data: Dictionary of widget data from WidgetDataFetcher

        Returns:
            Complete HTML document ready for WeasyPrint
        """
        html_parts = []

        # HTML header
        html_parts.append(self._generate_header())

        # Report header (domain, title, dates)
        html_parts.append(self._generate_report_header())

        # Grid rows with widgets
        for row in self.grid_rows:
            html_parts.append(self._generate_grid_row(row, widget_data))

        # HTML footer
        html_parts.append(self._generate_footer())

        return '\n'.join(html_parts)

    def _generate_header(self) -> str:
        """Generate HTML document header with embedded CSS"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.5;
            color: #1f2937;
            background: white;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        @page {
            size: A4;
            margin: 1.5cm;
        }

        .report-container {
            max-width: 100%;
            margin: 0 auto;
            padding: 0;
        }

        .report-header {
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }

        .report-header h2 {
            font-size: 1.5rem;
            font-weight: 700;
            color: #111827;
        }

        .report-header p {
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: 0.25rem;
        }

        .grid-row {
            display: grid;
            gap: 1rem;
            margin-bottom: 1rem;
            align-items: stretch;
        }

        .grid-single { grid-template-columns: 1fr; }
        .grid-double { grid-template-columns: repeat(2, 1fr); }
        .grid-triple { grid-template-columns: repeat(3, 1fr); }
        .grid-quad { grid-template-columns: repeat(4, 1fr); }

        .widget {
            break-inside: avoid;
            display: flex;
            flex-direction: column;
        }

        .metric-card {
            padding: 1.5rem;
            border-radius: 0.75rem;
            border-width: 1px;
            border-style: solid;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            overflow: hidden;
        }

        .metric-label {
            font-size: 1rem;
            color: #374151;
            font-weight: 500;
            margin-bottom: 0.75rem;
            line-height: 1.3;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 0.75rem;
            letter-spacing: -0.02em;
        }
        
        .metric-subtitle {
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: auto;
            line-height: 1.4;
        }
        
        .metric-growth {
            display: flex;
            align-items: center;
            gap: 0.375rem;
            font-size: 1rem;
            margin-top: 0.5rem;
        }
        
        .metric-growth-icon {
            font-size: 1.125rem;
            line-height: 1;
        }
        
        .metric-growth-value {
            font-weight: 600;
        }
        
        .metric-growth-label {
            color: #6b7280;
            font-weight: 400;
        }
        
        .metric-status {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.875rem;
            margin-top: 0.5rem;
            font-weight: 500;
        }
        
        .text-green { color: #16a34a; }
        .text-red { color: #dc2626; }
        .text-orange { color: #ea580c; }
        .text-blue { color: #2563eb; }
        .text-purple { color: #9333ea; }
        
        /* Chart widget styling */
        .chart-widget {
            padding: 1.5rem;
            border: 1px solid #e5e7eb;
            border-radius: 0.75rem;
            background: white;
        }
        
        .chart-title {
            font-size: 1.125rem;
            font-weight: 600;
            color: #111827;
            margin-bottom: 1rem;
        }

        .metric-growth {
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }

        .metric-growth-value {
            font-weight: 600;
        }

        @media print {
            body {
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
            }
        }
    </style>
</head>
<body>
    <div class="report-container">
"""

    def _generate_report_header(self) -> str:
        """Generate report header with logo, domain and dates"""
        domain_name = self.metadata.get('domain_name', 'Domain')
        domain_url = self.metadata.get('domain_url', '')
        template_name = self.metadata.get('template_name', 'Report')

        period = self.metadata.get('period', {})
        start_date = period.get('start', '')
        end_date = period.get('end', '')

        if start_date and end_date:
            date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        else:
            date_range = "N/A"

        # Generate favicon URL
        favicon_url = ''
        if domain_url:
            # Try to get favicon from domain
            favicon_url = f"https://www.google.com/s2/favicons?domain={domain_url}&sz=64"
        
        logo_html = ''
        if favicon_url:
            logo_html = f'<img src="{favicon_url}" alt="Logo" style="width: 32px; height: 32px; margin-right: 0.75rem; vertical-align: middle; border-radius: 0.25rem;" onerror="this.style.display=\'none\'">'

        return f"""
        <div class="report-header" style="display: flex; align-items: center; border-bottom: 1px solid #e5e7eb; padding-bottom: 1rem; margin-bottom: 1.5rem;">
            {logo_html}
            <div>
                <h2 style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0;">{domain_name}</h2>
                <p style="font-size: 0.875rem; color: #6b7280; margin: 0.25rem 0 0 0;">{template_name}</p>
                <p style="font-size: 0.875rem; color: #6b7280; margin: 0.25rem 0 0 0;">Report Period: {date_range}</p>
            </div>
        </div>
"""

    def _generate_grid_row(self, row: Dict, widget_data: Dict[str, Any]) -> str:
        """Generate a grid row with widgets"""
        grid_type = row.get('type', 'single')
        slots = row.get('slots', [])

        html_parts = [f'<div class="grid-row grid-{grid_type}">']

        for slot in slots:
            if not slot:
                html_parts.append('<div></div>')  # Empty slot
                continue

            widget_id = slot.get('id')
            widget_type = slot.get('type', 'metric')
            data = widget_data.get(widget_id, {})

            if widget_type == 'metric':
                html_parts.append(self._generate_metric_widget(widget_id, data))
            elif widget_type == 'chart':
                html_parts.append(self._generate_chart_widget(widget_id, data))
            elif widget_type == 'table':
                html_parts.append(self._generate_table_widget(widget_id, data))

        html_parts.append('</div>')

        return '\n'.join(html_parts)

    def _generate_metric_widget(self, widget_id: str, data: Dict[str, Any]) -> str:
        """Generate a metric widget with gradients, growth, and subtitle"""
        # Determine color scheme based on widget ID
        color_scheme = self._get_color_scheme(widget_id)
        colors = self.COLOR_SCHEMES[color_scheme]

        # Extract data
        value = data.get('value', '0')
        label = data.get('label', 'Metric')
        growth = data.get('growth')
        subtitle = data.get('subtitle', '')

        # Format value
        format_type = data.get('format', 'number')
        if format_type == 'percentage':
            formatted_value = f"{value:.1f}%"
        elif format_type == 'decimal':
            formatted_value = f"{value:.2f}"
        elif format_type == 'ordinal':
            formatted_value = f"#{int(value)}"
        else:
            try:
                formatted_value = f"{int(value):,}"
            except (ValueError, TypeError):
                formatted_value = str(value)

        # Growth indicator with icon and "from last month"
        growth_html = ''
        if growth is not None and growth != 0:
            try:
                growth_val = float(growth)
                # Use nice arrow icons
                arrow = '↗' if growth_val > 0 else '↘'
                growth_color = '#16a34a' if growth_val > 0 else '#dc2626'
                growth_text = f"{'+' if growth_val > 0 else ''}{growth_val:.1f}%"

                growth_html = f'''
                <div class="metric-growth">
                    <span class="metric-growth-icon" style="color: {growth_color};">{arrow}</span>
                    <span class="metric-growth-value" style="color: {growth_color};">{growth_text}</span>
                    <span class="metric-growth-label">from last month</span>
                </div>
                '''
            except (ValueError, TypeError):
                pass
        
        # Status text based on widget type and value
        status_html = ''
        status_text = self._get_status_text(widget_id, data)
        if status_text and not growth_html:  # Only show status if no growth
            status_color = colors.get('status_text', colors['text'])
            status_html = f'''
            <div class="metric-status" style="color: {status_color};">
                <span>↗</span>
                <span>{status_text}</span>
            </div>
            '''
        
        # Subtitle
        subtitle_html = ''
        if subtitle:
            # Truncate long subtitles
            display_subtitle = subtitle if len(str(subtitle)) <= 35 else str(subtitle)[:32] + '...'
            subtitle_html = f'''
            <div class="metric-subtitle">{display_subtitle}</div>
            '''

        return f'''
        <div class="widget metric-card" style="
            background: linear-gradient(to bottom right, {colors['gradient_start']}, {colors['gradient_end']});
            border-color: {colors['border']};
        ">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {colors['text']};">{formatted_value}</div>
            {growth_html}
            {status_html}
            {subtitle_html}
        </div>
        '''

    def _generate_chart_widget(self, widget_id: str, data: Dict[str, Any]) -> str:
        """Generate a chart widget with professional SVG visualization"""
        label = data.get('label', 'Chart')
        chart_type = data.get('chart_type', 'bar')
        chart_data = data.get('data', [])

        if not chart_data:
            return f'''
            <div class="chart-widget" style="
                padding: 1.5rem;
                border: 1px solid #e5e7eb;
                border-radius: 0.75rem;
                background: white;
            ">
                <h3 style="font-size: 1rem; font-weight: 600; margin-bottom: 1rem;">{label}</h3>
                <div style="height: 200px; background: #f9fafb; display: flex; align-items: center; justify-content: center; color: #6b7280; font-size: 0.875rem;">
                    No chart data available
                </div>
            </div>
            '''

        # Generate SVG chart based on type
        # The SVG generator has smart key detection, so it will auto-detect the correct keys
        chart_svg = ''
        try:
            if chart_type == 'bar':
                # Smart detection will handle: platform/name/category + value/count
                chart_svg = self.svg_generator.generate_bar_chart(chart_data)
            elif chart_type == 'line':
                # Smart detection will handle: date/time/day + value/count/score
                chart_svg = self.svg_generator.generate_line_chart(chart_data)
            elif chart_type == 'pie':
                # Smart detection will handle: name/label/domain + value/count/percentage
                chart_svg = self.svg_generator.generate_pie_chart(chart_data)
            else:
                # Default to bar chart
                chart_svg = self.svg_generator.generate_bar_chart(chart_data)
        except Exception as e:
            import traceback
            error_msg = str(e)[:50]
            print(f"Chart generation error: {error_msg}")
            print(traceback.format_exc())
            chart_svg = f'<svg width="600" height="300"><text x="300" y="150" text-anchor="middle" fill="#6b7280">Error: {error_msg}</text></svg>'

        return f'''
        <div class="chart-widget">
            <h3 class="chart-title">{label}</h3>
            <div style="width: 100%; overflow: hidden;">
                {chart_svg}
            </div>
        </div>
        '''


    def _generate_table_widget(self, widget_id: str, data: Dict[str, Any]) -> str:
        """Generate a table widget"""
        label = data.get('label', 'Table')
        columns = data.get('columns', [])
        rows = data.get('rows', [])

        if not columns or not rows:
            return f'<div class="widget"><p>No data available</p></div>'

        # Build table HTML
        table_html = ['<table style="width: 100%; border-collapse: collapse;">']

        # Header
        table_html.append('<thead><tr style="background: #f3f4f6;">')
        for col in columns:
            table_html.append(f'<th style="border: 1px solid #e5e7eb; padding: 0.75rem; text-align: left; font-weight: 600; font-size: 0.875rem;">{col}</th>')
        table_html.append('</tr></thead>')

        # Rows - handle both dict and list formats
        table_html.append('<tbody>')
        for i, row in enumerate(rows[:10]):  # Limit to 10 rows
            bg_color = 'white' if i % 2 == 0 else '#f9fafb'
            table_html.append(f'<tr style="background: {bg_color};">')
            
            # If row is a dict, convert to list based on column keys
            if isinstance(row, dict):
                # Map column names to dict keys (case-insensitive)
                for col in columns:
                    # Try different key formats
                    col_lower = col.lower().replace(' ', '_').replace('%', '')
                    
                    # Try exact match first
                    if col in row:
                        cell_value = row[col]
                    # Try lowercase with underscores
                    elif col_lower in row:
                        cell_value = row[col_lower]
                    # Try common variations
                    elif col_lower == 'rank' and 'rank' in row:
                        cell_value = row['rank']
                    elif col_lower == 'name' and 'name' in row:
                        cell_value = row['name']
                    elif col_lower == 'mentions' and 'mentions' in row:
                        cell_value = row['mentions']
                    elif col_lower == 'share' and 'share' in row:
                        cell_value = f"{row['share']}%"
                    else:
                        cell_value = ''
                    
                    table_html.append(f'<td style="border: 1px solid #e5e7eb; padding: 0.75rem; font-size: 0.875rem;">{cell_value}</td>')
            else:
                # Row is already a list
                for cell in row:
                    table_html.append(f'<td style="border: 1px solid #e5e7eb; padding: 0.75rem; font-size: 0.875rem;">{cell}</td>')
            
            table_html.append('</tr>')
        table_html.append('</tbody>')

        table_html.append('</table>')

        return f'''
        <div class="widget" style="
            padding: 1.5rem;
            border: 1px solid #e5e7eb;
            border-radius: 0.75rem;
            background: white;
        ">
            <h3 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem; color: #111827;">{label}</h3>
            {''.join(table_html)}
        </div>
        '''

    def _generate_footer(self) -> str:
        """Generate HTML document footer"""
        return """
    </div>
</body>
</html>
"""

    def _get_color_scheme(self, widget_id: str) -> str:
        """Determine color scheme based on widget ID - matches frontend exactly"""
        widget_id_lower = widget_id.lower()

        # Critical/issues/alerts -> Red
        if any(keyword in widget_id_lower for keyword in ['critical', 'issue', 'alert', 'error', 'misinformation']):
            return 'red'
        # Broken/warnings -> Yellow
        elif any(keyword in widget_id_lower for keyword in ['broken', 'warning', 'need']):
            return 'yellow'
        # Sentiment/positive/health -> Green
        elif any(keyword in widget_id_lower for keyword in ['sentiment', 'positive', 'health', 'quality', 'coverage', 'answer']):
            return 'green'
        # Platform/competitor/position/rank -> Purple
        elif any(keyword in widget_id_lower for keyword in ['platform', 'competitor', 'position', 'rank', 'topic', 'source']):
            return 'purple'
        # Share/voice/market/growth -> Orange
        elif any(keyword in widget_id_lower for keyword in ['share', 'voice', 'market', 'growth', 'trend']):
            return 'orange'
        # Citation/mention/content -> Blue (default)
        else:
            return 'blue'  # Default
    
    def _get_status_text(self, widget_id: str, data: Dict[str, Any]) -> str:
        """Generate status text like 'Strong growth', 'Improving', etc."""
        widget_id_lower = widget_id.lower()
        value = data.get('value', 0)
        growth = data.get('growth', 0)
        
        try:
            value = float(value) if value else 0
            growth = float(growth) if growth else 0
        except (ValueError, TypeError):
            value = 0
            growth = 0
        
        # Growth widgets
        if 'growth' in widget_id_lower:
            if value > 20:
                return 'Strong growth'
            elif value > 0:
                return 'Growing'
            elif value < -10:
                return 'Declining'
            else:
                return 'Stable'
        
        # Quality/score widgets
        elif 'quality' in widget_id_lower or 'score' in widget_id_lower:
            if value >= 80:
                return 'High quality'
            elif value >= 60:
                return 'Good quality'
            else:
                return 'Needs improvement'
        
        # Coverage widgets
        elif 'coverage' in widget_id_lower:
            if value >= 90:
                return 'Excellent coverage'
            elif value >= 70:
                return 'Good coverage'
            else:
                return 'Partial coverage'
        
        # Sentiment widgets
        elif 'sentiment' in widget_id_lower:
            if value > 0.5:
                return 'Positive overall'
            elif value > 0:
                return 'Slightly positive'
            elif value < -0.5:
                return 'Negative trend'
            else:
                return 'Neutral'
        
        # Topic/content widgets
        elif 'topic' in widget_id_lower:
            return 'Topics tracked'
        
        # Source widgets
        elif 'source' in widget_id_lower:
            return 'Unique sources'
        
        # Alert widgets
        elif 'alert' in widget_id_lower:
            if value == 0:
                return 'No active alerts'
            else:
                return 'Require attention'
        
        # Issue widgets
        elif 'issue' in widget_id_lower or 'critical' in widget_id_lower:
            if value == 0:
                return 'No issues detected'
            else:
                return 'High priority'
        
        # Broken links
        elif 'broken' in widget_id_lower:
            if value == 0:
                return 'All links verified'
            else:
                return 'Need fixing'
        
        # Default - no status text
        return ''


def generate_html_report(
    grid_rows: List[Dict],
    widget_data: Dict[str, Any],
    metadata: Dict[str, Any]
) -> str:
    """
    Convenience function to generate HTML report

    Args:
        grid_rows: Grid row configurations
        widget_data: Widget data from WidgetDataFetcher
        metadata: Report metadata

    Returns:
        Complete HTML document
    """
    generator = HTMLReportGenerator(grid_rows, metadata)
    return generator.generate(widget_data)
