# Quick Fix Guide - WeasyPrint PDF Implementation

## Problems Fixed

### 1. ✅ Serializer Not Accepting html_template/css_template
**Problem:** Backend serializer was ignoring the new fields
**Fix:** Added `html_template` and `css_template` to `ReportTemplateSerializer.fields`
**File:** `backend/reports/serializers.py:13`

### 2. ✅ Frontend Not Sending HTML Template to PDF Endpoint
**Problem:** ReportPreviewDialog was only sending `grid_rows`, not the saved `html_template`
**Fix:** Added `html_template` and `css_template` to PDF generation request
**File:** `frontend/src/components/ReportPreviewDialog.tsx:252-253`

---

## Complete Setup Steps

### Step 1: Install WeasyPrint System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfribidi0
```

**macOS:**
```bash
brew install pango
```

### Step 2: Install Python Package

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/backend
source .venv/bin/activate
pip install weasyprint==62.3
```

### Step 3: Run Database Migration

```bash
python manage.py migrate reports
```

Expected output:
```
Running migrations:
  Applying reports.0002_add_html_css_template_fields... OK
```

### Step 4: Verify Installation

```bash
python -c "from weasyprint import HTML; print('WeasyPrint OK')"
```

Should print: `WeasyPrint OK`

---

## Testing the Complete Flow

### Test 1: Create New Template

1. **Navigate to Report Builder**
   - Go to `/reports/builder`

2. **Build a Template**
   - Add some grids (double, triple, etc.)
   - Add widgets to slots (metrics, charts, tables)
   - Give it a name: "Test WeasyPrint Template"

3. **Save Template**
   - Click "Save Template"
   - Check browser Network tab
   - Verify payload includes `html_template` and `css_template` fields

4. **Verify in Database**
   ```bash
   python manage.py shell
   ```
   ```python
   from reports.models import ReportTemplate
   t = ReportTemplate.objects.filter(template_type='custom').last()
   print(f"HTML Template length: {len(t.html_template) if t.html_template else 0}")
   print(f"CSS Template length: {len(t.css_template) if t.css_template else 0}")
   ```

   Should show non-zero lengths.

### Test 2: Generate PDF

1. **Open Template Preview**
   - Go to Reports page
   - Click on your saved template
   - Click "PDF" button

2. **Check Network Request**
   - Open browser DevTools → Network tab
   - Look for POST to `/reports/generate-custom-pdf/`
   - Verify request includes:
     - `html_template`: "..."
     - `css_template`: "..."
     - `grid_rows`: [...]

3. **Check Backend Logs**
   ```bash
   tail -f backend/logs/debug.log  # or wherever logs are
   ```

   Should see:
   ```
   Using WeasyPrint for PDF generation (HTML template provided)
   ```

4. **Verify PDF Output**
   - PDF downloads
   - Open PDF
   - Compare to frontend preview
   - Should have:
     - ✅ Colored backgrounds (blue, green, purple, orange)
     - ✅ Proper fonts and sizes
     - ✅ Charts and tables
     - ✅ Layout matching preview

### Test 3: Fallback to ReportLab

To test fallback when html_template is missing:

```python
# In Django shell
from reports.models import ReportTemplate
t = ReportTemplate.objects.get(name='Test WeasyPrint Template')
t.html_template = None
t.save()
```

Generate PDF again - should use ReportLab (basic style).

---

## Debugging Common Issues

### Issue: "ImportError: WeasyPrint is not installed"

**Cause:** WeasyPrint not in virtual environment

**Fix:**
```bash
source .venv/bin/activate
pip install weasyprint==62.3
```

### Issue: "OSError: cannot load library 'gobject-2.0-0'"

**Cause:** Missing system dependencies

**Fix (Ubuntu):**
```bash
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
```

### Issue: html_template field is NULL/empty

**Symptoms:**
- Backend logs show "Using ReportLab" instead of "Using WeasyPrint"
- PDF looks basic (no colors/gradients)

**Diagnosis:**
```python
from reports.models import ReportTemplate
t = ReportTemplate.objects.filter(template_type='custom').last()
print(t.html_template)  # Should not be None
```

**Causes:**
1. Template was created before adding html_template fields
2. Frontend didn't send html_template when saving
3. Serializer didn't accept the field

**Fix:**
- Re-save template from frontend (after fixes)
- Verify serializer includes fields (check `serializers.py:13`)

### Issue: PDF still looks basic (like old ReportLab)

**Symptoms:**
- No gradients
- Basic colors only
- Charts are simple

**Diagnosis:**
1. Check backend logs - should say "Using WeasyPrint"
2. If says "Using ReportLab", check why fallback occurred
3. Check if `html_template` is being sent in request

**Debug Request:**
```python
# Add to views.py generate_custom_template_pdf():
print(f"html_template received: {len(html_template) if html_template else 0} chars")
print(f"css_template received: {len(css_template) if css_template else 0} chars")
```

### Issue: Placeholders not replaced ({{widget-id.value}} in PDF)

**Cause:** Widget data not matching placeholder IDs

**Fix:**
1. Check widget IDs in saved template
2. Verify WidgetDataFetcher is returning data for those IDs
3. Add logging to `html_template_renderer.py`:

```python
# In _replace_widget_placeholders():
print(f"Replacing placeholders for widget: {widget_id}")
print(f"Data: {data}")
```

---

## File Changes Summary

All files modified and their purposes:

### Backend:
1. ✅ `models.py` - Added html_template, css_template fields
2. ✅ `serializers.py` - Added fields to serializer (FIXED)
3. ✅ `migrations/0002_*.py` - Database migration
4. ✅ `services/html_template_renderer.py` - NEW: Placeholder injection
5. ✅ `services/weasyprint_pdf_generator.py` - NEW: PDF generation
6. ✅ `views.py` - Updated to use WeasyPrint
7. ✅ `requirements.txt` - Added weasyprint==62.3

### Frontend:
1. ✅ `utils/htmlTemplateCapture.ts` - NEW: HTML capture utility
2. ✅ `pages/ReportBuilder.tsx` - Captures HTML when saving
3. ✅ `components/ReportPreviewDialog.tsx` - Sends HTML to backend (FIXED)

---

## Expected Behavior After Fixes

### When Saving Template:
```
Frontend → Backend
POST /reports/templates/
{
  "name": "My Template",
  "grid_rows": [...],
  "html_template": "<div class='bg-gradient-to-br from-blue-500/10'>...</div>",
  "css_template": ".text-blue-600 { color: #2563eb; } ..."
}
```

### When Generating PDF:
```
Frontend → Backend
POST /reports/generate-custom-pdf/
{
  "domain_id": 1,
  "template_name": "My Template",
  "grid_rows": [...],
  "html_template": "<div>{{total-prompts-metric.value}}</div>",  // With placeholders
  "css_template": "..."
}

Backend:
1. Fetches real widget data
2. Injects into html_template (replaces {{...}})
3. WeasyPrint converts HTML → PDF
4. Returns PDF with exact styling
```

---

## Success Criteria

✅ **Template saves with html_template populated**
✅ **Backend logs show "Using WeasyPrint"**
✅ **PDF has colored backgrounds (blue, green, purple, orange)**
✅ **PDF fonts and sizes match frontend**
✅ **PDF layout matches preview exactly**
✅ **Charts render properly**
✅ **No placeholder text ({{...}}) visible in PDF**

---

## Next Steps After Testing

If everything works:

1. **Test with multiple widget types**
   - Metrics with different colors
   - Various chart types
   - Tables with data

2. **Test edge cases**
   - Empty widgets
   - Missing data
   - Long text values
   - Special characters

3. **Performance testing**
   - Large templates (10+ widgets)
   - Measure generation time
   - Should be < 5 seconds

4. **Update existing templates**
   - Re-save old templates to populate html_template
   - Or create migration to generate HTML from grid_rows

---

## Rollback Plan (If Needed)

If you need to rollback:

```bash
# Revert migration
python manage.py migrate reports 0001

# Remove WeasyPrint
pip uninstall weasyprint

# Git revert changes
git checkout -- backend/reports/serializers.py
git checkout -- frontend/src/components/ReportPreviewDialog.tsx
```

---

## Support

If issues persist:
1. Check all files were updated correctly
2. Restart Django server
3. Clear browser cache
4. Check backend logs for errors
5. Verify WeasyPrint installation with test command

The implementation is solid - just needed these two fixes! 🎉
