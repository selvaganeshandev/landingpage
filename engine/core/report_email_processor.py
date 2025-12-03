"""
Report Email Delivery Processor
Processes scheduled reports and sends emails via Mailgun
"""
import logging
import requests
from datetime import timedelta
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .mailgun_email_service import MailgunEmailService

logger = logging.getLogger(__name__)


class ReportEmailProcessor:
    """
    Processor for scheduled report email delivery.
    Checks for due scheduled reports and sends them via email.
    """

    def __init__(self):
        """Initialize processor with email service"""
        self.email_service = MailgunEmailService()
        self.backend_api_url = getattr(settings, 'BACKEND_API_URL', 'http://localhost:8000')

    def process_due_reports(self) -> Dict[str, Any]:
        """
        Process all scheduled reports that are due for generation and email delivery.

        Returns:
            Dict with processing results
        """
        from shared_models.models import ScheduledReport

        # Get all active scheduled reports that are due
        now = timezone.now()
        due_reports = ScheduledReport.objects.filter(
            status='active',
            next_run_at__lte=now,
            next_run_at__isnull=False  # Only process reports with next_run_at set
        ).select_related('template', 'domain', 'organisation')

        if not due_reports.exists():
            logger.debug("No due scheduled reports found")
            return {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'messages': []
            }

        logger.info(f"Found {due_reports.count()} due scheduled reports")

        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'messages': []
        }

        for scheduled_report in due_reports:
            try:
                result = self._process_single_scheduled_report(scheduled_report)
                results['processed'] += 1

                if result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1

                results['messages'].append(result['message'])

            except Exception as e:
                logger.error(
                    f"Error processing scheduled report {scheduled_report.id}: {e}",
                    exc_info=True
                )
                results['processed'] += 1
                results['failed'] += 1
                results['messages'].append(
                    f"Error processing report {scheduled_report.id}: {str(e)}"
                )

        return results

    def _process_single_scheduled_report(
        self,
        scheduled_report
    ) -> Dict[str, Any]:
        """
        Process a single scheduled report: generate and send via email.

        Args:
            scheduled_report: ScheduledReport instance

        Returns:
            Dict with success status and message
        """
        from shared_models.models import GeneratedReport

        logger.info(
            f"Processing scheduled report {scheduled_report.id}: {scheduled_report.name}"
        )

        # Calculate date range
        days = 30  # Default period, can be made configurable
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Create GeneratedReport record
        try:
            # Get template name safely
            template_name = scheduled_report.template.name if scheduled_report.template else 'Unknown'
            
            generated_report = GeneratedReport.objects.create(
                scheduled_report=scheduled_report,
                organisation=scheduled_report.organisation,
                domain=scheduled_report.domain,
                name=f"{scheduled_report.name} - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                report_type=template_name,
                format=scheduled_report.formats[0] if scheduled_report.formats else 'PDF',
                data_period_start=start_date,
                data_period_end=end_date,
                generated_by=scheduled_report.created_by,
                summary_data={
                    'sections': scheduled_report.sections or [],
                    'status': 'generating'
                }
            )

            # Generate report file by calling backend API
            logger.info(f"Generating report file for {generated_report.id} via backend API")
            success = self._generate_report_via_api(generated_report.id)

            if not success:
                return {
                    'success': False,
                    'message': f"Report generation failed for {scheduled_report.id}"
                }

            # Refresh to get updated file info
            generated_report.refresh_from_db()

            # Send email with report attachment
            if 'Email' in scheduled_report.formats or scheduled_report.recipients:
                email_result = self._send_report_email(
                    scheduled_report,
                    generated_report
                )

                if not email_result['success']:
                    return {
                        'success': False,
                        'message': f"Email delivery failed: {email_result['message']}"
                    }

            # Update scheduled report: calculate next run time
            with transaction.atomic():
                scheduled_report.last_generated_at = timezone.now()
                scheduled_report.next_run_at = self._calculate_next_run(scheduled_report)
                scheduled_report.save(update_fields=['last_generated_at', 'next_run_at'])

            logger.info(
                f"Successfully processed scheduled report {scheduled_report.id}"
            )

            return {
                'success': True,
                'message': f"Report {scheduled_report.id} generated and sent successfully"
            }

        except Exception as e:
            logger.error(
                f"Error processing scheduled report {scheduled_report.id}: {e}",
                exc_info=True
            )
            return {
                'success': False,
                'message': f"Error: {str(e)}"
            }

    def _generate_report_via_api(self, generated_report_id: int) -> bool:
        """
        Generate report by calling backend API.

        Args:
            generated_report_id: ID of GeneratedReport to generate

        Returns:
            True if successful, False otherwise
        """
        try:
            # Call backend API to generate the report
            # This endpoint should be internal and not require authentication
            # or use a service account token
            url = f"{self.backend_api_url}/reports/generation/generate_by_id/"
            
            response = requests.post(
                url,
                json={'generated_report_id': generated_report_id},
                timeout=300  # 5 minutes timeout for report generation
            )

            if response.status_code == 200:
                logger.info(f"Report {generated_report_id} generated successfully via API")
                return True
            else:
                logger.error(
                    f"Failed to generate report {generated_report_id} via API: "
                    f"Status {response.status_code}, Response: {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error calling backend API to generate report {generated_report_id}: {e}",
                exc_info=True
            )
            return False

    def _send_report_email(
        self,
        scheduled_report,
        generated_report
    ) -> Dict[str, Any]:
        """
        Send generated report via email.

        Args:
            scheduled_report: ScheduledReport instance
            generated_report: GeneratedReport instance

        Returns:
            Dict with success status
        """
        # Get recipients
        recipients = scheduled_report.recipients or []
        if not recipients:
            logger.warning(f"No recipients configured for scheduled report {scheduled_report.id}")
            return {
                'success': False,
                'message': 'No recipients configured'
            }

        # Prepare email content
        subject = f"Your {scheduled_report.name} Report"
        body_text = self._generate_email_body_text(scheduled_report, generated_report)
        body_html = self._generate_email_body_html(scheduled_report, generated_report)

        # Prepare attachment
        attachments = []
        if generated_report.file_path:
            try:
                # Get the absolute path to the file
                # file_path is a FileField, so we need to get the actual file system path
                import os

                # Construct the full path to the reports directory
                # The file_path is stored as a relative path like 'reports/filename.pdf'
                backend_root = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'backend'
                )

                full_file_path = os.path.join(backend_root, str(generated_report.file_path))

                logger.info(f"Reading report file from: {full_file_path}")

                # Read the file content
                with open(full_file_path, 'rb') as f:
                    file_content = f.read()

                filename = f"{generated_report.name}.{generated_report.format.lower()}"
                attachments.append({
                    'filename': filename,
                    'content': file_content,
                    'content_type': self._get_content_type(generated_report.format)
                })

                logger.info(f"Successfully read report file: {filename} ({len(file_content)} bytes)")

            except Exception as e:
                logger.error(f"Error reading report file for attachment: {e}", exc_info=True)

        # Send email
        result = self.email_service.send_report_email(
            recipients=recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments
        )

        return result

    def _generate_email_body_text(
        self,
        scheduled_report,
        generated_report
    ) -> str:
        """Generate plain text email body"""
        domain_name = scheduled_report.domain.name
        report_name = scheduled_report.name
        period_start = generated_report.data_period_start.strftime('%Y-%m-%d')
        period_end = generated_report.data_period_end.strftime('%Y-%m-%d')

        return f"""
Hello,

Your scheduled report "{report_name}" has been generated and is attached to this email.

Report Details:
--------------
Domain: {domain_name}
Report Type: {generated_report.report_type}
Format: {generated_report.format}
Period: {period_start} to {period_end}
Generated: {generated_report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

The report file is attached to this email.

View in dashboard: {self.email_service.frontend_url}/reports

---
LLM Monitor Report System
"""

    def _generate_email_body_html(
        self,
        scheduled_report,
        generated_report
    ) -> str:
        """Generate HTML email body"""
        domain_name = scheduled_report.domain.name
        report_name = scheduled_report.name
        period_start = generated_report.data_period_start.strftime('%Y-%m-%d')
        period_end = generated_report.data_period_end.strftime('%Y-%m-%d')

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4F46E5; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .details {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .button {{ display: inline-block; padding: 10px 20px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Your Report is Ready</h2>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>Your scheduled report <strong>"{report_name}"</strong> has been generated and is attached to this email.</p>
            
            <div class="details">
                <h3>Report Details</h3>
                <p><strong>Domain:</strong> {domain_name}</p>
                <p><strong>Report Type:</strong> {generated_report.report_type}</p>
                <p><strong>Format:</strong> {generated_report.format}</p>
                <p><strong>Period:</strong> {period_start} to {period_end}</p>
                <p><strong>Generated:</strong> {generated_report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <p>The report file is attached to this email.</p>
            
            <a href="{self.email_service.frontend_url}/reports" class="button">View in Dashboard</a>
        </div>
        <div class="footer">
            <p>LLM Monitor Report System</p>
            <p>This is an automated email. Please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""

    def _get_content_type(self, format: str) -> str:
        """Get MIME content type for report format"""
        format_lower = format.lower()
        if format_lower == 'pdf':
            return 'application/pdf'
        elif format_lower in ['xlsx', 'xls', 'excel']:
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif format_lower in ['pptx', 'ppt', 'powerpoint']:
            return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        else:
            return 'application/octet-stream'

    def _calculate_next_run(self, scheduled_report) -> Optional:
        """Calculate next run time based on frequency"""
        from datetime import datetime, time

        now = timezone.now()

        if scheduled_report.frequency == 'once':
            return None
        elif scheduled_report.frequency == 'daily':
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
            if now.day < scheduled_report.schedule_day:
                next_month = now.month
                next_year = now.year
            else:
                next_month = now.month + 1 if now.month < 12 else 1
                next_year = now.year if now.month < 12 else now.year + 1

            next_run = now.replace(
                year=next_year,
                month=next_month,
                day=min(scheduled_report.schedule_day, 28),
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0,
                microsecond=0
            )
            return next_run
        elif scheduled_report.frequency == 'quarterly':
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

