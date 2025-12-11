# Real Data PDF Integration Summary

## Problem Identified

The frontend was generating PDFs using `html2canvas` + `jsPDF`, which:
- Converted the UI/DOM directly to an image-based PDF
- Used **dummy/preview data** for widgets
- Did NOT call the backend's `WidgetDataFetcher` system
- Result: Users saw beautiful PDFs with fake data

## Solution Implemented

Created a direct backend PDF generation flow that:
1. Sends template configuration to backend
2. Backend fetches **real database data** using `WidgetDataFetcher`
3. Backend generates PDF with ReportLab
4. Returns professional PDF with actual metrics

---

## Changes Made

### 1. Backend: New API Endpoint

**File:** `backend/reports/views.py`

Added `generate_custom_template_pdf()` function (lines 581-694):

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_custom_template_pdf(request):
    """
    Generate PDF directly from custom template data without saving
    Accepts: domain_id, template_name, grid_rows, start_date, end_date
    Returns: PDF file with real widget data
    """
```

**What it does:**
1. Accepts template configuration from frontend
2. Validates domain ownership
3. Parses date range (defaults to last 30 days)
4. Uses `WidgetDataFetcher` to fetch real data for all widgets
5. Creates mock template object for PDF generator
6. Generates PDF using `PDFReportGenerator`
7. Returns PDF file as HTTP response

**Key Features:**
- ✅ No database save required (direct generation)
- ✅ Real-time data fetching
- ✅ Date range support
- ✅ Authentication and authorization checks
- ✅ Full error handling and logging

### 2. Backend: URL Route

**File:** `backend/reports/urls.py`

Added new URL pattern:
```python
path('generate-custom-pdf/', generate_custom_template_pdf, name='generate-custom-template-pdf'),
```

**Endpoint:** `POST /reports/generate-custom-pdf/`

### 3. Frontend: Smart PDF Download Handler

**File:** `frontend/src/components/ReportPreviewDialog.tsx`

Modified `handleDownloadPdf()` to detect template type:

```typescript
const handleDownloadPdf = async () => {
  // Check if this is a custom template with widgets
  if (report.template_type === 'custom' && report.grid_rows) {
    // Use backend API for custom templates with real data
    await handleDownloadCustomTemplatePdf();
  } else {
    // Use html2canvas for predefined templates (legacy)
    await handleDownloadHtmlPdf();
  }
};
```

**Added two new functions:**

1. **`handleDownloadCustomTemplatePdf()`** - Backend API call
   - Sends template data to backend
   - Receives real PDF with database data
   - Downloads file to user's device
   - Shows success toast with "PDF with real data downloaded"

2. **`handleDownloadHtmlPdf()`** - Legacy html2canvas method
   - Keeps existing functionality for predefined templates
   - Uses html2canvas + jsPDF
   - Maintains backward compatibility

---

## How It Works

### Data Flow

```
User clicks "Download PDF" in Report Preview
    ↓
Frontend: ReportPreviewDialog.handleDownloadPdf()
    ↓
Check: Is this a custom template?
    ↓
YES: Call handleDownloadCustomTemplatePdf()
    ├─ Prepare request:
    │   {
    │     domain_id: selectedDomain.id,
    │     template_name: report.name,
    │     grid_rows: report.grid_rows,
    │     start_date: "2025-11-10",
    │     end_date: "2025-12-10"
    │   }
    ├─ POST to /reports/generate-custom-pdf/
    └─ Backend receives request
        ↓
Backend: generate_custom_template_pdf()
    ├─ Validate domain ownership
    ├─ Parse date range
    ├─ Create WidgetDataFetcher instance
    ├─ Loop through grid_rows
    │   ├─ For each widget, call fetch_widget_data(widget_id)
    │   ├─ Query database (Prompts, Analytics, Topics, etc.)
    │   ├─ Calculate metrics, growth, trends
    │   └─ Return structured data dict
    ├─ Add metadata (domain, dates, template info)
    ├─ Create mock template object
    ├─ Pass to PDFReportGenerator
    │   ├─ _generate_custom_template()
    │   ├─ Render header with domain info
    │   ├─ Loop through grid_rows
    │   │   ├─ Render metrics with real values
    │   │   ├─ Render charts with real data points
    │   │   └─ Render tables with real records
    │   └─ Build PDF with ReportLab
    └─ Return PDF buffer
        ↓
Backend sends PDF file to frontend
    ↓
Frontend downloads file
    ↓
User gets PDF with REAL DATA! 🎉
```

---

## Request/Response Format

### Request to Backend

```json
{
  "domain_id": 1,
  "template_name": "My Custom Dashboard",
  "grid_rows": [
    {
      "id": "row-1",
      "type": "triple",
      "slots": [
        { "id": "total-prompts-metric", "title": "Total Prompts", "category": "prompts" },
        { "id": "total-citations-metric", "title": "Total Citations", "category": "citations" },
        { "id": "share-metric", "title": "Share of Voice", "category": "share-of-voice" }
      ]
    },
    {
      "id": "row-2",
      "type": "single",
      "slots": [
        { "id": "mentions-chart", "title": "Mentions Over Time", "category": "historical-trends" }
      ]
    }
  ],
  "start_date": "2025-11-10",
  "end_date": "2025-12-10"
}
```

### Response from Backend

- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="My_Custom_Dashboard_20251210_143022.pdf"`
- **Body:** Binary PDF file

---

## Benefits

### ✅ Real Data
- All metrics show actual database values
- Charts display real data points
- Tables contain real records
- Growth calculations use real previous period data

### ✅ Professional Quality
- ReportLab-generated PDFs (not screenshots)
- Proper text rendering (selectable, searchable)
- Vector graphics for charts
- Consistent formatting and styling

### ✅ No Template Save Required
- Users can experiment with widgets
- Download PDFs without committing to a template
- Quick iterations and testing

### ✅ Backward Compatible
- Predefined templates still use html2canvas (unchanged)
- Only custom templates use the new backend flow
- No breaking changes to existing functionality

### ✅ Date Range Support
- Defaults to last 30 days
- Frontend can specify custom date ranges
- Backend validates and applies filters

---

## Testing Checklist

To test the new functionality:

### 1. ✅ Create Custom Template
- Go to `/reports/create-template`
- Add widgets from different categories
- Save template or just keep in memory

### 2. ✅ Preview Template
- Click "Preview" button
- Verify widgets show dummy data in preview (as expected)

### 3. ✅ Download PDF with Real Data
- Click "Download PDF" button in preview dialog
- **Expected:**
  - Loading spinner appears
  - Backend generates PDF (may take 5-15 seconds)
  - PDF downloads automatically
  - Toast message: "PDF with real data downloaded successfully"

### 4. ✅ Verify PDF Content
- Open downloaded PDF
- Check metrics show real values (not dummy data)
- Check charts have real data points
- Check tables contain actual records
- Verify header shows domain name and date range
- Ensure text is selectable (not an image)

### 5. ✅ Test Different Scenarios
- Template with only metrics
- Template with only charts
- Template with mixed widgets
- Template with tables
- Empty date range (should use default 30 days)

---

## Known Limitations

1. **Synchronous Generation**
   - PDF generation is blocking (user must wait)
   - For large date ranges or many widgets, this can take 10-20 seconds
   - Future: Could be moved to async Celery task

2. **No Progress Indicator**
   - User only sees loading spinner
   - No indication of which widgets are being processed
   - Future: Could add websocket for progress updates

3. **Default Date Range**
   - Currently hardcoded to last 30 days
   - Frontend doesn't expose date range picker yet
   - Future: Add date range selector in preview dialog

4. **No Caching**
   - Every download regenerates the PDF from scratch
   - Widget data is fetched fresh each time
   - Future: Could cache widget data for repeated downloads

5. **No Preview of Real Data**
   - Preview still shows dummy data
   - Only downloaded PDF has real data
   - Future: Could add "Load Real Data" button in preview

---

## API Documentation

### POST /reports/generate-custom-pdf/

Generate a PDF report with real data from a custom template.

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "domain_id": 1,                    // Required: Domain ID
  "template_name": "string",         // Optional: Template name (default: "Custom Report")
  "grid_rows": [...],                // Required: Array of grid row objects with widgets
  "start_date": "YYYY-MM-DD",        // Optional: Start date (default: 30 days ago)
  "end_date": "YYYY-MM-DD"           // Optional: End date (default: today)
}
```

**Success Response:**
- **Code:** 200 OK
- **Content-Type:** application/pdf
- **Body:** Binary PDF file

**Error Responses:**

- **400 Bad Request**
  - Missing domain_id
  - Missing grid_rows
  - Invalid date format

- **404 Not Found**
  - Domain not found
  - Domain doesn't belong to user's organisation

- **500 Internal Server Error**
  - Database query error
  - PDF generation error
  - Widget data fetching error

**Example using cURL:**
```bash
curl -X POST http://localhost:8000/reports/generate-custom-pdf/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_id": 1,
    "template_name": "Q4 Performance Report",
    "grid_rows": [...],
    "start_date": "2025-10-01",
    "end_date": "2025-12-31"
  }' \
  --output report.pdf
```

**Example using JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/reports/generate-custom-pdf/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    domain_id: 1,
    template_name: 'My Report',
    grid_rows: [...],
    start_date: '2025-11-01',
    end_date: '2025-12-01',
  }),
});

const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'report.pdf';
a.click();
```

---

## Files Modified

### Backend
1. **`backend/reports/views.py`**
   - Added `generate_custom_template_pdf()` function (114 lines)
   - Imports: WidgetDataFetcher, PDFReportGenerator

2. **`backend/reports/urls.py`**
   - Added import: `generate_custom_template_pdf`
   - Added URL pattern: `generate-custom-pdf/`

### Frontend
3. **`frontend/src/components/ReportPreviewDialog.tsx`**
   - Modified `handleDownloadPdf()` to detect custom templates
   - Added `handleDownloadCustomTemplatePdf()` (56 lines)
   - Renamed old function to `handleDownloadHtmlPdf()` (78 lines)

---

## Comparison: Before vs After

### Before (Client-Side PDF)
```
User clicks Download
    ↓
html2canvas captures DOM screenshot
    ↓
jsPDF converts image to PDF
    ↓
PDF downloaded with dummy data
❌ Dummy data only
❌ Image-based PDF (low quality)
❌ Large file size
❌ Text not selectable
✅ Fast generation (2-3 seconds)
```

### After (Server-Side PDF)
```
User clicks Download
    ↓
Frontend sends template to backend
    ↓
Backend fetches real database data
    ↓
Backend generates PDF with ReportLab
    ↓
PDF downloaded with real data
✅ Real database data
✅ Vector-based PDF (high quality)
✅ Smaller file size
✅ Text selectable and searchable
⚠️ Slower generation (5-15 seconds)
```

---

## Next Steps (Optional Enhancements)

1. **Add Date Range Picker in Preview Dialog**
   - Let users select custom date ranges
   - Show date range in preview header
   - Pass to backend when generating PDF

2. **Async Generation with Celery**
   - Move PDF generation to background task
   - Show progress bar or notifications
   - Send email when PDF is ready

3. **Real Data Preview**
   - Add "Load Real Data" button in preview
   - Fetch widget data via API
   - Update preview with actual values

4. **PDF Caching**
   - Cache generated PDFs for repeat downloads
   - Invalidate cache when data changes
   - Show "Generated X minutes ago" badge

5. **Batch Download**
   - Select multiple templates
   - Download all as ZIP file
   - Use async generation for multiple PDFs

6. **Custom Branding**
   - Add organisation logo to PDF
   - Custom color schemes
   - Custom footer text

7. **Scheduled PDF Generation**
   - Create scheduled reports with custom templates
   - Auto-send PDFs via email
   - Store in report history

---

## Summary

Successfully integrated the backend `WidgetDataFetcher` system with the frontend PDF download functionality. Users can now:

1. ✅ Create custom templates with 40+ widgets
2. ✅ Preview templates with dummy data
3. ✅ Download PDFs with **real database metrics**
4. ✅ Get professional ReportLab-generated PDFs
5. ✅ No template save required for quick testing

The system now provides a complete end-to-end flow from widget selection to real-data PDF generation! 🚀
