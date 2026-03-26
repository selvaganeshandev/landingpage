"""
SVG Chart Generator for PDF Reports
Creates professional charts matching Recharts design
"""
from typing import List, Dict, Any
import math


class SVGChartGenerator:
    """Generate SVG charts that match frontend Recharts design"""

    # Chart dimensions
    WIDTH = 600
    HEIGHT = 300
    MARGIN = {'top': 20, 'right': 30, 'bottom': 40, 'left': 50}

    # Colors matching frontend
    COLORS = {
        'grid': '#e5e7eb',
        'axis': '#6b7280',
        'line': '#3b82f6',
        'bar': '#8b5cf6',
        'text': '#374151',
        'pie_colors': ['#10b981', '#f97316', '#3b82f6', '#8b5cf6', '#6366f1', '#ec4899']
    }

    def __init__(self):
        self.chart_width = self.WIDTH - self.MARGIN['left'] - self.MARGIN['right']
        self.chart_height = self.HEIGHT - self.MARGIN['top'] - self.MARGIN['bottom']

    def generate_line_chart(self, data: List[Dict], x_key: str = 'date', y_key: str = 'value', color: str = None) -> str:
        """
        Generate SVG line chart matching Recharts design

        Args:
            data: List of data points [{date: '...', value: ...}, ...]
            x_key: Key for x-axis data
            y_key: Key for y-axis data
            color: Line color (default: blue)

        Returns:
            SVG string
        """
        if not data:
            return self._generate_no_data_svg("No chart data available")

        color = color or self.COLORS['line']
        grid_color = self.COLORS['grid']
        axis_color = self.COLORS['axis']
        text_color = self.COLORS['text']
        margin_left = self.MARGIN['left']
        margin_top = self.MARGIN['top']

        # Smart key detection for labels
        def get_label(item):
            for key in [x_key, 'date', 'month', 'day', 'time', 'label']:
                if key in item:
                    return str(item[key])[:10]
            return 'Point'

        def get_value(item):
            for key in [y_key, 'value', 'count', 'score', 'mentions']:
                if key in item and item[key] is not None:
                    try:
                        return float(item[key])
                    except (ValueError, TypeError):
                        pass
            return 0

        # Extract values with smart key detection
        # For time series data, intelligently sample across the entire range
        max_points = 15  # Show up to 15 points for better readability

        if len(data) <= max_points:
            # Use all data if we have few points
            sampled_data = data
        else:
            # Sample evenly across the range to show the full picture
            step = len(data) / max_points
            indices = [int(i * step) for i in range(max_points)]
            sampled_data = [data[i] for i in indices]

        x_labels = [get_label(item) for item in sampled_data]
        y_values = [get_value(item) for item in sampled_data]

        # Calculate scales
        max_y = max(y_values) if y_values else 1
        min_y = min(y_values) if y_values else 0
        y_range = max_y - min_y if max_y != min_y else max_y

        # Add padding to y-axis
        y_padding = y_range * 0.1
        y_min = max(0, min_y - y_padding)
        y_max = max_y + y_padding
        y_range = y_max - y_min if y_max != y_min else y_max

        # Generate SVG
        svg_parts = [
            f'<svg width="{self.WIDTH}" height="{self.HEIGHT}" xmlns="http://www.w3.org/2000/svg">',
            # Background
            f'<rect width="{self.WIDTH}" height="{self.HEIGHT}" fill="white"/>',
            # Chart group
            f'<g transform="translate({margin_left}, {margin_top})">',
        ]

        # Grid lines (horizontal)
        grid_lines = 5
        for i in range(grid_lines + 1):
            y = self.chart_height * i / grid_lines
            svg_parts.append(
                f'<line x1="0" y1="{y}" x2="{self.chart_width}" y2="{y}" '
                f'stroke="{grid_color}" stroke-width="1" stroke-dasharray="3,3"/>'
            )

        # Y-axis
        svg_parts.append(
            f'<line x1="0" y1="0" x2="0" y2="{self.chart_height}" '
            f'stroke="{axis_color}" stroke-width="1"/>'
        )

        # X-axis
        svg_parts.append(
            f'<line x1="0" y1="{self.chart_height}" x2="{self.chart_width}" y2="{self.chart_height}" '
            f'stroke="{axis_color}" stroke-width="1"/>'
        )

        # Y-axis labels
        for i in range(grid_lines + 1):
            y = self.chart_height * (1 - i / grid_lines)
            value = y_min + (y_range * i / grid_lines)
            svg_parts.append(
                f'<text x="-10" y="{y + 4}" text-anchor="end" font-size="11" fill="{text_color}">'
                f'{value:.0f}</text>'
            )

        # Plot line
        if len(y_values) > 1:
            points = []
            for i, value in enumerate(y_values):
                x = (i / (len(y_values) - 1)) * self.chart_width
                y = self.chart_height - ((value - y_min) / y_range * self.chart_height) if y_range > 0 else self.chart_height / 2
                points.append(f"{x},{y}")

            # Line path
            path = f'M {" L ".join(points)}'
            svg_parts.append(
                f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>'
            )

            # Data points with value labels
            for i, value in enumerate(y_values):
                x = (i / (len(y_values) - 1)) * self.chart_width
                y = self.chart_height - ((value - y_min) / y_range * self.chart_height) if y_range > 0 else self.chart_height / 2

                # Circle
                svg_parts.append(
                    f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>'
                )

                # Value label (only for non-zero values or max values)
                if value > 0 or value == max(y_values):
                    label_y = y - 10 if y > 30 else y + 18  # Position above or below point
                    svg_parts.append(
                        f'<text x="{x}" y="{label_y}" text-anchor="middle" font-size="10" '
                        f'font-weight="600" fill="{text_color}">{value:.0f}</text>'
                    )

        # X-axis labels — skip labels to avoid overlap, rotate if many
        total = len(x_labels)
        step = max(1, total // 8)  # Show at most ~8 labels
        rotate = total > 6
        for i, label in enumerate(x_labels):
            if i % step != 0 and i != total - 1:
                continue
            if total > 1:
                x = (i / (total - 1)) * self.chart_width
            else:
                x = self.chart_width / 2
            short_label = label[-5:] if len(label) > 5 else label  # e.g. "03-24" from "2026-03-24"
            if rotate:
                svg_parts.append(
                    f'<text x="{x}" y="{self.chart_height + 18}" text-anchor="end" font-size="9" fill="{text_color}" '
                    f'transform="rotate(-45, {x}, {self.chart_height + 18})">{short_label}</text>'
                )
            else:
                svg_parts.append(
                    f'<text x="{x}" y="{self.chart_height + 20}" text-anchor="middle" font-size="10" fill="{text_color}">'
                    f'{short_label}</text>'
                )

        svg_parts.extend(['</g>', '</svg>'])

        return '\n'.join(svg_parts)

    def generate_bar_chart(self, data: List[Dict], x_key: str = 'name', y_key: str = 'value', color: str = None) -> str:
        """
        Generate SVG bar chart matching Recharts design

        Args:
            data: List of data points [{name: '...', value: ...}, ...]
            x_key: Key for x-axis labels
            y_key: Key for bar values
            color: Bar color (default: purple)

        Returns:
            SVG string
        """
        if not data:
            return self._generate_no_data_svg("No chart data available")

        color = color or self.COLORS['bar']
        grid_color = self.COLORS['grid']
        axis_color = self.COLORS['axis']
        text_color = self.COLORS['text']
        margin_left = self.MARGIN['left']
        margin_top = self.MARGIN['top']

        # Smart key detection - try multiple common key names
        def get_label(item):
            for key in [x_key, 'name', 'platform', 'category', 'label']:
                if key in item:
                    return str(item[key])[:15]
            return 'Item'

        def get_value(item):
            for key in [y_key, 'value', 'count', 'mentions']:
                if key in item and item[key] is not None:
                    try:
                        return float(item[key])
                    except (ValueError, TypeError):
                        pass
            return 0

        # Extract values with smart key detection
        # For bar charts, limit to reasonable number for readability
        max_bars = 12  # Show up to 12 bars

        if len(data) <= max_bars:
            # Use all data if we have few items
            sampled_data = data
        else:
            # Take first max_bars items (bar charts typically show top N)
            sampled_data = data[:max_bars]

        labels = [get_label(item) for item in sampled_data]
        values = [get_value(item) for item in sampled_data]

        # Calculate scales
        max_value = max(values) if values else 1
        y_padding = max_value * 0.1
        y_max = max_value + y_padding

        # Generate SVG
        svg_parts = [
            f'<svg width="{self.WIDTH}" height="{self.HEIGHT}" xmlns="http://www.w3.org/2000/svg">',
            f'<rect width="{self.WIDTH}" height="{self.HEIGHT}" fill="white"/>',
            f'<g transform="translate({margin_left}, {margin_top})">',
        ]

        # Grid lines
        grid_lines = 5
        for i in range(grid_lines + 1):
            y = self.chart_height * i / grid_lines
            svg_parts.append(
                f'<line x1="0" y1="{y}" x2="{self.chart_width}" y2="{y}" '
                f'stroke="{grid_color}" stroke-width="1" stroke-dasharray="3,3"/>'
            )

        # Axes
        svg_parts.append(
            f'<line x1="0" y1="0" x2="0" y2="{self.chart_height}" '
            f'stroke="{axis_color}" stroke-width="1"/>'
        )
        svg_parts.append(
            f'<line x1="0" y1="{self.chart_height}" x2="{self.chart_width}" y2="{self.chart_height}" '
            f'stroke="{axis_color}" stroke-width="1"/>'
        )

        # Y-axis labels
        for i in range(grid_lines + 1):
            y = self.chart_height * (1 - i / grid_lines)
            value = (y_max * i / grid_lines)
            svg_parts.append(
                f'<text x="-10" y="{y + 4}" text-anchor="end" font-size="11" fill="{text_color}">'
                f'{value:.0f}</text>'
            )

        # Bars
        bar_width = (self.chart_width / len(values)) * 0.7
        bar_spacing = self.chart_width / len(values)

        for i, value in enumerate(values):
            x = i * bar_spacing + (bar_spacing - bar_width) / 2
            bar_height = (value / y_max * self.chart_height) if y_max > 0 else 0
            y = self.chart_height - bar_height

            # Bar with gradient
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" '
                f'fill="{color}" opacity="0.8" rx="4"/>'
            )

            # Value label on top
            svg_parts.append(
                f'<text x="{x + bar_width/2}" y="{y - 5}" text-anchor="middle" font-size="10" '
                f'fill="{text_color}" font-weight="bold">{value:.0f}</text>'
            )

        # X-axis labels — rotate if many labels
        rotate = len(labels) > 5
        for i, label in enumerate(labels):
            x = i * bar_spacing + bar_spacing / 2
            short_label = label[:12] if len(label) > 12 else label
            if rotate:
                svg_parts.append(
                    f'<text x="{x}" y="{self.chart_height + 18}" text-anchor="end" font-size="9" fill="{text_color}" '
                    f'transform="rotate(-45, {x}, {self.chart_height + 18})">{short_label}</text>'
                )
            else:
                svg_parts.append(
                    f'<text x="{x}" y="{self.chart_height + 20}" text-anchor="middle" font-size="10" fill="{text_color}">'
                    f'{short_label}</text>'
                )

        svg_parts.extend(['</g>', '</svg>'])

        return '\n'.join(svg_parts)

    def generate_pie_chart(self, data: List[Dict], name_key: str = 'name', value_key: str = 'value') -> str:
        """
        Generate SVG pie chart matching Recharts design

        Args:
            data: List of data points [{name: '...', value: ...}, ...]
            name_key: Key for category names
            value_key: Key for values

        Returns:
            SVG string
        """
        if not data:
            return self._generate_no_data_svg("No chart data available")

        text_color = self.COLORS['text']
        axis_color = self.COLORS['axis']
        pie_colors = self.COLORS['pie_colors']

        # Smart key detection for names
        def get_name(item, index):
            for key in [name_key, 'name', 'label', 'category', 'domain', 'competitor']:
                if key in item:
                    return str(item[key])[:20]
            return f'Item {index+1}'

        def get_value(item):
            for key in [value_key, 'value', 'count', 'mentions', 'percentage']:
                if key in item and item[key] is not None:
                    try:
                        return float(item[key])
                    except (ValueError, TypeError):
                        pass
            return 0

        # Extract values with smart key detection
        items = []
        for i, item in enumerate(data[:6]):
            name = get_name(item, i)
            value = get_value(item)
            item_color = pie_colors[i % len(pie_colors)]
            items.append({'name': name, 'value': value, 'color': item_color})

        total = sum([item['value'] for item in items])
        if total == 0:
            return self._generate_no_data_svg("No chart data available")

        # Generate SVG
        svg_parts = [
            f'<svg width="{self.WIDTH}" height="{self.HEIGHT}" xmlns="http://www.w3.org/2000/svg">',
            f'<rect width="{self.WIDTH}" height="{self.HEIGHT}" fill="white"/>',
        ]

        # Pie chart center
        cx = 200
        cy = self.HEIGHT / 2
        radius = 80

        # Draw pie slices
        start_angle = 0
        for item in items:
            angle = (item['value'] / total) * 360
            end_angle = start_angle + angle

            # Calculate slice path
            start_rad = math.radians(start_angle - 90)
            end_rad = math.radians(end_angle - 90)

            x1 = cx + radius * math.cos(start_rad)
            y1 = cy + radius * math.sin(start_rad)
            x2 = cx + radius * math.cos(end_rad)
            y2 = cy + radius * math.sin(end_rad)

            large_arc = 1 if angle > 180 else 0

            path = f'M {cx},{cy} L {x1},{y1} A {radius},{radius} 0 {large_arc},1 {x2},{y2} Z'
            item_color = item['color']

            svg_parts.append(
                f'<path d="{path}" fill="{item_color}" stroke="white" stroke-width="2"/>'
            )

            # Label
            mid_angle = start_angle + angle / 2
            mid_rad = math.radians(mid_angle - 90)
            label_radius = radius * 0.7
            label_x = cx + label_radius * math.cos(mid_rad)
            label_y = cy + label_radius * math.sin(mid_rad)

            percentage = (item['value'] / total * 100)
            if percentage > 5:  # Only show label if slice is big enough
                svg_parts.append(
                    f'<text x="{label_x}" y="{label_y}" text-anchor="middle" font-size="12" '
                    f'fill="white" font-weight="bold">{percentage:.0f}%</text>'
                )

            start_angle = end_angle

        # Legend
        legend_x = 400
        legend_y = 50

        for i, item in enumerate(items):
            y = legend_y + i * 30
            percentage = (item['value'] / total * 100)
            item_color = item['color']
            item_name = item['name'][:20]
            item_value = item['value']

            # Color box
            svg_parts.append(
                f'<rect x="{legend_x}" y="{y - 10}" width="15" height="15" fill="{item_color}" rx="2"/>'
            )

            # Name
            svg_parts.append(
                f'<text x="{legend_x + 25}" y="{y}" font-size="12" fill="{text_color}">'
                f'{item_name}</text>'
            )

            # Percentage and value
            svg_parts.append(
                f'<text x="{legend_x + 25}" y="{y + 12}" font-size="10" fill="{axis_color}">'
                f'{percentage:.1f}% ({item_value:.0f})</text>'
            )

        svg_parts.append('</svg>')

        return '\n'.join(svg_parts)

    def _generate_no_data_svg(self, message: str) -> str:
        """Generate SVG with no data message"""
        return f'''
        <svg width="{self.WIDTH}" height="{self.HEIGHT}" xmlns="http://www.w3.org/2000/svg">
            <rect width="{self.WIDTH}" height="{self.HEIGHT}" fill="#f9fafb"/>
            <text x="{self.WIDTH/2}" y="{self.HEIGHT/2}" text-anchor="middle"
                  font-size="14" fill="#6b7280">{message}</text>
        </svg>
        '''
