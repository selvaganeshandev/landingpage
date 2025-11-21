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
    Spacer, PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
import os


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
        """Generate Executive Dashboard report with all 5 sections"""

        # 1. Executive Summary
        self._add_executive_summary()
        self.story.append(Spacer(1, 0.4*inch))

        # 2. Key Metrics
        self._add_key_metrics()
        self.story.append(Spacer(1, 0.4*inch))

        # 3. Visibility Trends
        self._add_visibility_trends()
        self.story.append(Spacer(1, 0.4*inch))

        # 4. Competitive Landscape
        self._add_competitive_landscape()
        self.story.append(Spacer(1, 0.4*inch))

        # 5. Strategic Recommendations
        self._add_strategic_recommendations()

    def _add_executive_summary(self):
        """Add Executive Summary section with styled metric cards"""
        self.story.append(Paragraph('Executive Summary', self.styles['CustomHeading']))

        metrics = self.data.get('key_metrics', {})
        domain_name = self.data.get('domain_name', 'N/A')

        # Calculate metrics
        total_prompts = metrics.get('total_prompts', 0)
        total_mentions = metrics.get('total_mentions', 0)
        mention_rate = metrics.get('mention_rate', 0)
        avg_sentiment = metrics.get('avg_sentiment', 0)

        # Determine trends
        visibility_trend = '↗ Growing' if mention_rate > 50 else '→ Stable' if mention_rate > 30 else '↘ Needs Attention'
        mentions_trend = '↗ Up' if total_mentions > 100 else '→ Steady'
        sentiment_score = int(avg_sentiment * 100) if avg_sentiment > 0 else 50
        sentiment_trend = '✓ Positive' if avg_sentiment > 0.3 else '→ Neutral'

        # Create 4 metric cards in a row
        metric_cards_data = [
            ['🎯 Overall Visibility Score', '📊 Total AI Mentions'],
            [f'{mention_rate}%', f'{total_mentions}'],
            [visibility_trend, mentions_trend],
            ['', ''],
            ['✓ Positive Sentiment', '💰 Total Prompts Monitored'],
            [f'{sentiment_score}%', f'{total_prompts}'],
            [sentiment_trend, 'Tracking'],
        ]

        # Create a table for metric cards with colored backgrounds
        metric_table = Table(metric_cards_data, colWidths=[3*inch, 3*inch])
        metric_table.setStyle(TableStyle([
            # First row - Card titles
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#EFF6FF')),  # Blue background
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#FAF5FF')),  # Purple background
            ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#A855F7')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

            # Second row - Big numbers
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 24),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#1A1A1A')),
            ('TOPPADDING', (0, 1), (-1, 1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
            ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#EFF6FF')),
            ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#FAF5FF')),

            # Third row - Trends
            ('FONTSIZE', (0, 2), (-1, 2), 9),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#16A34A')),
            ('BACKGROUND', (0, 2), (0, 2), colors.HexColor('#EFF6FF')),
            ('BACKGROUND', (1, 2), (1, 2), colors.HexColor('#FAF5FF')),
            ('TOPPADDING', (0, 2), (-1, 2), 4),
            ('BOTTOMPADDING', (0, 2), (-1, 2), 12),

            # Spacing row
            ('LINEABOVE', (0, 3), (-1, 3), 0, colors.white),
            ('TOPPADDING', (0, 3), (-1, 3), 8),
            ('BOTTOMPADDING', (0, 3), (-1, 3), 8),

            # Fourth row - Second set of card titles
            ('BACKGROUND', (0, 4), (0, 4), colors.HexColor('#F0FDF4')),  # Green background
            ('BACKGROUND', (1, 4), (1, 4), colors.HexColor('#FEFCE8')),  # Amber background
            ('TEXTCOLOR', (0, 4), (0, 4), colors.HexColor('#22C55E')),
            ('TEXTCOLOR', (1, 4), (1, 4), colors.HexColor('#F59E0B')),
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 4), (-1, 4), 10),
            ('TOPPADDING', (0, 4), (-1, 4), 12),
            ('BOTTOMPADDING', (0, 4), (-1, 4), 8),

            # Fifth row - Big numbers
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 5), (-1, 5), 24),
            ('TEXTCOLOR', (0, 5), (-1, 5), colors.HexColor('#1A1A1A')),
            ('TOPPADDING', (0, 5), (-1, 5), 8),
            ('BOTTOMPADDING', (0, 5), (-1, 5), 8),
            ('BACKGROUND', (0, 5), (0, 5), colors.HexColor('#F0FDF4')),
            ('BACKGROUND', (1, 5), (1, 5), colors.HexColor('#FEFCE8')),

            # Sixth row - Trends
            ('FONTSIZE', (0, 6), (-1, 6), 9),
            ('TEXTCOLOR', (0, 6), (-1, 6), colors.HexColor('#16A34A')),
            ('BACKGROUND', (0, 6), (0, 6), colors.HexColor('#F0FDF4')),
            ('BACKGROUND', (1, 6), (1, 6), colors.HexColor('#FEFCE8')),
            ('TOPPADDING', (0, 6), (-1, 6), 4),
            ('BOTTOMPADDING', (0, 6), (-1, 6), 12),

            # Borders for all cards
            ('BOX', (0, 0), (0, 2), 1, colors.HexColor('#E5E7EB')),
            ('BOX', (1, 0), (1, 2), 1, colors.HexColor('#E5E7EB')),
            ('BOX', (0, 4), (0, 6), 1, colors.HexColor('#E5E7EB')),
            ('BOX', (1, 4), (1, 6), 1, colors.HexColor('#E5E7EB')),

            # Rounded corners effect
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ]))

        self.story.append(metric_table)

    def _add_key_metrics(self):
        """Add Key Performance Indicators section"""
        self.story.append(Paragraph('Key Performance Indicators', self.styles['CustomHeading']))

        metrics = self.data.get('key_metrics', {})

        # Create metrics cards layout
        metrics_data = [
            ['Metric', 'Current Value', 'Status'],
            ['Total Prompts Monitored', str(metrics.get('total_prompts', 0)), '📊'],
            ['Total Mentions Received', str(metrics.get('total_mentions', 0)), '✓'],
            ['Mention Rate', f"{metrics.get('mention_rate', 0)}%", '📈' if metrics.get('mention_rate', 0) > 50 else '📉'],
            ['Average Sentiment Score', f"{metrics.get('avg_sentiment', 0):.2f}", '😊' if metrics.get('avg_sentiment', 0) > 0 else '😐'],
            ['Competitors Tracked', str(metrics.get('competitor_count', 0)), '🎯'],
        ]

        metrics_table = Table(metrics_data, colWidths=[3*inch, 1.5*inch, 1*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))

        self.story.append(metrics_table)

        # Top Performing Prompts subsection
        self.story.append(Spacer(1, 0.3*inch))
        self.story.append(Paragraph('Top Performing Prompts', self.styles['CustomBody']))
        self.story.append(Spacer(1, 0.1*inch))

        top_prompts = self.data.get('top_prompts', [])
        if top_prompts:
            prompt_data = [['Rank', 'Prompt', 'Type', 'Mentions']]
            for idx, prompt in enumerate(top_prompts[:5], 1):
                prompt_data.append([
                    str(idx),
                    prompt.get('text', '')[:60] + ('...' if len(prompt.get('text', '')) > 60 else ''),
                    prompt.get('type', 'N/A').title(),
                    str(prompt.get('mentions', 0))
                ])

            prompt_table = Table(prompt_data, colWidths=[0.5*inch, 3.5*inch, 0.8*inch, 0.7*inch])
            prompt_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))

            self.story.append(prompt_table)
        else:
            self.story.append(Paragraph('No prompt performance data available for this period.', self.styles['CustomBody']))

    def _add_visibility_trends(self):
        """Add Visibility Trends section with chart"""
        self.story.append(Paragraph('Visibility Trends', self.styles['CustomHeading']))

        trend_text = """
        This section analyzes your visibility trends across AI platforms over the reporting period.
        The data shows patterns in how frequently your domain appears in AI responses.
        """
        self.story.append(Paragraph(trend_text, self.styles['CustomBody']))
        self.story.append(Spacer(1, 0.2*inch))

        # Simple trend visualization using table
        metrics = self.data.get('key_metrics', {})
        trend_data = [
            ['Metric', 'Value', 'Trend Indicator'],
            ['Mention Rate', f"{metrics.get('mention_rate', 0)}%", '→' if metrics.get('mention_rate', 0) >= 40 else '↗' if metrics.get('mention_rate', 0) >= 20 else '↘'],
            ['Total Mentions', str(metrics.get('total_mentions', 0)), '📊'],
            ['Sentiment Score', f"{metrics.get('avg_sentiment', 0):.2f}", '↗' if metrics.get('avg_sentiment', 0) > 0 else '→'],
        ]

        trend_table = Table(trend_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        trend_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        self.story.append(trend_table)

    def _add_competitive_landscape(self):
        """Add Competitive Landscape section"""
        self.story.append(Paragraph('Competitive Landscape', self.styles['CustomHeading']))

        landscape_text = """
        Understanding your position relative to competitors is crucial for strategic planning.
        This analysis shows how your visibility compares across the competitive landscape.
        """
        self.story.append(Paragraph(landscape_text, self.styles['CustomBody']))
        self.story.append(Spacer(1, 0.2*inch))

        # Competitive metrics
        metrics = self.data.get('key_metrics', {})
        comp_count = metrics.get('competitor_count', 0)

        if comp_count > 0:
            comp_summary = f"""
            <b>Competitive Overview:</b><br/>
            • Currently tracking <b>{comp_count}</b> direct competitors<br/>
            • Your mention rate: <b>{metrics.get('mention_rate', 0)}%</b><br/>
            • Your sentiment score: <b>{metrics.get('avg_sentiment', 0):.2f}</b><br/><br/>

            <i>Note: Detailed competitor analysis is available in the Competitor Focus report.</i>
            """
            self.story.append(Paragraph(comp_summary, self.styles['CustomBody']))
        else:
            self.story.append(Paragraph('No competitor data available. Add competitors in your dashboard to enable competitive analysis.', self.styles['CustomBody']))

    def _add_strategic_recommendations(self):
        """Add Strategic Recommendations section"""
        self.story.append(Paragraph('Strategic Recommendations', self.styles['CustomHeading']))

        metrics = self.data.get('key_metrics', {})
        mention_rate = metrics.get('mention_rate', 0)
        sentiment = metrics.get('avg_sentiment', 0)
        total_prompts = metrics.get('total_prompts', 0)

        # Generate recommendations based on metrics
        recommendations = []

        if mention_rate < 30:
            recommendations.append("• <b>Improve Mention Rate:</b> Your current mention rate of {:.1f}% is below target. Focus on creating more relevant content and optimizing existing prompts.".format(mention_rate))
        elif mention_rate < 50:
            recommendations.append("• <b>Optimize Mention Rate:</b> You're at {:.1f}% mention rate. Target 60%+ by refining top-performing prompt patterns.".format(mention_rate))
        else:
            recommendations.append("• <b>Maintain Excellence:</b> Your {:.1f}% mention rate is strong. Continue current strategies and explore new prompt categories.".format(mention_rate))

        if sentiment < 0:
            recommendations.append("• <b>Address Sentiment Issues:</b> Negative sentiment detected ({}). Review content accuracy and address user concerns.".format(sentiment))
        elif sentiment < 0.3:
            recommendations.append("• <b>Enhance Sentiment:</b> Sentiment is neutral. Improve content quality and relevance to achieve more positive responses.")
        else:
            recommendations.append("• <b>Leverage Positive Sentiment:</b> Strong positive sentiment ({}). Use this momentum for brand building.".format(sentiment))

        if total_prompts < 50:
            recommendations.append("• <b>Expand Coverage:</b> Only {} prompts monitored. Increase prompt diversity to capture more opportunities.".format(total_prompts))

        recommendations.append("• <b>Monitor Competitors:</b> Regularly review competitive positioning to identify gaps and opportunities.")
        recommendations.append("• <b>Optimize Content:</b> Focus on prompts with high engagement and low mention rates for quick wins.")

        rec_text = "<br/>".join(recommendations)
        rec_text = f"""
        <b>Key Action Items:</b><br/><br/>
        {rec_text}<br/><br/>

        <i>For detailed optimization strategies, refer to the Content Strategy report.</i>
        """

        self.story.append(Paragraph(rec_text, self.styles['CustomBody']))

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
