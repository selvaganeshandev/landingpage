"""
Main Report Generation Coordinator
Orchestrates data fetching and report generation
"""
from django.core.files.base import ContentFile
from datetime import timedelta
from django.utils import timezone

from .report_generator import ReportDataService
from .pdf_generator import PDFReportGenerator
from .excel_generator import ExcelReportGenerator
from .powerpoint_generator import PowerPointReportGenerator
from .widget_data_fetcher import WidgetDataFetcher
from .html_generator import generate_html_report
from .weasyprint_pdf_generator import WeasyPrintPDFGenerator, WEASYPRINT_AVAILABLE
import logging

logger = logging.getLogger(__name__)


def generate_report(report_id):
    """
    Main function to generate a report
    Args:
        report_id: ID of the GeneratedReport model instance
    Returns:
        True if successful, False otherwise
    """
    from reports.models import GeneratedReport, ReportTemplate
    from domains.models import Domain

    try:
        # Get the report record
        report = GeneratedReport.objects.get(id=report_id)

        # Get the domain
        domain = report.domain

        # Get date range and convert to timezone-aware datetimes
        from datetime import datetime, time

        # Convert date to datetime at start of day (00:00:00)
        start_datetime = timezone.make_aware(datetime.combine(report.data_period_start, time.min))
        # Convert date to datetime at end of day (23:59:59)
        end_datetime = timezone.make_aware(datetime.combine(report.data_period_end, time.max))

        # Get the template if available
        template = None
        if report.scheduled_report:
            template = report.scheduled_report.template
        else:
            # Try to find template by report type
            try:
                template = ReportTemplate.objects.get(
                    name=report.report_type,
                    is_active=True
                )
            except ReportTemplate.DoesNotExist:
                pass

        # Determine if this is a custom template with widgets
        is_custom_template = template and template.template_type == 'custom' and template.grid_rows

        if is_custom_template:
            # Custom template - fetch data for widgets
            widget_fetcher = WidgetDataFetcher(
                domain=domain,
                start_date=start_datetime,
                end_date=end_datetime,
                organisation=report.organisation
            )

            # Fetch data for all widgets in the template
            data = widget_fetcher.fetch_all_widgets(template.grid_rows)

            # Add metadata
            data['_metadata'] = {
                'template_type': 'custom',
                'template_name': template.name,
                'template_id': template.id,
                'grid_rows': template.grid_rows,
                'domain_name': domain.name,
                'domain_url': domain.url,
                'organisation_name': report.organisation.name,
                'period': {
                    'start': start_datetime,
                    'end': end_datetime
                }
            }

        else:
            # Predefined template - use legacy report data service
            data_service = ReportDataService(
                domain=domain,
                start_date=start_datetime,
                end_date=end_datetime,
                organisation=report.organisation
            )

            # Fetch data based on report type
            if report.report_type == 'Executive Dashboard':
                data = data_service.get_executive_summary_data()
            elif report.report_type == 'Detailed Analytics':
                data = data_service.get_detailed_analytics_data()
            elif report.report_type == 'Competitor Focus':
                data = data_service.get_competitor_focus_data()
            elif report.report_type == 'Content Strategy':
                data = data_service.get_content_strategy_data()
            else:
                raise ValueError(f"Unknown report type: {report.report_type}")

        # Generate the file based on format
        file_buffer = None
        file_extension = ''

        if report.format == 'PDF':
            # Use WeasyPrint for all PDFs if available (better visual quality)
            if WEASYPRINT_AVAILABLE:
                try:
                    logger.info(f"Using WeasyPrint for PDF generation (report_id: {report.id})")
                    
                    # Generate HTML template
                    if is_custom_template:
                        # ALWAYS regenerate HTML from grid_rows for PDFs
                        # Saved html_template contains React components that won't render in PDF
                        # This ensures charts are generated as SVG for proper PDF rendering
                        logger.info("Generating HTML from grid_rows with SVG charts for PDF")
                        html_template = generate_html_report(
                            template.grid_rows,
                            data,
                            data.get('_metadata', {})
                        )
                        css_template = ''
                    else:
                        # For predefined templates, generate HTML on-the-fly
                        logger.info("Generating HTML for predefined template")
                        # Create a simple grid_rows structure for predefined templates
                        grid_rows = _create_grid_rows_for_predefined(report.report_type, data)
                        html_template = generate_html_report(
                            grid_rows,
                            data,
                            {
                                'domain_name': domain.name,
                                'domain_url': domain.url,
                                'template_name': report.report_type,
                                'organisation_name': report.organisation.name,
                                'period': {
                                    'start': start_datetime,
                                    'end': end_datetime
                                }
                            }
                        )
                        css_template = ''
                    
                    # Generate PDF with WeasyPrint
                    generator = WeasyPrintPDFGenerator(html_template, css_template)
                    file_buffer = generator.generate(data, {
                        'domain_name': domain.name,
                        'template_name': report.report_type,
                        'period': {
                            'start': start_datetime,
                            'end': end_datetime
                        }
                    })
                    file_extension = 'pdf'
                    logger.info("PDF generated successfully with WeasyPrint")
                    
                except Exception as e:
                    logger.warning(f"WeasyPrint PDF generation failed, falling back to ReportLab: {str(e)}")
                    # Fallback to ReportLab
                    generator = PDFReportGenerator(data, report.report_type, template=template)
                    file_buffer = generator.generate()
                    file_extension = 'pdf'
            else:
                logger.info("WeasyPrint not available, using ReportLab")
                # Fallback to ReportLab if WeasyPrint not available
                generator = PDFReportGenerator(data, report.report_type, template=template)
                file_buffer = generator.generate()
                file_extension = 'pdf'
        elif report.format == 'Excel':
            # Excel format not supported for custom templates yet
            if is_custom_template:
                raise ValueError("Excel format is not supported for custom templates yet. Please use PDF format.")
            generator = ExcelReportGenerator(data, report.report_type)
            file_buffer = generator.generate()
            file_extension = 'xlsx'
        elif report.format == 'PowerPoint':
            # PowerPoint format not supported for custom templates yet
            if is_custom_template:
                raise ValueError("PowerPoint format is not supported for custom templates yet. Please use PDF format.")
            generator = PowerPointReportGenerator(data, report.report_type)
            file_buffer = generator.generate()
            file_extension = 'pptx'
        else:
            raise ValueError(f"Unsupported format: {report.format}")

        # Save the file
        filename = f"{report.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        report.file_path.save(filename, ContentFile(file_buffer.read()), save=False)

        # Update file size
        report.file_size = report.file_path.size

        # Estimate page count (for PDF)
        if report.format == 'PDF':
            report.page_count = estimate_pdf_pages(data, report.report_type)
        elif report.format == 'Excel':
            report.page_count = estimate_excel_sheets(report.report_type)
        elif report.format == 'PowerPoint':
            report.page_count = estimate_ppt_slides(data, report.report_type)

        # Update summary data
        report.summary_data = {
            'status': 'completed',
            'generated_at': timezone.now().isoformat(),
            'data_summary': {
                'total_records': get_total_records(data),
                'date_range': f"{start_datetime.date()} to {end_datetime.date()}",
            }
        }

        report.save()

        return True

    except Exception as e:
        logger.error(f"Error generating report {report_id}: {str(e)}", exc_info=True)

        # Update report with error
        try:
            report = GeneratedReport.objects.get(id=report_id)
            report.summary_data = {
                'status': 'error',
                'error': str(e),
                'failed_at': timezone.now().isoformat(),
            }
            report.save()
        except:
            pass

        return False


def estimate_pdf_pages(data, report_type):
    """Estimate number of pages in PDF report"""
    # Simple estimation based on data volume
    base_pages = 2  # Title + summary

    if report_type == 'Executive Dashboard':
        return base_pages + 2
    elif report_type == 'Detailed Analytics':
        daily_stats = data.get('daily_stats', [])
        return base_pages + 3 + (len(daily_stats) // 30)  # One page per ~30 days
    elif report_type == 'Competitor Focus':
        competitors = data.get('competitors', [])
        return base_pages + (len(competitors) // 10)  # One page per ~10 competitors
    elif report_type == 'Content Strategy':
        gaps = data.get('content_gaps', [])
        opportunities = data.get('optimization_opportunities', [])
        return base_pages + 2 + ((len(gaps) + len(opportunities)) // 20)

    return base_pages


def estimate_excel_sheets(report_type):
    """Estimate number of sheets in Excel report"""
    if report_type == 'Executive Dashboard':
        return 3  # Summary + metrics + top prompts
    elif report_type == 'Detailed Analytics':
        return 4  # Summary + LLM perf + daily stats + trends
    elif report_type == 'Competitor Focus':
        return 2  # Summary + competitors
    elif report_type == 'Content Strategy':
        return 3  # Summary + gaps + optimization

    return 2


def estimate_ppt_slides(data, report_type):
    """Estimate number of slides in PowerPoint"""
    base_slides = 1  # Title

    if report_type == 'Executive Dashboard':
        return base_slides + 2  # Metrics + top prompts
    elif report_type == 'Detailed Analytics':
        return base_slides + 2  # LLM performance + trends
    elif report_type == 'Competitor Focus':
        return base_slides + 1  # Competitors
    elif report_type == 'Content Strategy':
        return base_slides + 2  # Gaps + optimization

    return base_slides + 1


def get_total_records(data):
    """Get total number of data records processed"""
    total = 0

    if 'top_prompts' in data:
        total += len(data['top_prompts'])
    if 'daily_stats' in data:
        total += len(data['daily_stats'])
    if 'competitors' in data:
        total += len(data['competitors'])
    if 'content_gaps' in data:
        total += len(data['content_gaps'])
    if 'optimization_opportunities' in data:
        total += len(data['optimization_opportunities'])

    return total


def _create_grid_rows_for_predefined(report_type, data):
    """
    Create grid_rows structure for predefined templates
    Converts old report data structure to widget-based grid_rows
    """
    grid_rows = []
    
    if report_type == 'Executive Dashboard':
        # Row 1: Key metrics (quad)
        grid_rows.append({
            'id': 'row-1',
            'type': 'quad',
            'slots': [
                {'id': 'total-prompts', 'type': 'metric', 'title': 'Total Prompts'},
                {'id': 'total-mentions', 'type': 'metric', 'title': 'Total Mentions'},
                {'id': 'mention-rate', 'type': 'metric', 'title': 'Mention Rate'},
                {'id': 'avg-sentiment', 'type': 'metric', 'title': 'Avg Sentiment'},
            ]
        })
        
        # Row 2: Charts (double)
        if 'platform_breakdown' in data or 'sentiment_breakdown' in data:
            grid_rows.append({
                'id': 'row-2',
                'type': 'double',
                'slots': [
                    {'id': 'platform-chart', 'type': 'chart', 'title': 'Platform Breakdown'},
                    {'id': 'sentiment-chart', 'type': 'chart', 'title': 'Sentiment Breakdown'},
                ]
            })
        
        # Row 3: Top prompts table
        if 'top_prompts' in data:
            grid_rows.append({
                'id': 'row-3',
                'type': 'single',
                'slots': [
                    {'id': 'top-prompts-table', 'type': 'table', 'title': 'Top Performing Prompts'},
                ]
            })
    
    elif report_type == 'Competitor Focus':
        # Row 1: Comparison metrics
        grid_rows.append({
            'id': 'row-1',
            'type': 'triple',
            'slots': [
                {'id': 'our-mentions', 'type': 'metric', 'title': 'Our Mentions'},
                {'id': 'share-of-voice', 'type': 'metric', 'title': 'Share of Voice'},
                {'id': 'market-position', 'type': 'metric', 'title': 'Market Position'},
            ]
        })
        
        # Row 2: Competitor table
        if 'competitors' in data:
            grid_rows.append({
                'id': 'row-2',
                'type': 'single',
                'slots': [
                    {'id': 'competitors-table', 'type': 'table', 'title': 'Competitor Comparison'},
                ]
            })
    
    elif report_type == 'Content Strategy':
        # Row 1: Content metrics
        grid_rows.append({
            'id': 'row-1',
            'type': 'triple',
            'slots': [
                {'id': 'content-score', 'type': 'metric', 'title': 'Content Quality Score'},
                {'id': 'total-topics', 'type': 'metric', 'title': 'Total Topics'},
                {'id': 'content-gaps', 'type': 'metric', 'title': 'Content Gaps'},
            ]
        })
        
        # Row 2: Gap analysis table
        if 'content_gaps' in data:
            grid_rows.append({
                'id': 'row-2',
                'type': 'single',
                'slots': [
                    {'id': 'gaps-table', 'type': 'table', 'title': 'Content Gap Analysis'},
                ]
            })
    
    else:
        # Default: Just show key metrics
        grid_rows.append({
            'id': 'row-1',
            'type': 'quad',
            'slots': [
                {'id': 'metric-1', 'type': 'metric', 'title': 'Metric 1'},
                {'id': 'metric-2', 'type': 'metric', 'title': 'Metric 2'},
                {'id': 'metric-3', 'type': 'metric', 'title': 'Metric 3'},
                {'id': 'metric-4', 'type': 'metric', 'title': 'Metric 4'},
            ]
        })
    
    return grid_rows
