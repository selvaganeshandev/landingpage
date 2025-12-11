"""
HTML Template Renderer with Placeholder System
Injects real widget data into saved HTML templates for PDF generation
"""
import re
from typing import Dict, Any


class HTMLTemplateRenderer:
    """Renders HTML templates by replacing placeholders with real data"""

    def __init__(self, html_template: str, css_template: str = ""):
        """
        Initialize renderer with saved template

        Args:
            html_template: HTML with placeholders like {{widget-id.value}}
            css_template: CSS styles (Tailwind CSS)
        """
        self.html_template = html_template
        self.css_template = css_template

    def render(self, widget_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """
        Render complete HTML document with real data

        Args:
            widget_data: Dictionary mapping widget IDs to their data
                Example: {
                    'total-prompts-metric': {
                        'type': 'metric',
                        'value': 1234,
                        'label': 'Total Prompts',
                        'growth': 12.5
                    }
                }
            metadata: Template metadata (domain name, date range, etc.)

        Returns:
            Complete HTML document ready for PDF conversion
        """
        html = self.html_template

        # Replace widget data placeholders
        html = self._replace_widget_placeholders(html, widget_data)

        # Replace metadata placeholders
        if metadata:
            html = self._replace_metadata_placeholders(html, metadata)

        # Build complete HTML document
        full_html = self._build_complete_html(html)

        return full_html

    def _replace_widget_placeholders(self, html: str, widget_data: Dict[str, Any]) -> str:
        """
        Replace all widget placeholders in HTML

        Placeholder format: {{widget-id.property}}
        Example: {{total-prompts-metric.value}} → 1234
        """
        for widget_id, data in widget_data.items():
            if not data:
                continue

            # Replace value
            value = data.get('value', '')
            html = html.replace(f'{{{{{widget_id}.value}}}}', self._format_value(value, data))

            # Replace label
            label = data.get('label', '')
            html = html.replace(f'{{{{{widget_id}.label}}}}', str(label))

            # Replace growth
            growth = data.get('growth', '')
            if growth:
                try:
                    growth_val = float(growth)
                    growth_formatted = f"{'+' if growth_val > 0 else ''}{growth_val:.1f}%"
                    html = html.replace(f'{{{{{widget_id}.growth}}}}', growth_formatted)

                    # Replace growth indicator (▲ or ▼)
                    indicator = '▲' if growth_val > 0 else '▼'
                    html = html.replace(f'{{{{{widget_id}.indicator}}}}', indicator)

                    # Replace growth color class with inline style
                    color_style = 'color: #16a34a;' if growth_val > 0 else 'color: #dc2626;'  # green-600 or red-600
                    html = html.replace(f'{{{{{widget_id}.growth_color}}}}', f'style="{color_style}"')
                except (ValueError, TypeError):
                    html = html.replace(f'{{{{{widget_id}.growth}}}}', '')
                    html = html.replace(f'{{{{{widget_id}.indicator}}}}', '')
                    html = html.replace(f'{{{{{widget_id}.growth_color}}}}', 'text-gray-600')

            # Replace subtitle
            subtitle = data.get('subtitle', '')
            html = html.replace(f'{{{{{widget_id}.subtitle}}}}', str(subtitle))

            # Replace chart SVG or table HTML
            if data.get('type') == 'chart':
                chart_html = self._render_chart_placeholder(data)
                html = html.replace(f'{{{{{widget_id}.chart}}}}', chart_html)
            elif data.get('type') == 'table':
                table_html = self._render_table_placeholder(data)
                html = html.replace(f'{{{{{widget_id}.table}}}}', table_html)

        # Clean up any remaining placeholders (replace with empty string)
        html = re.sub(r'\{\{[^}]+\}\}', '', html)

        return html

    def _replace_metadata_placeholders(self, html: str, metadata: Dict[str, Any]) -> str:
        """Replace metadata placeholders (domain name, dates, etc.)"""
        replacements = {
            'domain_name': metadata.get('domain_name', ''),
            'domain_url': metadata.get('domain_url', ''),
            'template_name': metadata.get('template_name', ''),
            'organisation_name': metadata.get('organisation_name', ''),
        }

        # Handle date period
        period = metadata.get('period', {})
        if period:
            start_date = period.get('start', '')
            end_date = period.get('end', '')
            if start_date and end_date:
                replacements['date_range'] = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
                replacements['start_date'] = start_date.strftime('%B %d, %Y')
                replacements['end_date'] = end_date.strftime('%B %d, %Y')

        for key, value in replacements.items():
            html = html.replace(f'{{{{{key}}}}}', str(value))

        return html

    def _format_value(self, value: Any, data: Dict[str, Any]) -> str:
        """Format value based on format type"""
        format_type = data.get('format', 'number')

        try:
            if format_type == 'percentage':
                return f"{float(value):.1f}%"
            elif format_type == 'decimal':
                return f"{float(value):.2f}"
            elif format_type == 'ordinal':
                return f"#{int(value)}"
            elif isinstance(value, (int, float)):
                return f"{int(value):,}"
            else:
                return str(value)
        except (ValueError, TypeError):
            return str(value)

    def _render_chart_placeholder(self, data: Dict[str, Any]) -> str:
        """
        Render chart data as HTML/SVG
        Note: Charts should be pre-rendered as SVG by frontend
        """
        svg = data.get('svg', '')
        if svg:
            return svg

        # Fallback: render basic chart info
        chart_type = data.get('chart_type', 'chart')
        label = data.get('label', 'Chart')
        return f'<div class="chart-placeholder">{label} ({chart_type})</div>'

    def _render_table_placeholder(self, data: Dict[str, Any]) -> str:
        """Render table data as HTML"""
        columns = data.get('columns', [])
        rows = data.get('rows', [])

        if not columns or not rows:
            return '<div class="table-placeholder">No data</div>'

        # Build HTML table
        html = '<table class="w-full border-collapse">'

        # Header
        html += '<thead><tr class="bg-gray-100">'
        for col in columns:
            html += f'<th class="border border-gray-300 px-4 py-2 text-left font-semibold">{col}</th>'
        html += '</tr></thead>'

        # Rows
        html += '<tbody>'
        for i, row in enumerate(rows):
            bg_class = 'bg-white' if i % 2 == 0 else 'bg-gray-50'
            html += f'<tr class="{bg_class}">'
            for cell in row:
                html += f'<td class="border border-gray-300 px-4 py-2">{cell}</td>'
            html += '</tr>'
        html += '</tbody>'

        html += '</table>'
        return html

    def _build_complete_html(self, body_html: str) -> str:
        """Build complete HTML document with CSS"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report</title>
    <style>
        /* Reset and base styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            font-size: 14px;
            line-height: 1.5;
            color: #1f2937;
            background: white;
        }}

        /* Tailwind-like utilities */
        .text-sm {{ font-size: 0.875rem; }}
        .text-base {{ font-size: 1rem; }}
        .text-lg {{ font-size: 1.125rem; }}
        .text-xl {{ font-size: 1.25rem; }}
        .text-2xl {{ font-size: 1.5rem; }}
        .text-3xl {{ font-size: 1.875rem; }}
        .text-4xl {{ font-size: 2.25rem; }}
        .text-5xl {{ font-size: 3rem; }}

        .font-normal {{ font-weight: 400; }}
        .font-medium {{ font-weight: 500; }}
        .font-semibold {{ font-weight: 600; }}
        .font-bold {{ font-weight: 700; }}

        .text-gray-500 {{ color: #6b7280; }}
        .text-gray-600 {{ color: #4b5563; }}
        .text-gray-700 {{ color: #374151; }}
        .text-gray-900 {{ color: #111827; }}
        .text-blue-600 {{ color: #2563eb; }}
        .text-green-600 {{ color: #16a34a; }}
        .text-red-600 {{ color: #dc2626; }}
        .text-purple-600 {{ color: #9333ea; }}
        .text-orange-600 {{ color: #ea580c; }}
        .text-indigo-600 {{ color: #4f46e5; }}

        .bg-white {{ background-color: white; }}
        .bg-gray-50 {{ background-color: #f9fafb; }}
        .bg-gray-100 {{ background-color: #f3f4f6; }}
        .bg-blue-50 {{ background-color: #eff6ff; }}
        .bg-green-50 {{ background-color: #f0fdf4; }}
        .bg-purple-50 {{ background-color: #faf5ff; }}
        .bg-orange-50 {{ background-color: #fff7ed; }}
        .bg-indigo-50 {{ background-color: #eef2ff; }}

        .border {{ border-width: 1px; }}
        .border-gray-200 {{ border-color: #e5e7eb; }}
        .border-gray-300 {{ border-color: #d1d5db; }}
        .border-blue-200 {{ border-color: #bfdbfe; }}
        .border-green-200 {{ border-color: #bbf7d0; }}
        .border-purple-200 {{ border-color: #e9d5ff; }}
        .border-orange-200 {{ border-color: #fed7aa; }}

        .rounded {{ border-radius: 0.25rem; }}
        .rounded-lg {{ border-radius: 0.5rem; }}
        .rounded-xl {{ border-radius: 0.75rem; }}

        .p-4 {{ padding: 1rem; }}
        .p-6 {{ padding: 1.5rem; }}
        .px-4 {{ padding-left: 1rem; padding-right: 1rem; }}
        .py-2 {{ padding-top: 0.5rem; padding-bottom: 0.5rem; }}

        .mb-2 {{ margin-bottom: 0.5rem; }}
        .mt-2 {{ margin-top: 0.5rem; }}
        .mb-4 {{ margin-bottom: 1rem; }}
        .mt-4 {{ margin-top: 1rem; }}

        .flex {{ display: flex; }}
        .items-center {{ align-items: center; }}
        .gap-1 {{ gap: 0.25rem; }}
        .gap-2 {{ gap: 0.5rem; }}

        .w-full {{ width: 100%; }}

        /* Gradient backgrounds (simulated with solid colors for PDF) */
        .bg-gradient-to-br {{
            background: linear-gradient(to bottom right, var(--tw-gradient-from), var(--tw-gradient-to));
        }}

        /* Custom styles from saved template */
        {self.css_template}

        /* Print-specific styles */
        @media print {{
            body {{
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
    {body_html}
</body>
</html>"""


def inject_widget_data(html_template: str, css_template: str, widget_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
    """
    Convenience function to inject widget data into HTML template

    Args:
        html_template: HTML with placeholders
        css_template: CSS styles
        widget_data: Widget data dictionary
        metadata: Template metadata

    Returns:
        Complete HTML document
    """
    renderer = HTMLTemplateRenderer(html_template, css_template)
    return renderer.render(widget_data, metadata)
