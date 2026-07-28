# Report Email Delivery Implementation

## Overview
This document describes the implementation of automated email delivery for scheduled reports using Mailgun SMTP in the engine.

## Architecture

```
Backend (Reports Module)
  ↓
ScheduledReport (stored in database)
  ↓
Engine (Celery Beat Scheduler - every 15 seconds)
  ↓
ReportEmailProcessor (checks due reports)
  ↓
Backend API (generates report file)
  ↓
MailgunEmailService (sends emails via Mailgun SMTP)
  ↓
Email delivered to recipients with report attachment
```

## Files Created/Modified

### Engine Files

1. **`engine/llm_monitor_engine/settings.py`**
   - Added Mailgun SMTP email configuration
   - Added `BACKEND_API_URL` for engine-to-backend communication
   - Added Celery Beat schedule for report email processing

2. **`engine/core/mailgun_email_service.py`** (NEW)
   - `MailgunEmailService` class for sending emails via Mailgun SMTP
   - Supports text and HTML email bodies
   - Supports file attachments
   - Error handling and logging

3. **`engine/core/report_email_processor.py`** (NEW)
   - `ReportEmailProcessor` class for processing scheduled reports
   - Checks for due scheduled reports
   - Creates GeneratedReport records
   - Calls backend API to generate report files
   - Sends emails with report attachments
   - Calculates next run time for scheduled reports

4. **`engine/core/processing_tasks.py`**
   - Added `process_report_email_scheduler` Celery task (runs every 15 seconds)
   - Added `process_single_report_email_task` for manual triggers

5. **`engine/shared_models/models.py`**
   - Added `ScheduledReport` model (read-only from engine)
   - Added `GeneratedReport` model (read-only from engine)

### Backend Files

6. **`backend/reports/views.py`**
   - Added `generate_by_id` endpoint for engine to trigger report generation
   - Allows unauthenticated access for internal engine calls

## Configuration

### Environment Variables

Add to `.env` file:

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

## How It Works

### 1. Scheduled Report Creation
- User creates a scheduled report via frontend
- Report is stored in `scheduled_reports` table with:
  - Frequency (daily/weekly/monthly/quarterly)
  - Schedule time and day
  - Recipients list
  - Output formats
  - `next_run_at` calculated based on frequency

### 2. Periodic Processing
- Celery Beat runs `process_report_email_scheduler` every 15 seconds
- Processor checks for scheduled reports where `next_run_at <= now`
- For each due report:
  1. Creates a `GeneratedReport` record
  2. Calls backend API to generate the report file
  3. Sends email with report attachment to recipients
  4. Updates `next_run_at` for next occurrence

### 3. Email Delivery
- `MailgunEmailService` sends emails via Mailgun SMTP
- Email includes:
  - Plain text and HTML body
  - Report file as attachment
  - Links to dashboard

### 4. Next Run Calculation
- Processor calculates next run time based on frequency:
  - **Daily**: Next day at schedule time
  - **Weekly**: Next occurrence of schedule day
  - **Monthly**: Next month on schedule day
  - **Quarterly**: Next quarter
  - **Once**: No next run (disabled after first run)

## API Endpoints

### Backend Endpoints

**POST `/api/reports/generation/generate_by_id/`**
- Internal endpoint for engine to trigger report generation
- Body: `{"generated_report_id": <id>}`
- Returns: Report generation status

## Testing

### Manual Testing

1. **Create a scheduled report:**
   ```python
   # Via Django shell or API
   scheduled_report = ScheduledReport.objects.create(
       organisation=org,
       domain=domain,
       name="Test Report",
       template=template,
       frequency='daily',
       schedule_time='09:00:00',
       formats=['PDF'],
       recipients=['test@example.com'],
       status='active',
       next_run_at=timezone.now() - timedelta(minutes=1)  # Set to past to trigger immediately
   )
   ```

2. **Check Celery logs:**
   ```bash
   # Engine logs should show:
   # "Found X due scheduled reports"
   # "Processing scheduled report X"
   # "Email sent successfully to X recipients"
   ```

3. **Verify email delivery:**
   - Check recipient inbox
   - Verify report attachment
   - Check email content

### Automated Testing

Run Celery Beat and Celery Worker:
```bash
# Terminal 1: Celery Beat
cd engine
celery -A llm_monitor_engine beat -l info

# Terminal 2: Celery Worker
cd engine
celery -A llm_monitor_engine worker -l info
```

## Error Handling

- **Email sending failures**: Logged but don't fail the entire process
- **Report generation failures**: Logged and marked in GeneratedReport summary_data
- **SMTP connection errors**: Retried with exponential backoff
- **Missing recipients**: Warning logged, report still generated

## Security Considerations

1. **API Authentication**: The `generate_by_id` endpoint currently allows unauthenticated access. In production, add:
   - Service token authentication
   - IP whitelist for engine
   - API key validation

2. **Email Security**:
   - Use TLS for SMTP connections
   - Store credentials in environment variables
   - Validate recipient email addresses

## Future Enhancements

1. **Service Token Authentication**: Add authentication for engine-to-backend API calls
2. **Retry Logic**: Add retry mechanism for failed email deliveries
3. **Email Templates**: Support custom email templates per report type
4. **Delivery Tracking**: Track email delivery status (sent, delivered, bounced)
5. **Rate Limiting**: Limit number of emails sent per hour/day
6. **Async Report Generation**: Move report generation to async Celery task

## Troubleshooting

### Emails Not Sending

1. Check Mailgun credentials in `.env`
2. Verify SMTP connection:
   ```python
   from engine.core.mailgun_email_service import MailgunEmailService
   service = MailgunEmailService()
   result = service.send_simple_email(
       recipients=['test@example.com'],
       subject='Test',
       body='Test email'
   )
   print(result)
   ```

3. Check engine logs for SMTP errors

### Reports Not Generating

1. Check backend API is accessible from engine
2. Verify `BACKEND_API_URL` in engine settings
3. Check backend logs for report generation errors
4. Verify GeneratedReport record exists in database

### Scheduled Reports Not Processing

1. Check Celery Beat is running
2. Verify `next_run_at` is set correctly
3. Check Celery logs for scheduler errors
4. Verify scheduled report `status` is 'active'

## Monitoring

Monitor the following:
- Number of scheduled reports processed per hour
- Email delivery success rate
- Report generation success rate
- Average time to generate and send reports
- Failed email deliveries

## Support

For issues or questions:
1. Check engine logs: `logs/engine.log`
2. Check backend logs: `logs/backend.log`
3. Review Celery task logs
4. Check Mailgun dashboard for email delivery status

