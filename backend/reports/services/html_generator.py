"""
HTML Generator for Report Templates
Generates styled HTML for PDF conversion with exact color matching
"""
from typing import List, Dict, Any
from .svg_chart_generator import SVGChartGenerator


class HTMLReportGenerator:
    """Generates styled HTML for WeasyPrint PDF conversion"""

    # Color schemes for PDF - slightly higher opacity for better visibility in PDF
    # WeasyPrint renders gradients differently than browsers
    COLOR_SCHEMES = {
        'blue': {
            'gradient_start': 'rgba(59, 130, 246, 0.15)',   # More visible in PDF
            'gradient_end': 'rgba(59, 130, 246, 0.08)',
            'border': '#bfdbfe',                             # border-blue-200
            'text': '#2563eb',                               # text-blue-600
            'bg': '#eff6ff',                                 # bg-blue-50
            'status_text': '#2563eb',
        },
        'purple': {
            'gradient_start': 'rgba(168, 85, 247, 0.15)',
            'gradient_end': 'rgba(168, 85, 247, 0.08)',
            'border': '#e9d5ff',                             # border-purple-200
            'text': '#9333ea',                               # text-purple-600
            'bg': '#faf5ff',                                 # bg-purple-50
            'status_text': '#9333ea',
        },
        'green': {
            'gradient_start': 'rgba(34, 197, 94, 0.15)',
            'gradient_end': 'rgba(34, 197, 94, 0.08)',
            'border': '#bbf7d0',                             # border-green-200
            'text': '#16a34a',                               # text-green-600
            'bg': '#f0fdf4',                                 # bg-green-50
            'status_text': '#16a34a',
        },
        'orange': {
            'gradient_start': 'rgba(249, 115, 22, 0.15)',
            'gradient_end': 'rgba(249, 115, 22, 0.08)',
            'border': '#fed7aa',                             # border-orange-200
            'text': '#ea580c',                               # text-orange-600
            'bg': '#fff7ed',                                 # bg-orange-50
            'status_text': '#ea580c',
        },
        'red': {
            'gradient_start': 'rgba(239, 68, 68, 0.15)',
            'gradient_end': 'rgba(239, 68, 68, 0.08)',
            'border': '#fecaca',                             # border-red-200
            'text': '#dc2626',                               # text-red-600
            'bg': '#fef2f2',                                 # bg-red-50
            'status_text': '#dc2626',
        },
        'yellow': {
            'gradient_start': 'rgba(234, 179, 8, 0.15)',
            'gradient_end': 'rgba(234, 179, 8, 0.08)',
            'border': '#fef08a',                             # border-yellow-200
            'text': '#ca8a04',                               # text-yellow-600
            'bg': '#fefce8',                                 # bg-yellow-50
            'status_text': '#ca8a04',
        },
        # Additional colors to match frontend widgets
        'indigo': {
            'gradient_start': 'rgba(99, 102, 241, 0.15)',
            'gradient_end': 'rgba(99, 102, 241, 0.08)',
            'border': '#c7d2fe',                             # border-indigo-200
            'text': '#4f46e5',                               # text-indigo-600
            'bg': '#eef2ff',                                 # bg-indigo-50
            'status_text': '#4f46e5',
        },
        'cyan': {
            'gradient_start': 'rgba(6, 182, 212, 0.15)',
            'gradient_end': 'rgba(6, 182, 212, 0.08)',
            'border': '#a5f3fc',                             # border-cyan-200
            'text': '#0891b2',                               # text-cyan-600
            'bg': '#ecfeff',                                 # bg-cyan-50
            'status_text': '#0891b2',
        },
        'teal': {
            'gradient_start': 'rgba(20, 184, 166, 0.15)',
            'gradient_end': 'rgba(20, 184, 166, 0.08)',
            'border': '#99f6e4',                             # border-teal-200
            'text': '#0d9488',                               # text-teal-600
            'bg': '#f0fdfa',                                 # bg-teal-50
            'status_text': '#0d9488',
        },
        'amber': {
            'gradient_start': 'rgba(245, 158, 11, 0.15)',
            'gradient_end': 'rgba(245, 158, 11, 0.08)',
            'border': '#fde68a',                             # border-amber-200
            'text': '#d97706',                               # text-amber-600
            'bg': '#fffbeb',                                 # bg-amber-50
            'status_text': '#d97706',
        },
        'violet': {
            'gradient_start': 'rgba(139, 92, 246, 0.15)',
            'gradient_end': 'rgba(139, 92, 246, 0.08)',
            'border': '#ddd6fe',                             # border-violet-200
            'text': '#7c3aed',                               # text-violet-600
            'bg': '#f5f3ff',                                 # bg-violet-50
            'status_text': '#7c3aed',
        },
        'emerald': {
            'gradient_start': 'rgba(16, 185, 129, 0.15)',
            'gradient_end': 'rgba(16, 185, 129, 0.08)',
            'border': '#a7f3d0',                             # border-emerald-200
            'text': '#059669',                               # text-emerald-600
            'bg': '#ecfdf5',                                 # bg-emerald-50
            'status_text': '#059669',
        },
        'sky': {
            'gradient_start': 'rgba(14, 165, 233, 0.15)',
            'gradient_end': 'rgba(14, 165, 233, 0.08)',
            'border': '#bae6fd',                             # border-sky-200
            'text': '#0284c7',                               # text-sky-600
            'bg': '#f0f9ff',                                 # bg-sky-50
            'status_text': '#0284c7',
        },
        'pink': {
            'gradient_start': 'rgba(236, 72, 153, 0.15)',
            'gradient_end': 'rgba(236, 72, 153, 0.08)',
            'border': '#fbcfe8',                             # border-pink-200
            'text': '#db2777',                               # text-pink-600
            'bg': '#fdf2f8',                                 # bg-pink-50
            'status_text': '#db2777',
        },
        'rose': {
            'gradient_start': 'rgba(244, 63, 94, 0.15)',
            'gradient_end': 'rgba(244, 63, 94, 0.08)',
            'border': '#fecdd3',                             # border-rose-200
            'text': '#e11d48',                               # text-rose-600
            'bg': '#fff1f2',                                 # bg-rose-50
            'status_text': '#e11d48',
        },
        'fuchsia': {
            'gradient_start': 'rgba(217, 70, 239, 0.15)',
            'gradient_end': 'rgba(217, 70, 239, 0.08)',
            'border': '#f5d0fe',                             # border-fuchsia-200
            'text': '#c026d3',                               # text-fuchsia-600
            'bg': '#fdf4ff',                                 # bg-fuchsia-50
            'status_text': '#c026d3',
        },
        'lime': {
            'gradient_start': 'rgba(132, 204, 22, 0.15)',
            'gradient_end': 'rgba(132, 204, 22, 0.08)',
            'border': '#d9f99d',                             # border-lime-200
            'text': '#65a30d',                               # text-lime-600
            'bg': '#f7fee7',                                 # bg-lime-50
            'status_text': '#65a30d',
        },
        'slate': {
            'gradient_start': 'rgba(100, 116, 139, 0.15)',
            'gradient_end': 'rgba(100, 116, 139, 0.08)',
            'border': '#e2e8f0',                             # border-slate-200
            'text': '#475569',                               # text-slate-600
            'bg': '#f8fafc',                                 # bg-slate-50
            'status_text': '#475569',
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
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 13px;
            line-height: 1.4;
            color: #1f2937;
            background: white;
        }

        @page {
            size: A4;
            margin: 1cm 1.2cm;
        }

        .report-container {
            max-width: 100%;
            margin: 0 auto;
            padding: 0;
        }

        .grid-row {
            display: grid;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
            align-items: stretch;
            break-inside: avoid;
            page-break-inside: avoid;
        }

        .grid-single { grid-template-columns: 1fr; }
        .grid-double { grid-template-columns: repeat(2, 1fr); }
        .grid-triple { grid-template-columns: repeat(3, 1fr); }
        .grid-quad { grid-template-columns: repeat(4, 1fr); }

        .metric-widget {
            padding: 0.6rem 0.75rem;
            border-radius: 0.5rem;
            border: 1px solid;
            overflow: hidden;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        .metric-widget .label {
            font-size: 0.7rem;
            color: #6b7280;
            margin: 0 0 0.2rem 0;
            line-height: 1.3;
        }

        .metric-widget .value {
            font-size: 1.5rem;
            font-weight: 700;
            line-height: 1.1;
            margin: 0;
        }

        .metric-widget .growth {
            font-size: 0.65rem;
            margin: 0.2rem 0 0 0;
            line-height: 1.3;
        }

        .metric-widget .status {
            font-size: 0.65rem;
            margin: 0.15rem 0 0 0;
            font-weight: 500;
            line-height: 1.3;
        }

        .metric-widget .subtitle {
            font-size: 0.6rem;
            color: #6b7280;
            margin: 0.15rem 0 0 0;
            line-height: 1.3;
        }

        .chart-widget {
            padding: 1rem;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            background: white;
            break-inside: avoid;
            page-break-inside: avoid;
        }

        .chart-title {
            font-size: 0.9rem;
            font-weight: 600;
            color: #111827;
            margin-bottom: 0.75rem;
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
        <div style="display: flex; align-items: center; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.6rem; margin-bottom: 0.75rem;">
            {logo_html}
            <div>
                <h2 style="font-size: 1.1rem; font-weight: 700; color: #111827; margin: 0;">{domain_name}</h2>
                <p style="font-size: 0.75rem; color: #6b7280; margin: 0.15rem 0 0 0;">{template_name}</p>
                <p style="font-size: 0.75rem; color: #6b7280; margin: 0.15rem 0 0 0;">Report Period: {date_range}</p>
            </div>
        </div>
"""

    def _generate_grid_row(self, row: Dict, widget_data: Dict[str, Any]) -> str:
        """Generate a grid row with widgets"""
        grid_type = row.get('type', 'single')
        slots = row.get('slots', [])

        html_parts = [f'<div class="grid-row grid-{grid_type}" style="break-inside: avoid; page-break-inside: avoid;">']

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
            elif widget_type == 'text':
                html_parts.append(self._generate_text_widget(widget_id, data))

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

        # Growth indicator
        growth_html = ''
        if growth is not None and growth != 0:
            try:
                growth_val = float(growth)
                arrow = '↗' if growth_val > 0 else '↘'
                growth_color = '#16a34a' if growth_val > 0 else '#dc2626'
                growth_text = f"{'+' if growth_val > 0 else ''}{growth_val:.1f}%"
                growth_html = f'<p class="growth"><span style="color: {growth_color};">{arrow} {growth_text}</span> <span style="color: #6b7280;">from last month</span></p>'
            except (ValueError, TypeError):
                pass

        # Status text (only show if no growth)
        status_html = ''
        status_text = self._get_status_text(widget_id, data)
        if status_text and not growth_html:
            status_color = colors.get('status_text', colors['text'])
            status_html = f'<p class="status" style="color: {status_color};">↗ {status_text}</p>'

        # Subtitle
        subtitle_html = ''
        if subtitle:
            display_subtitle = subtitle if len(str(subtitle)) <= 30 else str(subtitle)[:27] + '...'
            subtitle_html = f'<p class="subtitle">{display_subtitle}</p>'

        return f'''
        <div class="metric-widget" style="
            background: linear-gradient(to bottom right, {colors['gradient_start']}, {colors['gradient_end']});
            border-color: {colors['border']};
        ">
            <p class="label">{label}</p>
            <p class="value" style="color: {colors['text']};">{formatted_value}</p>
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

    def _generate_text_widget(self, widget_id: str, data: Dict[str, Any]) -> str:
        """Generate a text/summary widget"""
        label = data.get('label', 'Summary')
        value = data.get('value', '')

        if not value:
            return f'''
            <div style="padding: 1rem; border: 1px solid #e5e7eb; border-radius: 0.5rem; background: white;">
                <h3 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem; color: #111827;">{label}</h3>
                <p style="font-size: 0.8rem; color: #6b7280;">No summary data available</p>
            </div>
            '''

        # Split into paragraphs if there are multiple sentences
        paragraphs = value.split('. ')
        paragraphs_html = ''
        for i, p in enumerate(paragraphs):
            text = p.strip()
            if not text:
                continue
            if not text.endswith('.'):
                text += '.'
            paragraphs_html += f'<p style="font-size: 0.8rem; color: #374151; margin: 0 0 0.5rem 0; line-height: 1.5;">{text}</p>'

        return f'''
        <div style="padding: 1rem; border: 1px solid #e5e7eb; border-radius: 0.5rem; background: white;">
            <h3 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 0.75rem; color: #111827;">{label}</h3>
            {paragraphs_html}
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

        # Exact matches for specific widget types (matching ReportBuilder.tsx)
        color_mapping = {
            # Blue family
            'mentions': 'blue',
            'ranking': 'blue',
            'trends': 'blue',

            # Green family
            'sentiment': 'green',
            'growth': 'green',
            'revenue': 'green',
            'authority': 'green',
            'actions': 'green',
            'answer': 'green',
            'health': 'green',

            # Purple family
            'competitors': 'purple',
            'traffic': 'purple',
            'performance': 'purple',
            'gaps': 'purple',

            # Orange family
            'share': 'orange',
            'voice': 'orange',
            'referral': 'orange',
            'opportunities': 'orange',

            # Indigo family
            'prompts': 'indigo',
            'accuracy': 'indigo',
            'conversion': 'indigo',
            'recommendations': 'indigo',

            # Cyan family
            'citations': 'cyan',
            'consistency': 'cyan',

            # Emerald family
            'sources': 'emerald',
            'engagement': 'emerald',
            'freshness': 'emerald',

            # Amber family
            'response': 'amber',

            # Violet family
            'position': 'violet',

            # Sky family
            'platforms': 'sky',

            # Teal family
            'topics': 'teal',

            # Pink family
            'coverage': 'pink',

            # Fuchsia family
            'score': 'fuchsia',

            # Rose family
            'alerts': 'rose',

            # Lime family
            'reach': 'lime',

            # Slate family
            'quality': 'slate',

            # Red family
            'critical': 'red',
            'issue': 'red',
            'error': 'red',
            'misinformation': 'red',

            # Yellow family
            'broken': 'yellow',
            'warning': 'yellow',
        }

        # Check for keyword matches
        for keyword, color in color_mapping.items():
            if keyword in widget_id_lower:
                return color

        # Default to blue
        return 'blue'
    
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
