# Reports Module Architecture

## Overview

The Reports module provides a comprehensive reporting system that allows users to generate, schedule, and manage analytics reports in multiple formats (PDF, Excel, PowerPoint). The system is built with Django REST Framework on the backend and React/TypeScript on the frontend.

## Backend Architecture

### URL Routing (`backend/reports/urls.py`)

The reports module is accessible at `/reports/` and includes the following endpoints:

```
/reports/
├── templates/              # Report templates (read-only)
├── scheduled/             # Scheduled reports (CRUD)
├── generated/             # Generated reports (read-only + download)
├── generation/            # Report generation endpoints
├── convert-to-pdf/        # HTML to PDF conversion
└── preview-data/          # Report preview data
```

### Models (`backend/reports/models.py`)

#### 1. **ReportTemplate**
- Predefined report templates (Executive Dashboard, Detailed Analytics, Competitor Focus, Content Strategy)
- Fields: `name`, `description`, `sections` (JSON), `is_active`
- Read-only for users (managed by admins)

#### 2. **ScheduledReport**
- User-configured scheduled reports
- Fields:
  - Scheduling: `frequency` (once/daily/weekly/monthly/quarterly), `schedule_day`, `schedule_time`
  - Configuration: `sections` (JSON), `formats` (JSON), `recipients` (JSON)
  - Status: `status` (active/paused), `last_generated_at`, `next_run_at`
- Relationships: `organisation`, `domain`, `template`, `created_by`

#### 3. **GeneratedReport**
- History of generated reports
- Fields:
  - File info: `format` (PDF/Excel/PowerPoint), `file_path`, `file_size`, `page_count`
  - Metadata: `data_period_start`, `data_period_end`, `summary_data` (JSON)
- Relationships: `scheduled_report` (optional), `organisation`, `domain`, `generated_by`

### Views (`backend/reports/views.py`)

#### 1. **ReportTemplateViewSet** (ReadOnlyModelViewSet)
- `GET /reports/templates/` - List all active templates
- `GET /reports/templates/{id}/` - Get template details

#### 2. **ScheduledReportViewSet** (ModelViewSet)
- `GET /reports/scheduled/` - List scheduled reports (filtered by domain)
- `POST /reports/scheduled/` - Create new scheduled report
- `GET /reports/scheduled/{id}/` - Get scheduled report details
- `PATCH /reports/scheduled/{id}/` - Update scheduled report
- `DELETE /reports/scheduled/{id}/` - Delete scheduled report
- `POST /reports/scheduled/{id}/pause/` - Pause scheduled report
- `POST /reports/scheduled/{id}/resume/` - Resume paused report

#### 3. **GeneratedReportViewSet** (ReadOnlyModelViewSet)
- `GET /reports/generated/` - List generated reports (filtered by domain)
- `GET /reports/generated/{id}/` - Get generated report details
- `GET /reports/generated/{id}/download/` - Download report file
- `GET /reports/generated/download_all/?ids=1,2,3` - Download multiple reports as ZIP

#### 4. **ReportGenerationViewSet** (ViewSet)
- `POST /reports/generation/generate_now/` - Generate report immediately
  - Request body: `{domain_id, template_id, sections, format, data_period_days}`
  - Creates `GeneratedReport` record and triggers generation
- `POST /reports/generation/generate_by_id/` - Generate report by ID (internal/engine use)
- `GET /reports/generation/task_status/?task_id=...` - Check generation status (placeholder)

#### 5. **Utility Endpoints**
- `GET /reports/preview-data/?domain_id=X&report_type=Y&days=30` - Get preview data for frontend
- `POST /reports/convert-to-pdf/` - Convert HTML content to PDF

### Services Layer

#### 1. **ReportDataService** (`backend/reports/services/report_generator.py`)
Fetches and aggregates data from various sources:

- **`get_executive_summary_data()`**
  - Key metrics: total prompts, mentions, mention rate, sentiment
  - Top performing prompts
  - Platform breakdown
  - Sentiment breakdown
  - Competitor count

- **`get_detailed_analytics_data()`**
  - LLM performance by model (ChatGPT, Claude, Gemini, Perplexity)
  - Daily performance trends
  - Query statistics

- **`get_competitor_focus_data()`**
  - Our brand metrics vs competitors
  - Share of voice calculations
  - Competitor comparison table
  - Platform performance
  - Sentiment comparison

- **`get_content_strategy_data()`**
  - Content quality score
  - Topic performance
  - Content gaps analysis
  - Untapped keywords
  - Trending keywords
  - Strategic recommendations

#### 2. **Report Generation** (`backend/reports/services/main.py`)
- **`generate_report(report_id)`** - Main orchestration function
  1. Fetches `GeneratedReport` record
  2. Initializes `ReportDataService` with domain and date range
  3. Fetches data based on report type
  4. Generates file using appropriate generator (PDF/Excel/PowerPoint)
  5. Saves file to `GeneratedReport.file_path`
  6. Updates metadata (file_size, page_count, summary_data)

#### 3. **Format Generators**

- **PDFGenerator** (`backend/reports/services/pdf_generator.py`)
  - Uses ReportLab library
  - Modern design with color-coded sections
  - Supports all 4 report types
  - Includes charts, tables, and formatted text

- **ExcelGenerator** (`backend/reports/services/excel_generator.py`)
  - Uses openpyxl library
  - Multiple sheets per report type

- **PowerPointGenerator** (`backend/reports/services/powerpoint_generator.py`)
  - Uses python-pptx library
  - Slide-based presentation format

## Frontend Architecture

### Main Page (`frontend/src/pages/Reports.tsx`)

The Reports page is the main interface at `/reports` (http://localhost:8080/reports).

#### State Management
- Uses React Query for data fetching and caching
- Domain selection via `useDomainStore`
- Multiple dialog states for different actions

#### Data Fetching
```typescript
// Templates (always loaded)
useQuery(['reportTemplates'], () => apiClient.getReportTemplates())

// Scheduled reports (filtered by domain)
useQuery(['scheduledReports', domainId], 
  () => apiClient.getScheduledReports({ domain_id: domainId }),
  { enabled: !!domainId }
)

// Generated reports (filtered by domain)
useQuery(['generatedReports', domainId],
  () => apiClient.getGeneratedReports({ domain_id: domainId }),
  { enabled: !!domainId }
)
```

#### Key Features

1. **Quick Actions**
   - Generate Now - Create report immediately
   - Schedule Report - Set up recurring reports
   - Download All - Download all reports as ZIP
   - Share Report - (Coming soon)

2. **Scheduled Reports Section**
   - Lists all scheduled reports for selected domain
   - Shows: name, template, schedule, status, next run time
   - Actions: View, Run Now, Edit, Pause/Resume, Delete

3. **Report Templates Section**
   - Displays available templates with thumbnails
   - Shows: name, description, section count
   - Actions: Preview, Use Template

4. **Dialogs**
   - `CreateReportDialog` - Create new scheduled report
   - `EditReportDialog` - Edit existing scheduled report
   - `ScheduleReportDialog` - Configure scheduling
   - `GenerateNowDialog` - Generate report immediately
   - `ReportPreviewDialog` - Preview report data
   - `PDFViewerDialog` - View/download generated PDFs

### API Client (`frontend/src/services/api.ts`)

All report-related API methods:

```typescript
// Templates
getReportTemplates()
getReportTemplate(id)

// Scheduled Reports
getScheduledReports(params?)
createScheduledReport(data)
getScheduledReport(id)
updateScheduledReport(id, data)
deleteScheduledReport(id)
pauseScheduledReport(id)
resumeScheduledReport(id)

// Generated Reports
getGeneratedReports(params?)
getGeneratedReport(id)
downloadReport(id, filename?)
downloadAllReports(ids, domainId)

// Generation
generateReport(data) // {domain_id, template_id, sections, format, data_period_days}
```

### Components

1. **CreateReportDialog** - Form to create new scheduled report
2. **EditReportDialog** - Form to edit existing scheduled report
3. **ScheduleReportDialog** - Configure report scheduling
4. **GenerateNowDialog** - Quick report generation
5. **ReportPreviewDialog** - Preview report data before generation
6. **PDFViewerDialog** - Embedded PDF viewer with download option

## Data Flow

### Report Generation Flow

```
1. User clicks "Generate Now" or "Run Now"
   ↓
2. Frontend calls POST /reports/generation/generate_now/
   ↓
3. Backend creates GeneratedReport record
   ↓
4. Backend calls generate_report(report_id)
   ↓
5. ReportDataService fetches data from database
   ↓
6. Format generator (PDF/Excel/PPT) creates file
   ↓
7. File saved to GeneratedReport.file_path
   ↓
8. Frontend polls/refreshes generated reports list
   ↓
9. User can view/download the generated report
```

### Scheduled Report Flow

```
1. User creates scheduled report via CreateReportDialog
   ↓
2. Frontend calls POST /reports/scheduled/
   ↓
3. Backend creates ScheduledReport with next_run_at calculated
   ↓
4. (Future: Celery task checks for scheduled reports)
   ↓
5. When scheduled time arrives:
   - Create GeneratedReport from ScheduledReport
   - Generate report file
   - Send email to recipients (if configured)
   - Update last_generated_at and next_run_at
```

### Preview Flow

```
1. User clicks "Preview" on template or scheduled report
   ↓
2. Frontend calls GET /reports/preview-data/?domain_id=X&report_type=Y&days=30
   ↓
3. Backend fetches data using ReportDataService
   ↓
4. Returns JSON data structure
   ↓
5. Frontend displays data in ReportPreviewDialog
```

## Key Design Decisions

1. **Synchronous Generation**: Currently reports are generated synchronously. TODO: Move to Celery for async processing.

2. **Domain Filtering**: All reports are scoped to domains and organizations for multi-tenancy.

3. **Format Support**: Currently PDF is fully implemented. Excel and PowerPoint generators exist but may need refinement.

4. **File Storage**: Reports are stored in Django's FileField (typically `backend/reports/` directory).

5. **Preview Endpoint**: Separate endpoint for preview allows frontend to show data without generating full report.

6. **ZIP Download**: Bulk download feature creates ZIP file in memory for multiple reports.

## Future Enhancements

1. **Async Processing**: Move report generation to Celery tasks
2. **Email Delivery**: Send reports via email to recipients
3. **Custom Templates**: Allow users to create custom report templates
4. **Report Sharing**: Share reports via secure links
5. **Scheduled Execution**: Implement Celery beat for scheduled reports
6. **Report Caching**: Cache generated reports to avoid regeneration
7. **API Authentication**: Add service token auth for engine endpoints

## Database Schema

### report_templates
- id, name, description, sections (JSON), is_active, created_at, modified_at

### scheduled_reports
- id, organisation_id, domain_id, name, description, template_id
- frequency, schedule_day, schedule_time
- sections (JSON), formats (JSON), recipients (JSON)
- status, last_generated_at, next_run_at
- created_by_id, created_at, modified_at

### generated_reports
- id, scheduled_report_id (nullable), organisation_id, domain_id
- name, report_type, format, file_path, file_size, page_count
- data_period_start, data_period_end, generated_at
- generated_by_id, summary_data (JSON)

## Security Considerations

1. **Authentication**: All endpoints require `IsAuthenticated` permission
2. **Authorization**: Reports filtered by user's organisation
3. **Domain Validation**: Domain must belong to user's organisation
4. **File Access**: Download endpoints verify user has access to report
5. **Internal Endpoints**: `generate_by_id` allows unauthenticated access (TODO: Add service token)

## Testing

To test the reports module:

1. **Backend**: Use Django test client or API testing tools
2. **Frontend**: Test via browser at http://localhost:8080/reports
3. **Integration**: Test full flow from creation to generation to download

## Common Issues

1. **Missing Domain**: Reports require a selected domain
2. **File Not Found**: Generated reports may not have files if generation failed
3. **Large Reports**: Very large reports may timeout (consider async processing)
4. **Date Range**: Reports use date ranges; ensure data exists for selected period

