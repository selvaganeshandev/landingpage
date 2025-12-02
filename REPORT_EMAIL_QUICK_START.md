# Report Email Delivery - Quick Start Guide

## Setup

### 1. Environment Variables

Add to `.env` file in both `backend/` and `engine/` directories:

```bash
# Mailgun SMTP Configuration
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=postmaster@your-domain.mailgun.org
EMAIL_HOST_PASSWORD=your-mailgun-smtp-password
DEFAULT_FROM_EMAIL=LLM Monitor <noreply@your-domain.com>
FRONTEND_URL=http://localhost:8080
EMAIL_TIMEOUT=10

# Backend API URL (for engine to call backend)
BACKEND_API_URL=http://localhost:8000

# Celery Beat Schedule (optional, defaults to 15 seconds)
CELERY_BEAT_SCHEDULE_REPORT_EMAIL=15.0
```

### 2. Start Services

```bash
# Terminal 1: Backend
cd backend
python manage.py runserver

# Terminal 2: Engine Celery Beat
cd engine
celery -A llm_monitor_engine beat -l info

# Terminal 3: Engine Celery Worker
cd engine
celery -A llm_monitor_engine worker -l info
```

## Testing

### Create a Test Scheduled Report

1. **Via Frontend:**
   - Go to `http://localhost:8080/reports`
   - Click "Schedule Report"
   - Fill in details:
     - Name: "Test Daily Report"
     - Template: Select any template
     - Frequency: Daily
     - Time: Set to a few minutes from now
     - Recipients: Your email address
     - Formats: PDF

2. **Via Django Shell:**
   ```python
   from reports.models import ScheduledReport, ReportTemplate
   from domains.models import Domain
   from authentication.models import Organisation, Account
   from django.utils import timezone
   from datetime import timedelta
   
   # Get objects
   org = Organisation.objects.first()
   domain = Domain.objects.first()
   template = ReportTemplate.objects.first()
   user = Account.objects.first()
   
   # Create scheduled report
   scheduled_report = ScheduledReport.objects.create(
       organisation=org,
       domain=domain,
       name="Test Daily Report",
       template=template,
       frequency='daily',
       schedule_time='09:00:00',
       formats=['PDF'],
       recipients=['your-email@example.com'],
       status='active',
       next_run_at=timezone.now() + timedelta(minutes=1)  # Run in 1 minute
   )
   ```

### Verify Processing

1. **Check Engine Logs:**
   ```bash
   tail -f logs/engine.log | grep -i "report"
   ```

2. **Expected Log Messages:**
   ```
   Found X due scheduled reports
   Processing scheduled report X: Test Daily Report
   Generating report file for X via backend API
   Report X generated successfully via API
   Email sent successfully to X recipients
   Successfully processed scheduled report X
   ```

3. **Check Email:**
   - Check recipient inbox
   - Verify report PDF attachment
   - Verify email content

## Troubleshooting

### Emails Not Sending

1. **Check Mailgun Credentials:**
   ```python
   from engine.core.mailgun_email_service import MailgunEmailService
   service = MailgunEmailService()
   print(f"Host: {service.email_host}")
   print(f"User: {service.email_host_user}")
   print(f"Password set: {bool(service.email_host_password)}")
   ```

2. **Test Email Sending:**
   ```python
   from engine.core.mailgun_email_service import MailgunEmailService
   service = MailgunEmailService()
   result = service.send_simple_email(
       recipients=['test@example.com'],
       subject='Test Email',
       body='This is a test email from LLM Monitor'
   )
   print(result)
   ```

### Reports Not Generating

1. **Check Backend API:**
   ```bash
   curl -X POST http://localhost:8000/reports/generation/generate_by_id/ \
     -H "Content-Type: application/json" \
     -d '{"generated_report_id": 1}'
   ```

2. **Check GeneratedReport:**
   ```python
   from reports.models import GeneratedReport
   report = GeneratedReport.objects.get(id=1)
   print(f"Status: {report.summary_data.get('status')}")
   print(f"File: {report.file_path}")
   ```

### Scheduled Reports Not Processing

1. **Check next_run_at:**
   ```python
   from reports.models import ScheduledReport
   from django.utils import timezone
   
   now = timezone.now()
   due = ScheduledReport.objects.filter(
       status='active',
       next_run_at__lte=now
   )
   print(f"Due reports: {due.count()}")
   for r in due:
       print(f"  {r.id}: {r.name} - next_run_at: {r.next_run_at}")
   ```

2. **Check Celery Beat:**
   - Verify Celery Beat is running
   - Check logs for scheduler errors
   - Verify task is registered: `celery -A llm_monitor_engine inspect registered`

## API Endpoints

### Backend

**POST `/reports/generation/generate_by_id/`**
- Internal endpoint for engine
- Body: `{"generated_report_id": <id>}`
- Returns: `{"success": true, "message": "...", "report_id": <id>}`

## Files Reference

- **Email Service:** `engine/core/mailgun_email_service.py`
- **Report Processor:** `engine/core/report_email_processor.py`
- **Celery Tasks:** `engine/core/processing_tasks.py`
- **Shared Models:** `engine/shared_models/models.py`
- **Backend API:** `backend/reports/views.py`

## Next Steps

1. Set up Mailgun account and domain
2. Configure environment variables
3. Create a test scheduled report
4. Monitor logs for processing
5. Verify email delivery

For detailed documentation, see `REPORT_EMAIL_DELIVERY_IMPLEMENTATION.md`

