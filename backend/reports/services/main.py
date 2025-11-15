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


def generate_report(report_id):
    """
    Main function to generate a report
    Args:
        report_id: ID of the GeneratedReport model instance
    Returns:
        True if successful, False otherwise
    """
    from reports.models import GeneratedReport
    from domains.models import Domain

    try:
        # Get the report record
        report = GeneratedReport.objects.get(id=report_id)

        # Get the domain
        domain = report.domain

        # Get date range
        end_date = report.data_period_end
        start_date = report.data_period_start

        # Initialize data service
        data_service = ReportDataService(
            domain=domain,
            start_date=start_date,
            end_date=end_date,
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
            generator = PDFReportGenerator(data, report.report_type)
            file_buffer = generator.generate()
            file_extension = 'pdf'
        elif report.format == 'Excel':
            generator = ExcelReportGenerator(data, report.report_type)
            file_buffer = generator.generate()
            file_extension = 'xlsx'
        elif report.format == 'PowerPoint':
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
                'date_range': f"{start_date} to {end_date}",
            }
        }

        report.save()

        return True

    except Exception as e:
        print(f"Error generating report {report_id}: {str(e)}")

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
