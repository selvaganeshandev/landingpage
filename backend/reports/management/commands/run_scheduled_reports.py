"""
Management command to execute scheduled reports that are due.
Run via cron every 5-10 minutes:
    */5 * * * * cd /path/to/project && python manage.py run_scheduled_reports
"""
import calendar
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from reports.models import ScheduledReport, GeneratedReport
from reports.services.main import generate_report

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Execute scheduled reports that are due'

    def handle(self, *args, **options):
        now = timezone.now()
        due_reports = ScheduledReport.objects.filter(
            status='active',
            next_run_at__lte=now,
            next_run_at__isnull=False,
        ).select_related('template', 'domain', 'organisation', 'created_by')

        count = due_reports.count()
        if count == 0:
            self.stdout.write('No scheduled reports due.')
            return

        self.stdout.write(f'Found {count} scheduled report(s) due.')

        for scheduled in due_reports:
            try:
                self.stdout.write(f'  Running: {scheduled.name} (id={scheduled.id})')
                self._execute_report(scheduled, now)
                self.stdout.write(self.style.SUCCESS(f'  Done: {scheduled.name}'))
            except Exception as e:
                logger.error(f'Failed to run scheduled report {scheduled.id}: {e}', exc_info=True)
                self.stdout.write(self.style.ERROR(f'  Failed: {scheduled.name} - {e}'))

        self.stdout.write(self.style.SUCCESS(f'Finished processing {count} report(s).'))

    def _execute_report(self, scheduled, now):
        """Create a GeneratedReport, run generation, update schedule."""
        # Determine date range (last 30 days by default)
        end_date = now.date()
        start_date = end_date - timedelta(days=30)

        # Generate for each format
        formats = scheduled.formats or ['PDF']
        for fmt in formats:
            fmt_upper = fmt.upper()
            if fmt_upper not in ('PDF', 'EXCEL', 'POWERPOINT'):
                continue

            # Create GeneratedReport record
            generated = GeneratedReport.objects.create(
                scheduled_report=scheduled,
                organisation=scheduled.organisation,
                domain=scheduled.domain,
                name=scheduled.name,
                report_type=scheduled.template.name if scheduled.template else 'Custom Report',
                format=fmt_upper if fmt_upper != 'EXCEL' else 'Excel',
                data_period_start=start_date,
                data_period_end=end_date,
                generated_by=scheduled.created_by,
            )

            # Run generation
            success = generate_report(generated.id)
            if not success:
                logger.warning(f'Report generation failed for GeneratedReport id={generated.id}')

        # Update schedule timestamps
        scheduled.last_generated_at = now
        scheduled.next_run_at = self._calculate_next_run(scheduled)

        # For one-time reports, mark as paused after execution
        if scheduled.frequency == 'once':
            scheduled.status = 'paused'

        scheduled.save(update_fields=['last_generated_at', 'next_run_at', 'status', 'modified_at'])

    def _calculate_next_run(self, scheduled_report):
        """Calculate next run time based on frequency (same logic as views.py)"""
        now = timezone.now()

        if scheduled_report.frequency == 'once':
            return None
        elif scheduled_report.frequency == 'daily':
            next_run = now.replace(
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0, microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        elif scheduled_report.frequency == 'weekly':
            days_ahead = scheduled_report.schedule_day - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0, microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(days=7)
            return next_run
        elif scheduled_report.frequency == 'monthly':
            next_month = now.month
            next_year = now.year
            schedule_day = scheduled_report.schedule_day or 1

            if now.day >= schedule_day:
                next_month = now.month + 1 if now.month < 12 else 1
                next_year = now.year if now.month < 12 else now.year + 1

            max_day = calendar.monthrange(next_year, next_month)[1]
            day = min(schedule_day, max_day)

            next_run = now.replace(
                year=next_year, month=next_month, day=day,
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0, microsecond=0
            )
            return next_run
        elif scheduled_report.frequency == 'quarterly':
            current_quarter = (now.month - 1) // 3
            next_quarter = (current_quarter + 1) % 4
            next_quarter_month = next_quarter * 3 + 1
            next_year = now.year + 1 if next_quarter == 0 else now.year

            next_run = now.replace(
                year=next_year, month=next_quarter_month, day=1,
                hour=scheduled_report.schedule_time.hour,
                minute=scheduled_report.schedule_time.minute,
                second=0, microsecond=0
            )
            return next_run

        return None
