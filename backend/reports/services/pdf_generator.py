"""
PDF Report Generator using ReportLab
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart


class PDFReportGenerator:
    """Generate PDF reports using ReportLab"""

    def __init__(self, report_data, report_type):
        self.data = report_data
        self.report_type = report_type
        self.buffer = BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )
        self.styles = getSampleStyleSheet()
        self.story = []

        # Custom styles
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12,
        ))

        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            spaceAfter=8,
        ))

    def generate(self):
        """Generate the PDF and return BytesIO buffer"""
        # Add title
        self._add_title()

        # Add content based on report type
        if self.report_type == 'Executive Dashboard':
            self._generate_executive_dashboard()
        elif self.report_type == 'Detailed Analytics':
            self._generate_detailed_analytics()
        elif self.report_type == 'Competitor Focus':
            self._generate_competitor_focus()
        elif self.report_type == 'Content Strategy':
            self._generate_content_strategy()

        # Build PDF
        self.doc.build(self.story)
        self.buffer.seek(0)
        return self.buffer

    def _add_title(self):
        """Add report title and metadata"""
        title = Paragraph(self.report_type, self.styles['CustomTitle'])
        self.story.append(title)

        # Add domain and period info
        meta_text = f"""
        <b>Domain:</b> {self.data.get('domain_name', 'N/A')}<br/>
        <b>Period:</b> {self.data['period']['start'].strftime('%Y-%m-%d')} to {self.data['period']['end'].strftime('%Y-%m-%d')}<br/>
        <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        meta = Paragraph(meta_text, self.styles['CustomBody'])
        self.story.append(meta)
        self.story.append(Spacer(1, 0.3*inch))

    def _generate_executive_dashboard(self):
        """Generate Executive Dashboard report"""
        # Key Metrics Section
        self.story.append(Paragraph('Key Performance Indicators', self.styles['CustomHeading']))

        metrics = self.data.get('key_metrics', {})
        metrics_data = [
            ['Metric', 'Value'],
            ['Total Prompts', str(metrics.get('total_prompts', 0))],
            ['Total Mentions', str(metrics.get('total_mentions', 0))],
            ['Mention Rate', f"{metrics.get('mention_rate', 0)}%"],
            ['Average Sentiment', f"{metrics.get('avg_sentiment', 0):.2f}"],
            ['Competitors Tracked', str(metrics.get('competitor_count', 0))],
        ]

        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))

        self.story.append(metrics_table)
        self.story.append(Spacer(1, 0.3*inch))

        # Top Performing Prompts
        self.story.append(Paragraph('Top Performing Prompts', self.styles['CustomHeading']))

        top_prompts = self.data.get('top_prompts', [])
        if top_prompts:
            prompt_data = [['Prompt', 'Type', 'Mentions']]
            for prompt in top_prompts[:5]:
                prompt_data.append([
                    prompt.get('text', '')[:50] + '...',
                    prompt.get('type', 'N/A'),
                    str(prompt.get('mentions', 0))
                ])

            prompt_table = Table(prompt_data, colWidths=[3.5*inch, 1*inch, 1*inch])
            prompt_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))

            self.story.append(prompt_table)
        else:
            self.story.append(Paragraph('No prompt data available', self.styles['CustomBody']))

    def _generate_detailed_analytics(self):
        """Generate Detailed Analytics report"""
        self.story.append(Paragraph('LLM Performance Overview', self.styles['CustomHeading']))

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
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            self.story.append(llm_table)
            self.story.append(Spacer(1, 0.3*inch))

        # Daily Statistics
        self.story.append(Paragraph('Daily Performance Trends', self.styles['CustomHeading']))

        daily_stats = self.data.get('daily_stats', [])[:14]  # Last 14 days
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
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            self.story.append(daily_table)

    def _generate_competitor_focus(self):
        """Generate Competitor Focus report"""
        self.story.append(Paragraph('Competitive Landscape', self.styles['CustomHeading']))

        # Our mentions vs competitors
        our_mentions = self.data.get('our_mentions', 0)
        info_text = f"<b>Our Domain Mentions:</b> {our_mentions}"
        self.story.append(Paragraph(info_text, self.styles['CustomBody']))
        self.story.append(Spacer(1, 0.2*inch))

        # Competitor table
        competitors = self.data.get('competitors', [])
        if competitors:
            comp_data = [['Competitor', 'Website', 'Mentions']]
            for comp in competitors[:10]:
                comp_data.append([
                    comp.get('name', ''),
                    comp.get('website', '')[:30],
                    str(comp.get('mentions', 0))
                ])

            comp_table = Table(comp_data, colWidths=[2*inch, 2.5*inch, 1.5*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            self.story.append(comp_table)
        else:
            self.story.append(Paragraph('No competitor data available', self.styles['CustomBody']))

    def _generate_content_strategy(self):
        """Generate Content Strategy report"""
        self.story.append(Paragraph('Content Gaps Analysis', self.styles['CustomHeading']))

        gaps = self.data.get('content_gaps', [])
        if gaps:
            gap_text = f"Found {len(gaps)} prompts with no mentions. Top gaps:"
            self.story.append(Paragraph(gap_text, self.styles['CustomBody']))
            self.story.append(Spacer(1, 0.1*inch))

            gap_data = [['Prompt', 'Type']]
            for gap in gaps[:10]:
                gap_data.append([
                    gap.get('text', '')[:60] + '...',
                    gap.get('type', 'N/A')
                ])

            gap_table = Table(gap_data, colWidths=[4*inch, 1.5*inch])
            gap_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            self.story.append(gap_table)
            self.story.append(Spacer(1, 0.3*inch))

        # Optimization Opportunities
        self.story.append(Paragraph('Optimization Opportunities', self.styles['CustomHeading']))

        opportunities = self.data.get('optimization_opportunities', [])
        if opportunities:
            opp_data = [['Prompt', 'Current Mention Rate']]
            for opp in opportunities[:10]:
                opp_data.append([
                    opp.get('text', '')[:60] + '...',
                    f"{opp.get('mention_rate', 0)}%"
                ])

            opp_table = Table(opp_data, colWidths=[4.5*inch, 1.5*inch])
            opp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            self.story.append(opp_table)
