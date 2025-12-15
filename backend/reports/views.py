from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import ReportTemplate, ScheduledReport, GeneratedReport
from .serializers import (
    ReportTemplateSerializer,
    ScheduledReportSerializer,
    ScheduledReportCreateSerializer,
    ScheduledReportUpdateSerializer,
    GeneratedReportSerializer,
    GenerateReportRequestSerializer
)
from .services.html_to_pdf import convert_html_to_pdf
import logging
import zipfile
import io
import os

logger = logging.getLogger(__name__)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for report templates
    - Predefined templates are read-only (visible to all)
    - Custom templates can be created/updated/deleted by users (organisation-specific)
    """
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination

    def get_queryset(self):
        """
        Return:
        - All active predefined templates
        - Custom templates belonging to user's organisation
        """
        queryset = ReportTemplate.objects.filter(is_active=True)

        # Filter: predefined OR custom templates from user's org
        from django.db.models import Q
        queryset = queryset.filter(
            Q(template_type='predefined') |
            Q(template_type='custom', organisation=self.request.user.organisation)
        )

        # Optional filter by template_type
        template_type = self.request.query_params.get('template_type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)

        return queryset

    def perform_create(self, serializer):
        """Set organisation and created_by for custom templates"""
        # The serializer's create method already handles this,
        # but we can also do it here for clarity
        if serializer.validated_data.get('template_type') == 'custom':
            serializer.save(
                organisation=self.request.user.organisation,
                created_by=self.request.user
            )
        else:
            serializer.save()

    def perform_destroy(self, instance):
        """Only allow deletion of custom templates owned by user's organisation"""
        if instance.template_type == 'predefined':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot delete predefined templates")

        if instance.organisation != self.request.user.organisation:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot delete templates from other organisations")

        # Soft delete
        instance.is_active = False
        instance.save()

    def perform_update(self, serializer):
        """Only allow updating custom templates owned by user's organisation"""
        instance = self.get_object()

        if instance.template_type == 'predefined':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot modify predefined templates")

        if instance.organisation != self.request.user.organisation:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot modify templates from other organisations")

        serializer.save()


class ScheduledReportViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for scheduled reports
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination

    def get_queryset(self):
        # Filter by user's organisation
        queryset = ScheduledReport.objects.filter(
            organisation=self.request.user.organisation
        ).select_related('template', 'domain', 'created_by')

        # Optional domain filter
        domain_id = self.request.query_params.get('domain_id')
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return ScheduledReportCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ScheduledReportUpdateSerializer
        return ScheduledReportSerializer

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a scheduled report"""
        scheduled_report = self.get_object()
        scheduled_report.status = 'paused'
        scheduled_report.save()
        serializer = self.get_serializer(scheduled_report)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused report"""
        scheduled_report = self.get_object()
        scheduled_report.status = 'active'
        # Set next run time
        scheduled_report.next_run_at = self._calculate_next_run(scheduled_report)
        scheduled_report.save()
        serializer = self.get_serializer(scheduled_report)
        return Response(serializer.data)

    def _calculate_next_run(self, scheduled_report):
        """Calculate next run time based on frequency"""
        now = timezone.now()

        if scheduled_report.frequency == 'once':
            return None
        elif scheduled_report.frequency == 'daily':
            # Next day at schedule_time
            next_run = now.replace(
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0,
                microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        elif scheduled_report.frequency == 'weekly':
            # Next occurrence of schedule_day (0=Monday, 6=Sunday)
            days_ahead = scheduled_report.schedule_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0,
                microsecond=0
            )
            return next_run
        elif scheduled_report.frequency == 'monthly':
            # Next month on schedule_day
            if now.day < scheduled_report.schedule_day:
                next_month = now.month
                next_year = now.year
            else:
                next_month = now.month + 1 if now.month < 12 else 1
                next_year = now.year if now.month < 12 else now.year + 1

            next_run = now.replace(
                year=next_year,
                month=next_month,
                day=min(scheduled_report.schedule_day, 28),  # Avoid invalid dates
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0,
                microsecond=0
            )
            return next_run
        elif scheduled_report.frequency == 'quarterly':
            # Next quarter
            current_quarter = (now.month - 1) // 3
            next_quarter_month = (current_quarter + 1) * 3 + 1
            if next_quarter_month > 12:
                next_quarter_month = 1
                next_year = now.year + 1
            else:
                next_year = now.year

            next_run = now.replace(
                year=next_year,
                month=next_quarter_month,
                day=1,
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0,
                microsecond=0
            )
            return next_run

        return None


class GeneratedReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and download generated reports
    Read-only - reports are created via generation endpoint
    """
    serializer_class = GeneratedReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination

    def get_queryset(self):
        # Filter by user's organisation
        queryset = GeneratedReport.objects.filter(
            organisation=self.request.user.organisation
        ).select_related('domain', 'generated_by', 'scheduled_report')

        # Optional domain filter
        domain_id = self.request.query_params.get('domain_id')
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        return queryset

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download report file"""
        report = self.get_object()

        if not report.file_path:
            return Response(
                {'error': 'Report file not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            file_handle = report.file_path.open('rb')

            # Determine content type based on format
            content_type = 'application/pdf' if report.format.upper() == 'PDF' else 'application/octet-stream'

            response = FileResponse(
                file_handle,
                content_type=content_type
            )
            filename = f"{report.name}.{report.format.lower()}"

            # Use 'inline' instead of 'attachment' to display in browser
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        except FileNotFoundError:
            return Response(
                {'error': 'Report file not found on disk'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def download_all(self, request):
        """Download all reports as a single ZIP file"""
        # Get report IDs from query params (comma-separated)
        report_ids = request.query_params.get('ids', '')

        if report_ids:
            # Download specific reports
            ids_list = [int(id.strip()) for id in report_ids.split(',') if id.strip()]
            reports = self.get_queryset().filter(id__in=ids_list)
        else:
            # Download all reports for the domain/organization
            reports = self.get_queryset()

        if not reports.exists():
            return Response(
                {'error': 'No reports found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()

        files_added = 0
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for report in reports:
                if not report.file_path:
                    continue

                try:
                    # Get the file content
                    file_content = report.file_path.read()

                    # Create a clean filename
                    filename = f"{report.name}.{report.format.lower()}"
                    # Sanitize filename (remove invalid characters)
                    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).strip()

                    # Add to ZIP
                    zip_file.writestr(filename, file_content)
                    files_added += 1
                except Exception as e:
                    logger.warning(f"Could not add report {report.id} to ZIP: {str(e)}")
                    continue

        if files_added == 0:
            return Response(
                {'error': 'No report files available for download'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prepare response
        zip_buffer.seek(0)

        # Generate filename with date
        zip_filename = f"reports_{timezone.now().strftime('%Y-%m-%d')}.zip"

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

        return response


class ReportGenerationViewSet(viewsets.ViewSet):
    """
    Generate reports on-demand
    """
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Allow unauthenticated access for generate_by_id (internal engine endpoint).
        TODO: Add service token authentication for production.
        """
        if self.action == 'generate_by_id':
            from rest_framework.permissions import AllowAny
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'])
    def generate_now(self, request):
        """
        Generate a report immediately
        For now, this creates a placeholder record
        TODO: Implement actual report generation in Phase 2
        """
        serializer = GenerateReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        domain_id = data['domain_id']
        template_id = data['template_id']

        # Verify domain belongs to user's organisation
        from domains.models import Domain
        try:
            domain = Domain.objects.get(
                id=domain_id,
                organisation=request.user.organisation
            )
        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get template
        try:
            template = ReportTemplate.objects.get(id=template_id, is_active=True)
        except ReportTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Calculate date range
        days = data.get('data_period_days', 30)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Create generated report record (placeholder for now)
        generated_report = GeneratedReport.objects.create(
            organisation=request.user.organisation,
            domain=domain,
            name=f"{template.name} - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            report_type=template.name,
            format=data['format'],
            data_period_start=start_date,
            data_period_end=end_date,
            generated_by=request.user,
            summary_data={
                'sections': data.get('sections', []),
                'status': 'generating'
            }
        )

        # Generate report synchronously for now
        # TODO: Phase 3 - Move to async Celery task for production
        from reports.services.main import generate_report
        try:
            success = generate_report(generated_report.id)
            if not success:
                return Response(
                    {'error': 'Report generation failed'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': f'Report generation error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Refresh from database to get updated file info
        generated_report.refresh_from_db()

        serializer = GeneratedReportSerializer(
            generated_report,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def task_status(self, request):
        """
        Check generation task status
        TODO: Implement with Celery in Phase 3
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Placeholder response
        return Response({
            'task_id': task_id,
            'status': 'SUCCESS',
            'result': {'message': 'Report generation will be implemented in Phase 2'}
        })

    @action(detail=False, methods=['post'])
    def generate_by_id(self, request):
        """
        Generate a report by GeneratedReport ID.
        Internal API endpoint for engine to trigger report generation.
        """
        generated_report_id = request.data.get('generated_report_id')
        
        if not generated_report_id:
            return Response(
                {'error': 'generated_report_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            generated_report = GeneratedReport.objects.get(id=generated_report_id)
        except GeneratedReport.DoesNotExist:
            return Response(
                {'error': 'GeneratedReport not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate report synchronously
        from reports.services.main import generate_report
        try:
            success = generate_report(generated_report.id)
            if not success:
                return Response(
                    {'error': 'Report generation failed'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.error(f"Error generating report {generated_report.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Report generation error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Refresh from database to get updated file info
        generated_report.refresh_from_db()

        return Response({
            'success': True,
            'message': 'Report generated successfully',
            'report_id': generated_report.id,
            'file_path': str(generated_report.file_path) if generated_report.file_path else None,
            'file_size': generated_report.file_size
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_report_preview_data(request):
    """
    Get report preview data for frontend templates
    Accepts: domain_id, report_type, days (optional, default 30)
    """
    domain_id = request.query_params.get('domain_id')
    report_type = request.query_params.get('report_type')
    days = int(request.query_params.get('days', 30))

    if not domain_id or not report_type:
        return Response(
            {'error': 'domain_id and report_type are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verify domain belongs to user's organisation
    from domains.models import Domain
    try:
        domain = Domain.objects.get(
            id=domain_id,
            organisation=request.user.organisation
        )
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Calculate date range
    from datetime import datetime, time
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Get report data based on type
    from reports.services.report_generator import ReportDataService

    data_service = ReportDataService(
        domain=domain,
        start_date=start_date,
        end_date=end_date,
        organisation=request.user.organisation
    )

    try:
        if report_type == 'Competitor Focus':
            data = data_service.get_competitor_focus_data()
        elif report_type == 'Content Strategy':
            data = data_service.get_content_strategy_data()
        elif report_type == 'Executive Dashboard':
            data = data_service.get_executive_summary_data()
        elif report_type == 'Detailed Analytics':
            data = data_service.get_detailed_analytics_data()
        else:
            return Response(
                {'error': f'Unknown report type: {report_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert datetime objects to strings for JSON serialization
        if 'period' in data:
            if hasattr(data['period']['start'], 'strftime'):
                data['period']['start'] = data['period']['start'].strftime('%Y-%m-%d')
            if hasattr(data['period']['end'], 'strftime'):
                data['period']['end'] = data['period']['end'].strftime('%Y-%m-%d')

        return Response(data)

    except Exception as e:
        logger.error(f"Error getting report preview data: {str(e)}")
        return Response(
            {'error': f'Failed to get report data: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_custom_template_pdf(request):
    """
    Generate PDF directly from custom template data without saving
    Accepts: domain_id, template_name, grid_rows, start_date, end_date, html_template (optional), css_template (optional)
    Returns: PDF file with real widget data

    If html_template is provided, uses WeasyPrint for exact visual match.
    Otherwise, falls back to ReportLab generator.
    """
    domain_id = request.data.get('domain_id')
    template_name = request.data.get('template_name', 'Custom Report')
    grid_rows = request.data.get('grid_rows', [])
    html_template = request.data.get('html_template')  # NEW: Optional HTML template
    css_template = request.data.get('css_template', '')  # NEW: Optional CSS
    start_date_str = request.data.get('start_date')
    end_date_str = request.data.get('end_date')

    # Validation
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not grid_rows:
        return Response(
            {'error': 'grid_rows is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verify domain belongs to user's organisation
    from domains.models import Domain
    try:
        domain = Domain.objects.get(
            id=domain_id,
            organisation=request.user.organisation
        )
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Parse dates or use default (last 30 days)
    from datetime import datetime, time
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
            end_datetime = timezone.make_aware(datetime.combine(end_date, time.max))
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        end_datetime = timezone.now()
        start_datetime = end_datetime - timedelta(days=30)

    try:
        # Fetch widget data using WidgetDataFetcher
        from reports.services.widget_data_fetcher import WidgetDataFetcher

        widget_fetcher = WidgetDataFetcher(
            domain=domain,
            start_date=start_datetime,
            end_date=end_datetime,
            organisation=request.user.organisation
        )

        # Fetch data for all widgets in grid_rows
        data = widget_fetcher.fetch_all_widgets(grid_rows)

        # Add metadata
        data['_metadata'] = {
            'template_type': 'custom',
            'template_name': template_name,
            'grid_rows': grid_rows,
            'domain_name': domain.name,
            'domain_url': domain.url,
            'organisation_name': request.user.organisation.name,
            'period': {
                'start': start_datetime,
                'end': end_datetime
            }
        }

        # Generate PDF - ALWAYS try WeasyPrint first for better quality
        pdf_buffer = None
        
        try:
            from reports.services.weasyprint_pdf_generator import WeasyPrintPDFGenerator, WEASYPRINT_AVAILABLE
            from reports.services.html_generator import generate_html_report
            
            if not WEASYPRINT_AVAILABLE:
                raise ImportError("WeasyPrint not installed")
            
            logger.info(f"Using WeasyPrint for PDF generation")
            
            # Prepare metadata
            metadata = {
                'domain_name': domain.name,
                'domain_url': domain.url,
                'template_name': template_name,
                'organisation_name': request.user.organisation.name,
                'period': {
                    'start': start_datetime,
                    'end': end_datetime
                }
            }
            
            # ALWAYS generate HTML from grid_rows for PDF (not from saved html_template)
            # Saved html_template contains React components that won't render in PDF
            # This ensures charts are generated as SVG for proper PDF rendering
            logger.info("Generating HTML from grid_rows with SVG charts for PDF")
            html_template = generate_html_report(grid_rows, data, metadata)
            css_template = css_template or ''
            
            # Generate PDF with WeasyPrint
            generator = WeasyPrintPDFGenerator(html_template, css_template)
            pdf_buffer = generator.generate(data, metadata)
            
        except (ImportError, Exception) as e:
            logger.warning(f"WeasyPrint PDF generation failed, falling back to ReportLab: {str(e)}")
            
            # FALLBACK: Use ReportLab (original method)
            from reports.services.pdf_generator import PDFReportGenerator
            
            logger.info(f"Using ReportLab for PDF generation")
            
            # Create a mock template object for PDF generator
            class MockTemplate:
                def __init__(self, name, grid_rows):
                    self.name = name
                    self.template_type = 'custom'
                    self.grid_rows = grid_rows
            
            mock_template = MockTemplate(template_name, grid_rows)
            generator = PDFReportGenerator(data, template_name, template=mock_template)
            pdf_buffer = generator.generate()

        # Create HTTP response with PDF
        filename = f"{template_name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(f"Successfully generated custom template PDF: {filename}")
        return response

    except Exception as e:
        logger.error(f"Error generating custom template PDF: {str(e)}", exc_info=True)
        return Response(
            {'error': f'PDF generation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_report_html_to_pdf(request):
    """
    Convert HTML content to PDF
    Accepts HTML from frontend report template and converts to PDF
    """
    html_content = request.data.get('html_content')
    css_content = request.data.get('css_content', '')
    filename = request.data.get('filename', 'report.pdf')

    if not html_content:
        logger.error("HTML content missing in request")
        return Response(
            {'error': 'HTML content is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        logger.info(f"Converting HTML to PDF for filename: {filename}")

        # Convert HTML to PDF
        pdf_buffer = convert_html_to_pdf(html_content, css_content)

        # Create HTTP response with PDF
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(f"Successfully generated PDF: {filename}")
        return response

    except Exception as e:
        logger.error(f"Error converting HTML to PDF: {str(e)}")
        return Response(
            {'error': f'PDF conversion failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
