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

logger = logging.getLogger(__name__)


class ReportTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List available report templates
    Read-only - templates are predefined
    """
    queryset = ReportTemplate.objects.filter(is_active=True)
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination


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


class ReportGenerationViewSet(viewsets.ViewSet):
    """
    Generate reports on-demand
    """
    permission_classes = [IsAuthenticated]

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
