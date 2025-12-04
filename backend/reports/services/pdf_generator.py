"""
PDF Report Generator using ReportLab
Modern, professional design with proper spacing and visual hierarchy
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image, KeepTogether, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
import os


class PDFReportGenerator:
    """Generate PDF reports using ReportLab"""

    # Modern color palette
    COLORS = {
        'primary': colors.HexColor('#6366f1'),      # Indigo
        'primary_light': colors.HexColor('#eef2ff'),
        'success': colors.HexColor('#10b981'),      # Green
        'success_light': colors.HexColor('#ecfdf5'),
        'warning': colors.HexColor('#f59e0b'),      # Amber
        'warning_light': colors.HexColor('#fffbeb'),
        'danger': colors.HexColor('#ef4444'),       # Red
        'danger_light': colors.HexColor('#fef2f2'),
        'info': colors.HexColor('#3b82f6'),         # Blue
        'info_light': colors.HexColor('#eff6ff'),
        'purple': colors.HexColor('#8b5cf6'),
        'purple_light': colors.HexColor('#f5f3ff'),
        'dark': colors.HexColor('#1f2937'),
        'gray': colors.HexColor('#6b7280'),
        'light_gray': colors.HexColor('#f3f4f6'),
        'border': colors.HexColor('#e5e7eb'),
        'white': colors.white,
    }

    def __init__(self, report_data, report_type):
        self.data = report_data
        self.report_type = report_type
        self.buffer = BytesIO()
        self.page_width = letter[0]
        self.page_height = letter[1]
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=0.6*inch,
            leftMargin=0.6*inch,
            topMargin=0.6*inch,
            bottomMargin=0.75*inch,
        )
        self.styles = getSampleStyleSheet()
        self.story = []
        self.page_number = 0

        # Calculate usable width
        self.usable_width = self.page_width - 1.2*inch

        self._setup_styles()

    def _setup_styles(self):
        """Setup custom paragraph styles"""
        # Report Title
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=self.COLORS['dark'],
            spaceAfter=6,
            spaceBefore=0,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
        ))

        # Report Subtitle
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.COLORS['gray'],
            spaceAfter=20,
            alignment=TA_LEFT,
        ))

        # Section Heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.COLORS['dark'],
            spaceAfter=12,
            spaceBefore=24,
            fontName='Helvetica-Bold',
        ))

        # Subsection Heading
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=self.COLORS['dark'],
            spaceAfter=8,
            spaceBefore=16,
            fontName='Helvetica-Bold',
        ))

        # Body Text - CustomBody to avoid conflict with default BodyText
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLORS['gray'],
            spaceAfter=8,
            leading=14,
        ))

        # Small Text
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.COLORS['gray'],
            spaceAfter=4,
        ))

        # Metric Value (large number)
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=32,
            textColor=self.COLORS['dark'],
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
        ))

        # Metric Label
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLORS['gray'],
            spaceAfter=4,
        ))

    def _add_footer(self, canvas, doc):
        """Add footer with page number and branding"""
        canvas.saveState()
        # Footer line
        canvas.setStrokeColor(self.COLORS['border'])
        canvas.setLineWidth(0.5)
        canvas.line(0.6*inch, 0.6*inch, self.page_width - 0.6*inch, 0.6*inch)

        # Footer text
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.COLORS['gray'])
        canvas.drawString(0.6*inch, 0.4*inch, f"AI Visibility Monitor - {self.report_type}")
        canvas.drawRightString(self.page_width - 0.6*inch, 0.4*inch, f"Page {doc.page}")
        canvas.restoreState()

    def generate(self):
        """Generate the PDF and return BytesIO buffer"""
        # Add title header
        self._add_header()

        # Add content based on report type
        if self.report_type == 'Executive Dashboard':
            self._generate_executive_dashboard()
        elif self.report_type == 'Detailed Analytics':
            self._generate_detailed_analytics()
        elif self.report_type == 'Competitor Focus':
            self._generate_competitor_focus()
        elif self.report_type == 'Content Strategy':
            self._generate_content_strategy()

        # Build PDF with footer
        self.doc.build(self.story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
        self.buffer.seek(0)
        return self.buffer

    def _add_header(self):
        """Add modern report header with prominent domain name and favicon"""
        domain_name = self.data.get('domain_name', 'N/A')
        domain_url = self.data.get('domain_url', '')
        period_start = self.data['period']['start'].strftime('%B %d, %Y')
        period_end = self.data['period']['end'].strftime('%B %d, %Y')

        # Try to get favicon
        favicon_img = None
        if domain_url:
            try:
                import urllib.request
                # Get domain from URL
                from urllib.parse import urlparse
                parsed = urlparse(domain_url)
                domain_host = parsed.netloc or domain_url.replace('https://', '').replace('http://', '').split('/')[0]
                favicon_url = f"https://www.google.com/s2/favicons?domain={domain_host}&sz=64"

                # Download favicon to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                    urllib.request.urlretrieve(favicon_url, tmp.name)
                    favicon_img = Image(tmp.name, width=32, height=32)
            except Exception as e:
                favicon_img = None

        # Build header with favicon and domain name side by side
        if favicon_img:
            # Domain name style - use larger leading to match favicon height
            domain_para = Paragraph(domain_name, ParagraphStyle(
                'DomainInline',
                parent=self.styles['Normal'],
                fontSize=26,
                textColor=self.COLORS['dark'],
                fontName='Helvetica-Bold',
                leading=32,  # Match favicon height for vertical centering
            ))

            # Create a table with favicon and domain name
            header_data = [[favicon_img, domain_para]]
            header_table = Table(header_data, colWidths=[44, self.usable_width - 54], rowHeights=[36])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('LEFTPADDING', (0, 0), (0, 0), 0),
                ('LEFTPADDING', (1, 0), (1, 0), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            self.story.append(header_table)
        else:
            # No favicon - just domain name
            domain_style = ParagraphStyle(
                'DomainName',
                parent=self.styles['Normal'],
                fontSize=26,
                textColor=self.COLORS['dark'],
                fontName='Helvetica-Bold',
            )
            self.story.append(Paragraph(domain_name, domain_style))

        self.story.append(Spacer(1, 8))

        # Report type and date on same line
        meta_text = f'''<font size="10" color="#6b7280">{self.report_type}  •  {period_start} - {period_end}</font>'''
        meta_style = ParagraphStyle(
            'MetaInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLORS['gray'],
            spaceAfter=16,
        )
        self.story.append(Paragraph(meta_text, meta_style))

        # Divider line
        self.story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=self.COLORS['border'],
            spaceBefore=0,
            spaceAfter=20
        ))

    def _create_metric_card(self, label, value, trend_text="", color_key='primary'):
        """Create a single metric card as a table"""
        bg_color = self.COLORS.get(f'{color_key}_light', self.COLORS['light_gray'])
        text_color = self.COLORS.get(color_key, self.COLORS['primary'])

        card_data = [
            [Paragraph(f'<font color="#{text_color.hexval()[2:]}">{label}</font>', self.styles['MetricLabel'])],
            [Paragraph(f'<font size="28"><b>{value}</b></font>', self.styles['CustomBody'])],
        ]
        if trend_text:
            card_data.append([Paragraph(f'<font color="#10b981" size="9">{trend_text}</font>', self.styles['SmallText'])])

        card_table = Table(card_data, colWidths=[self.usable_width/4 - 10])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return card_table

    def _generate_executive_dashboard(self):
        """Generate Executive Dashboard report with modern design"""

        metrics = self.data.get('key_metrics', {})
        domain_name = self.data.get('domain_name', 'N/A')

        # Calculate metrics
        total_prompts = metrics.get('total_prompts', 0)
        total_mentions = metrics.get('total_mentions', 0)
        mention_rate = metrics.get('mention_rate', 0)
        avg_sentiment = metrics.get('avg_sentiment', 0)
        competitor_count = metrics.get('competitor_count', 0)

        # ===== SECTION 1: Key Metrics Cards =====
        self.story.append(Paragraph('Performance Overview', self.styles['SectionHeading']))

        # Calculate trends
        visibility_trend = 'Stable' if mention_rate >= 40 else ('Growing' if mention_rate >= 20 else 'Needs attention')
        sentiment_score = int(avg_sentiment * 100) if avg_sentiment > 0 else 50
        sentiment_label = 'Positive' if avg_sentiment > 0.3 else ('Neutral' if avg_sentiment >= 0 else 'Negative')

        # Create 4 metric cards in a 2x2 grid
        card_width = (self.usable_width - 20) / 2

        # Row 1: Visibility Score and Total Mentions
        row1_data = [[
            self._create_single_metric_cell('AI Visibility Score', f'{mention_rate}%', visibility_trend, 'info'),
            self._create_single_metric_cell('Total Mentions', f'{total_mentions}', f'From {total_prompts} prompts', 'purple'),
        ]]

        row1_table = Table(row1_data, colWidths=[card_width, card_width])
        row1_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, -1), 10),
            ('RIGHTPADDING', (1, 0), (1, -1), 0),
        ]))
        self.story.append(row1_table)
        self.story.append(Spacer(1, 10))

        # Row 2: Sentiment and Competitors
        row2_data = [[
            self._create_single_metric_cell('Sentiment Score', f'{sentiment_score}%', sentiment_label, 'success'),
            self._create_single_metric_cell('Competitors Tracked', f'{competitor_count}', 'Active monitoring', 'warning'),
        ]]

        row2_table = Table(row2_data, colWidths=[card_width, card_width])
        row2_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, -1), 10),
            ('RIGHTPADDING', (1, 0), (1, -1), 0),
        ]))
        self.story.append(row2_table)

        # ===== SECTION 2: Platform Performance =====
        self.story.append(Paragraph('Platform Distribution', self.styles['SectionHeading']))

        # Use real platform data if available, otherwise use calculated distribution
        platform_breakdown = self.data.get('platform_breakdown', [])
        platform_table_data = [['Platform', 'Queries', 'Mentions', 'Mention Rate', 'Sentiment']]

        if platform_breakdown:
            for plat in platform_breakdown:
                platform_name = plat.get('platform', 'Unknown')
                if platform_name:
                    platform_name = platform_name.title()
                platform_table_data.append([
                    platform_name,
                    str(plat.get('total', 0)),
                    str(plat.get('mentions', 0)),
                    f"{plat.get('mention_rate', 0)}%",
                    f"{plat.get('avg_sentiment', 0):.2f}"
                ])
        else:
            # Fallback to calculated distribution
            platforms = ['ChatGPT', 'Claude', 'Gemini', 'Perplexity']
            for platform in platforms:
                queries = max(1, total_prompts // 4)
                mentions = max(0, total_mentions // 4)
                rate = (mentions / queries * 100) if queries > 0 else 0
                platform_table_data.append([platform, str(queries), str(mentions), f'{rate:.0f}%', f'{avg_sentiment:.2f}'])

        # Full width columns
        col_widths = [self.usable_width * 0.25, self.usable_width * 0.18, self.usable_width * 0.18, self.usable_width * 0.22, self.usable_width * 0.17]
        platform_table = Table(platform_table_data, colWidths=col_widths)
        platform_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['dark']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            # Data rows
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['white'], self.COLORS['light_gray']]),
            # Alignment
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            # Grid
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        self.story.append(platform_table)

        # ===== SECTION 2b: Sentiment Analysis =====
        sentiment_data = self.data.get('sentiment_breakdown', {})
        if sentiment_data and sentiment_data.get('total', 0) > 0:
            self.story.append(Paragraph('Sentiment Analysis', self.styles['SectionHeading']))

            # Create sentiment summary cards
            sent_card_width = (self.usable_width - 20) / 3
            sent_row_data = [[
                self._create_sentiment_card('Positive', sentiment_data.get('positive', 0), sentiment_data.get('positive_pct', 0), 'success'),
                self._create_sentiment_card('Neutral', sentiment_data.get('neutral', 0), sentiment_data.get('neutral_pct', 0), 'warning'),
                self._create_sentiment_card('Negative', sentiment_data.get('negative', 0), sentiment_data.get('negative_pct', 0), 'danger'),
            ]]
            sent_table = Table(sent_row_data, colWidths=[sent_card_width, sent_card_width, sent_card_width])
            sent_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            self.story.append(sent_table)

        # ===== SECTION 3: Top Performing Prompts =====
        self.story.append(Paragraph('Top Performing Prompts', self.styles['SectionHeading']))

        top_prompts = self.data.get('top_prompts', [])
        if top_prompts:
            prompt_data = [['#', 'Prompt', 'Type', 'Mentions']]
            for idx, prompt in enumerate(top_prompts[:5], 1):
                prompt_text = prompt.get('text', '')[:60]
                if len(prompt.get('text', '')) > 60:
                    prompt_text += '...'
                prompt_data.append([
                    str(idx),
                    prompt_text,
                    prompt.get('type', 'N/A').title(),
                    str(prompt.get('mentions', 0))
                ])

            # Full width columns
            prompt_col_widths = [self.usable_width * 0.06, self.usable_width * 0.64, self.usable_width * 0.18, self.usable_width * 0.12]
            prompt_table = Table(prompt_data, colWidths=prompt_col_widths)
            prompt_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                # Data rows
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['white'], self.COLORS['primary_light']]),
                # Alignment
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                # Grid
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            self.story.append(prompt_table)
        else:
            self.story.append(Paragraph(
                'No prompt data available for this period. Add prompts to start tracking.',
                self.styles['CustomBody']
            ))

        # ===== SECTION 4: Competitive Position =====
        self.story.append(Paragraph('Competitive Position', self.styles['SectionHeading']))

        if competitor_count > 0:
            comp_summary = f"""
            <b>Market Overview</b><br/><br/>
            You are currently tracking <b>{competitor_count}</b> competitors in your market.
            Your visibility score of <b>{mention_rate}%</b> indicates {'strong' if mention_rate > 50 else 'moderate' if mention_rate > 25 else 'developing'}
            presence across AI platforms.<br/><br/>
            <b>Key Insight:</b> {'Your mention rate is above average - focus on maintaining momentum.' if mention_rate > 50 else 'There is opportunity to improve visibility through content optimization.'}
            """
            self.story.append(Paragraph(comp_summary, self.styles['CustomBody']))
        else:
            self.story.append(Paragraph(
                'Add competitors in your dashboard to enable competitive analysis and benchmarking.',
                self.styles['CustomBody']
            ))

        # ===== SECTION 5: Strategic Recommendations =====
        self.story.append(Spacer(1, 20))
        self.story.append(Paragraph('Strategic Recommendations', self.styles['SectionHeading']))

        # Generate recommendations based on metrics
        recommendations = []

        # Visibility recommendation
        if mention_rate < 30:
            recommendations.append({
                'priority': 'High',
                'title': 'Improve AI Visibility',
                'description': f'Your current visibility of {mention_rate}% is below target. Focus on creating more AI-optimized content.',
                'color': 'danger'
            })
        elif mention_rate < 60:
            recommendations.append({
                'priority': 'Medium',
                'title': 'Optimize Visibility',
                'description': f'With {mention_rate}% visibility, target 60%+ by analyzing top-performing prompt patterns.',
                'color': 'warning'
            })
        else:
            recommendations.append({
                'priority': 'Low',
                'title': 'Maintain Excellence',
                'description': f'Your {mention_rate}% visibility is strong. Continue current strategies and expand to new topics.',
                'color': 'success'
            })

        # Sentiment recommendation
        if avg_sentiment < 0:
            recommendations.append({
                'priority': 'High',
                'title': 'Address Negative Sentiment',
                'description': 'Negative sentiment detected. Review content accuracy and address potential misinformation.',
                'color': 'danger'
            })
        elif avg_sentiment < 0.3:
            recommendations.append({
                'priority': 'Medium',
                'title': 'Enhance Sentiment',
                'description': 'Sentiment is neutral. Improve content quality to achieve more positive AI responses.',
                'color': 'warning'
            })
        else:
            recommendations.append({
                'priority': 'Low',
                'title': 'Leverage Positive Sentiment',
                'description': 'Strong positive sentiment. Use this for brand building and thought leadership.',
                'color': 'success'
            })

        # Coverage recommendation
        if total_prompts < 20:
            recommendations.append({
                'priority': 'Medium',
                'title': 'Expand Prompt Coverage',
                'description': f'Only {total_prompts} prompts monitored. Add more diverse prompts to capture more opportunities.',
                'color': 'warning'
            })

        # Create recommendation cards
        for rec in recommendations:
            self._add_recommendation_card(rec)

        # Quick wins section
        self.story.append(Spacer(1, 20))
        self.story.append(Paragraph('Quick Wins', self.styles['SubsectionHeading']))

        quick_wins = [
            'Review and optimize your top-performing prompts for additional keywords',
            'Monitor competitor content strategies weekly for new opportunities',
            'Update website content based on common AI query patterns',
            'Track sentiment trends to identify potential reputation issues early',
        ]

        for win in quick_wins:
            self.story.append(Paragraph(f'• {win}', self.styles['CustomBody']))

    def _create_sentiment_card(self, label, count, percentage, color_key):
        """Create a sentiment summary card"""
        bg_color = self.COLORS.get(f'{color_key}_light', self.COLORS['light_gray'])
        accent_color = self.COLORS.get(color_key, self.COLORS['primary'])

        content = f'''<font size="9" color="#{accent_color.hexval()[2:]}">{label}</font><br/><br/>
<font size="22" color="#1f2937"><b>{percentage}%</b></font><br/><br/>
<font size="9" color="#6b7280">{count} responses</font>'''

        content_style = ParagraphStyle(
            'SentimentContent_' + color_key + '_' + str(id(self)),
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
        )

        cell_data = [[Paragraph(content, content_style)]]
        cell_table = Table(cell_data)
        cell_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return cell_table

    def _create_single_metric_cell(self, label, value, subtitle, color_key):
        """Create a styled metric cell with proper vertical stacking"""
        bg_color = self.COLORS.get(f'{color_key}_light', self.COLORS['light_gray'])
        accent_color = self.COLORS.get(color_key, self.COLORS['primary'])

        # Build content as a single paragraph with line breaks and explicit spacing
        content = f'''<font size="10" color="#{accent_color.hexval()[2:]}">{label}</font><br/><br/>
<font size="28" color="#1f2937"><b>{value}</b></font><br/><br/>
<font size="9" color="#6b7280">{subtitle}</font>'''

        content_style = ParagraphStyle(
            'MetricContent_' + color_key + '_' + str(id(self)),
            parent=self.styles['Normal'],
            fontSize=10,
            leading=16,
        )

        cell_data = [[Paragraph(content, content_style)]]
        cell_table = Table(cell_data)
        cell_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('LEFTPADDING', (0, 0), (-1, -1), 16),
            ('RIGHTPADDING', (0, 0), (-1, -1), 16),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return cell_table

    def _add_recommendation_card(self, rec):
        """Add a styled recommendation card"""
        color_key = rec.get('color', 'primary')
        bg_color = self.COLORS.get(f'{color_key}_light', self.COLORS['light_gray'])
        accent_color = self.COLORS.get(color_key, self.COLORS['primary'])

        # Priority badge
        priority_text = f'<font color="#{accent_color.hexval()[2:]}"><b>{rec["priority"]} Priority</b></font>'

        card_content = f"""
        {priority_text}<br/>
        <font size="12"><b>{rec['title']}</b></font><br/><br/>
        <font size="10" color="#6b7280">{rec['description']}</font>
        """

        card_data = [[Paragraph(card_content, self.styles['CustomBody'])]]
        card_table = Table(card_data, colWidths=[self.usable_width])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('LEFTPADDING', (0, 0), (-1, -1), 16),
            ('RIGHTPADDING', (0, 0), (-1, -1), 16),
            ('LINEBELOW', (0, 0), (-1, -1), 3, accent_color),
        ]))

        self.story.append(card_table)
        self.story.append(Spacer(1, 10))

    def _generate_detailed_analytics(self):
        """Generate Detailed Analytics report"""
        self.story.append(Paragraph('LLM Performance Overview', self.styles['SectionHeading']))

        llm_perf = self.data.get('llm_performance', {})
        if llm_perf:
            llm_data = [['LLM Model', 'Total Queries', 'Mentions', 'Avg Sentiment']]
            for llm_name, stats in llm_perf.items():
                llm_data.append([
                    llm_name.upper(),
                    str(stats.get('total', 0)),
                    str(stats.get('mentions', 0)),
                    f"{stats.get('avg_sentiment', 0):.2f}"
                ])

            llm_table = Table(llm_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            llm_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['dark']),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['white'], self.COLORS['light_gray']]),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))

            self.story.append(llm_table)
            self.story.append(Spacer(1, 0.3*inch))

        # Daily Statistics
        self.story.append(Paragraph('Daily Performance Trends', self.styles['SectionHeading']))

        daily_stats = self.data.get('daily_stats', [])[:14]
        if daily_stats:
            daily_data = [['Date', 'Total Queries', 'Mentions']]
            for stat in daily_stats:
                daily_data.append([
                    stat.get('date', ''),
                    str(stat.get('total', 0)),
                    str(stat.get('mentions', 0))
                ])

            daily_table = Table(daily_data, colWidths=[2*inch, 2*inch, 2*inch])
            daily_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['white'], self.COLORS['primary_light']]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))

            self.story.append(daily_table)

    def _generate_competitor_focus(self):
        """Generate Competitor Focus report with modern design"""

        our_metrics = self.data.get('our_metrics', {})
        total_competitors = self.data.get('total_competitors', 0)
        total_market = self.data.get('total_market_mentions', 0)
        competitors = self.data.get('competitors', [])

        # ===== SECTION 1: Market Overview Cards =====
        self.story.append(Paragraph('Market Overview', self.styles['SectionHeading']))

        # Create 2x2 metric cards
        card_width = (self.usable_width - 20) / 2

        # Row 1: Total Competitors and Market Mentions
        row1_data = [[
            self._create_single_metric_cell('Competitors Tracked', str(total_competitors), 'Active monitoring', 'info'),
            self._create_single_metric_cell('Market Mentions', str(total_market), 'Total across all brands', 'purple'),
        ]]
        row1_table = Table(row1_data, colWidths=[card_width, card_width])
        row1_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, -1), 10),
            ('RIGHTPADDING', (1, 0), (1, -1), 0),
        ]))
        self.story.append(row1_table)
        self.story.append(Spacer(1, 10))

        # Row 2: Your Share of Voice and Visibility Score
        our_sov = our_metrics.get('share_of_voice', 0)
        our_visibility = our_metrics.get('visibility_score', 0)
        row2_data = [[
            self._create_single_metric_cell('Your Share of Voice', f'{our_sov}%', 'Growing' if our_sov > 30 else 'Developing', 'success'),
            self._create_single_metric_cell('Your Visibility Score', f'{our_visibility}%', 'vs competitors', 'warning'),
        ]]
        row2_table = Table(row2_data, colWidths=[card_width, card_width])
        row2_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, -1), 10),
            ('RIGHTPADDING', (1, 0), (1, -1), 0),
        ]))
        self.story.append(row2_table)

        # ===== SECTION 2: Your Brand Performance =====
        self.story.append(Paragraph('Your Brand Performance', self.styles['SectionHeading']))

        our_mentions = our_metrics.get('mentions', 0)
        our_sentiment = our_metrics.get('sentiment_score', 0)

        our_data = [
            ['Metric', 'Value', 'Status'],
            ['Total Mentions', str(our_mentions), 'Active'],
            ['Visibility Score', f"{our_visibility}%", 'Tracking'],
            ['Share of Voice', f"{our_sov}%", 'Growing' if our_sov > 30 else 'Developing'],
            ['Sentiment Score', f"{our_sentiment:.2f}", 'Positive' if our_sentiment > 0 else 'Neutral'],
        ]

        # Full width table
        our_col_widths = [self.usable_width * 0.45, self.usable_width * 0.30, self.usable_width * 0.25]
        our_table = Table(our_data, colWidths=our_col_widths)
        our_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['white'], self.COLORS['primary_light']]),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        self.story.append(our_table)

        # ===== SECTION 3: Competitor Comparison Table =====
        self.story.append(Paragraph('Competitor Analysis', self.styles['SectionHeading']))

        if competitors:
            comp_data = [['#', 'Competitor', 'Mentions', 'Share of Voice', 'Visibility', 'Trend']]
            for idx, comp in enumerate(competitors[:10], 1):
                trend_val = comp.get('trend', 0)
                trend_icon = '+' if trend_val > 0 else ('-' if trend_val < 0 else '')
                trend_str = f"{trend_icon}{abs(trend_val)}%" if trend_val != 0 else "—"
                comp_data.append([
                    str(idx),
                    comp.get('name', '')[:25],
                    str(comp.get('mentions', 0)),
                    f"{comp.get('share_of_voice', 0)}%",
                    f"{comp.get('visibility_score', 0)}%",
                    trend_str
                ])

            # Full width columns
            comp_col_widths = [self.usable_width * 0.06, self.usable_width * 0.34, self.usable_width * 0.15,
                              self.usable_width * 0.18, self.usable_width * 0.15, self.usable_width * 0.12]
            comp_table = Table(comp_data, colWidths=comp_col_widths)
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['dark']),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['white'], self.COLORS['light_gray']]),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            self.story.append(comp_table)
        else:
            self.story.append(Paragraph('No competitor data available. Add competitors to enable analysis.', self.styles['CustomBody']))

        # ===== SECTION 4: Platform Performance =====
        platform_data = self.data.get('platform_breakdown', [])
        if platform_data:
            self.story.append(Paragraph('Platform Performance', self.styles['SectionHeading']))

            plat_table_data = [['Platform', 'Total Queries', 'Mentions', 'Mention Rate']]
            for plat in platform_data:
                plat_table_data.append([
                    plat.get('platform', 'Unknown').title(),
                    str(plat.get('total', 0)),
                    str(plat.get('mentions', 0)),
                    f"{plat.get('mention_rate', 0)}%"
                ])

            plat_col_widths = [self.usable_width * 0.30, self.usable_width * 0.25, self.usable_width * 0.22, self.usable_width * 0.23]
            plat_table = Table(plat_table_data, colWidths=plat_col_widths)
            plat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['info']),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['white'], self.COLORS['info_light']]),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            self.story.append(plat_table)

        # ===== SECTION 5: Sentiment Comparison =====
        if competitors:
            self.story.append(Paragraph('Sentiment Comparison', self.styles['SectionHeading']))

            sent_table_data = [['Brand', 'Sentiment Score', 'Rating']]
            # Add our brand first
            sent_table_data.append([
                self.data.get('domain_name', 'Your Brand'),
                f"{our_sentiment:.2f}",
                'Positive' if our_sentiment > 0.3 else ('Neutral' if our_sentiment >= 0 else 'Negative')
            ])
            # Add competitors
            for comp in competitors[:5]:
                sent = comp.get('sentiment_score', 0)
                sent_table_data.append([
                    comp.get('name', ''),
                    f"{sent:.2f}",
                    'Positive' if sent > 0.3 else ('Neutral' if sent >= 0 else 'Negative')
                ])

            sent_col_widths = [self.usable_width * 0.45, self.usable_width * 0.28, self.usable_width * 0.27]
            sent_table = Table(sent_table_data, colWidths=sent_col_widths)
            sent_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['success']),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                # Highlight our brand row
                ('BACKGROUND', (0, 1), (-1, 1), self.COLORS['success_light']),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                ('ROWBACKGROUNDS', (0, 2), (-1, -1), [self.COLORS['white'], self.COLORS['light_gray']]),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            self.story.append(sent_table)

        # ===== SECTION 6: Strategic Recommendations =====
        self.story.append(Spacer(1, 20))
        self.story.append(Paragraph('Strategic Recommendations', self.styles['SectionHeading']))

        # Generate insights as recommendation cards
        if competitors:
            top_competitor = competitors[0]

            # Market leader insight
            self._add_recommendation_card({
                'priority': 'Info',
                'title': 'Market Leader',
                'description': f"{top_competitor.get('name', 'N/A')} leads the market with {top_competitor.get('mentions', 0)} mentions and {top_competitor.get('share_of_voice', 0)}% share of voice.",
                'color': 'info'
            })

            # Your position insight
            if our_sov > 30:
                self._add_recommendation_card({
                    'priority': 'Strong',
                    'title': 'Competitive Position',
                    'description': f"Your {our_sov}% share of voice puts you in a strong competitive position. Focus on maintaining momentum.",
                    'color': 'success'
                })
            else:
                self._add_recommendation_card({
                    'priority': 'Opportunity',
                    'title': 'Growth Potential',
                    'description': f"Your current {our_sov}% share of voice has room for growth. Focus on content optimization to increase visibility.",
                    'color': 'warning'
                })

            # Actionable recommendation
            if len(competitors) > 1:
                gap = top_competitor.get('mentions', 0) - our_mentions
                if gap > 0:
                    self._add_recommendation_card({
                        'priority': 'Action',
                        'title': 'Close the Gap',
                        'description': f"You are {gap} mentions behind the market leader. Increase prompt coverage in key topic areas.",
                        'color': 'primary'
                    })
        else:
            self.story.append(Paragraph('Add competitors to your dashboard to generate competitive insights and benchmarking analysis.', self.styles['CustomBody']))

    def _generate_content_strategy(self):
        """Generate Content Strategy report"""

        # 1. Content Overview
        self.story.append(Paragraph('Content Overview', self.styles['SectionHeading']))

        overview = self.data.get('overview', {})
        domain_name = self.data.get('domain_name', 'N/A')

        overview_text = f"""
        <b>Domain:</b> {domain_name}<br/>
        <b>Content Quality Score:</b> {overview.get('content_quality_score', 0)}%<br/>
        <b>Topics Covered:</b> {overview.get('topics_covered', 0)}<br/>
        <b>Content Gaps Found:</b> {overview.get('content_gaps_found', 0)}<br/>
        <b>Engagement Rate:</b> {overview.get('engagement_rate', 0)}%
        """
        self.story.append(Paragraph(overview_text, self.styles['CustomBody']))
        self.story.append(Spacer(1, 0.3*inch))

        # 2. Topic Performance
        self.story.append(Paragraph('Topic Performance', self.styles['SectionHeading']))

        topics = self.data.get('topic_performance', [])
        if topics:
            topic_data = [['Topic', 'Mentions', 'Coverage', 'Sentiment', 'Trend']]
            for topic in topics[:10]:
                trend = topic.get('growth', 0)
                trend_str = f"+{trend}%" if trend > 0 else f"{trend}%"
                topic_data.append([
                    topic.get('name', '')[:25],
                    str(topic.get('mentions', 0)),
                    f"{topic.get('coverage_score', 0)}%",
                    f"{topic.get('sentiment', 0):.2f}",
                    trend_str
                ])

            topic_col_widths = [self.usable_width * 0.35, self.usable_width * 0.15, self.usable_width * 0.18, self.usable_width * 0.16, self.usable_width * 0.16]
            topic_table = Table(topic_data, colWidths=topic_col_widths)
            topic_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['white'], self.COLORS['primary_light']]),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            self.story.append(topic_table)
        else:
            self.story.append(Paragraph('No topic data available. Add topics to track performance.', self.styles['CustomBody']))

        # 3. Content Gaps
        self.story.append(Spacer(1, 0.4*inch))
        self.story.append(Paragraph('Content Gaps Analysis', self.styles['SectionHeading']))

        gaps = self.data.get('content_gaps', [])
        if gaps:
            gap_data = [['Keyword', 'Priority', 'Opportunity', 'Est. Traffic']]
            for gap in gaps[:10]:
                gap_data.append([
                    gap.get('keyword', '')[:30],
                    gap.get('priority', 'Medium'),
                    f"{gap.get('opportunity_score', 0)}/100",
                    f"+{gap.get('estimated_traffic', 0)}/mo"
                ])

            gap_col_widths = [self.usable_width * 0.35, self.usable_width * 0.20, self.usable_width * 0.23, self.usable_width * 0.22]
            gap_table = Table(gap_data, colWidths=gap_col_widths)
            gap_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['danger']),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.COLORS['white']),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLORS['danger_light'], self.COLORS['white']]),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            self.story.append(gap_table)
        else:
            self.story.append(Paragraph('No content gaps identified. Great coverage!', self.styles['CustomBody']))

        # 4. Recommendations
        self.story.append(Spacer(1, 0.4*inch))
        self.story.append(Paragraph('Strategic Recommendations', self.styles['SectionHeading']))

        recommendations = self.data.get('recommendations', [])
        if recommendations:
            for rec in recommendations[:5]:
                rec_text = f"""
                <b>{rec.get('priority', '')}. {rec.get('title', '')}</b><br/>
                {rec.get('description', '')}<br/>
                <i>Timeline: {rec.get('timeline', 'N/A')} | Expected: {rec.get('expected_traffic', 'N/A')}</i>
                """
                self.story.append(Paragraph(rec_text, self.styles['CustomBody']))
                self.story.append(Spacer(1, 0.1*inch))
        else:
            default_recs = []
            if gaps:
                default_recs.append(f"• <b>Address Content Gaps:</b> Focus on the top {min(5, len(gaps))} keyword gaps")
            if topics:
                low_coverage = [t for t in topics if t.get('coverage_score', 0) < 50]
                if low_coverage:
                    default_recs.append(f"• <b>Improve Topic Coverage:</b> {len(low_coverage)} topics need attention")
            if default_recs:
                for rec in default_recs:
                    self.story.append(Paragraph(rec, self.styles['CustomBody']))
            else:
                self.story.append(Paragraph('Maintain current content strategy and monitor for opportunities.', self.styles['CustomBody']))
