# Final Test Steps - WeasyPrint PDF with Exact Styling

## What Was Fixed

### Issues Identified from Screenshots:
1. ❌ PDF had plain white/gray boxes (no gradients)
2. ❌ PDF had black text (not colored like UI: purple/blue)
3. ❌ No growth indicators visible
4. ❌ Basic styling (didn't match beautiful UI preview)

### Fixes Applied:

1. **HTML Template Generator** (`htmlTemplateCapture.ts`)
   - Now uses REAL RGB color values for gradients
   - Purple for platform metrics: `rgba(139, 92, 246, 0.1)`
   - Blue for mention metrics: `rgba(59, 130, 246, 0.1)`
   - Green for sentiment: `rgba(34, 197, 94, 0.1)`
   - Orange for share/voice: `rgba(249, 115, 22, 0.1)`
   - Uses inline styles (CSS gradients work in WeasyPrint!)

2. **Placeholder Renderer** (`html_template_renderer.py`)
   - Growth color now uses inline style instead of CSS class
   - Green for positive: `color: #16a34a;`
   - Red for negative: `color: #dc2626;`

3. **Serializer Fix** (`serializers.py`)
   - Added `html_template` and `css_template` to fields

4. **Preview Dialog Fix** (`ReportPreviewDialog.tsx`)
   - Now sends `html_template` and `css_template` to backend

---

## Complete Test Procedure

### Step 1: Install & Migrate (One-time Setup)

```bash
# 1. Install WeasyPrint
cd backend
source .venv/bin/activate
pip install weasyprint==62.3

# 2. Run migration
python manage.py migrate reports

# 3. Verify WeasyPrint works
python -c "from weasyprint import HTML; print('✓ WeasyPrint OK')"
```

### Step 2: Create NEW Template (IMPORTANT!)

**Why?** Old templates don't have the new HTML with gradients.

1. Go to Report Builder: `http://localhost:8080/reports/builder`

2. Create a new template:
   - Name: "Test Styled PDF"
   - Add **Double** grid
   - Add these two widgets:
     - Slot 1: "Total Platforms Tracked" (should have purple styling in preview)
     - Slot 2: "Total Platform Mentions" (should have blue styling in preview)

3. **Before saving**, verify in browser preview:
   - Left widget should have **light purple background**
   - Right widget should have **light blue background**
   - Numbers should be **colored** (purple "5", blue "2,847")
   - Should show growth indicators ("+15.3%")

4. Click **"Save Template"**

5. **Verify payload in Network tab:**
   - Open DevTools → Network
   - Filter: `templates`
   - Look at Request Payload
   - Should include:
     ```json
     {
       "html_template": "<div ... linear-gradient ... rgba(139, 92, 246 ...",
       "css_template": "..."
     }
     ```

### Step 3: Generate PDF

1. Go to Reports page
2. Find "Test Styled PDF" template
3. Click **"PDF"** button

4. **Check Network Request:**
   - DevTools → Network → `generate-custom-pdf`
   - Verify payload includes:
     ```json
     {
       "html_template": "...linear-gradient...",
       "css_template": "..."
     }
     ```

5. **Check Backend Logs:**
   ```bash
   # In another terminal
   cd backend
   tail -f logs/app.log  # or wherever logs are
   ```

   Should see:
   ```
   Using WeasyPrint for PDF generation (HTML template provided)
   ```

   If you see "Using ReportLab" → html_template is empty/null → something is wrong

### Step 4: Verify PDF Output

1. PDF downloads automatically
2. Open the PDF file
3. Compare with UI screenshot

**Expected in PDF:**
- ✅ **Light purple gradient background** on "Total Platforms Tracked"
- ✅ **Light blue gradient background** on "Total Platform Mentions"
- ✅ **Purple "5"** text (not black!)
- ✅ **Blue "2,847"** text (not black!)
- ✅ **Green "+15.3%"** growth text
- ✅ **Upward arrow ▲** visible
- ✅ Rounded corners on cards
- ✅ Proper spacing and fonts

---

## Debugging If PDF Still Looks Basic

### Check 1: Is html_template being saved?

```python
# Django shell
python manage.py shell

from reports.models import ReportTemplate
t = ReportTemplate.objects.filter(name='Test Styled PDF').first()

print(f"HTML template length: {len(t.html_template) if t.html_template else 0}")
print("\nFirst 500 chars:")
print(t.html_template[:500] if t.html_template else "NULL")

# Look for "linear-gradient" in the HTML
if t.html_template and 'linear-gradient' in t.html_template:
    print("\n✓ HTML has gradients!")
else:
    print("\n✗ HTML missing gradients - frontend not generating correctly")
```

### Check 2: Is html_template being sent to PDF endpoint?

Add debug logging to `views.py`:

```python
# In generate_custom_template_pdf() function, around line 595
html_template = request.data.get('html_template')
css_template = request.data.get('css_template', '')

# ADD THIS:
logger.info(f"=== PDF Generation Debug ===")
logger.info(f"html_template length: {len(html_template) if html_template else 0}")
logger.info(f"css_template length: {len(css_template) if css_template else 0}")
if html_template:
    logger.info(f"Has gradients: {'linear-gradient' in html_template}")
```

### Check 3: Is WeasyPrint actually being used?

Look for this in logs:
```
Using WeasyPrint for PDF generation (HTML template provided)
```

If you see:
```
Using ReportLab for PDF generation
```

Then `html_template` is None/empty → Check frontend is sending it

### Check 4: View generated HTML before PDF conversion

Add to `weasyprint_pdf_generator.py`:

```python
# In generate() method, after inject_widget_data:
complete_html = inject_widget_data(...)

# ADD THIS:
with open('/tmp/debug_template.html', 'w') as f:
    f.write(complete_html)
logger.info("Debug HTML saved to /tmp/debug_template.html")
```

Then open `/tmp/debug_template.html` in browser - should look exactly like UI

---

## Expected Color Values in HTML

After generation, the HTML should contain:

**For Platform widget (purple):**
```html
<div style="
  background: linear-gradient(to bottom right, rgba(139, 92, 246, 0.1), rgba(139, 92, 246, 0.05));
  border: 1px solid #e9d5ff;
  ...
">
  <p style="color: #9ca3af;">Total Platforms Tracked</p>
  <p style="color: #9333ea;">5</p>
  <p><span style="color: #16a34a;">+15.3%</span></p>
</div>
```

**For Mentions widget (blue):**
```html
<div style="
  background: linear-gradient(to bottom right, rgba(59, 130, 246, 0.1), rgba(59, 130, 246, 0.05));
  border: 1px solid #bfdbfe;
  ...
">
  <p style="color: #9ca3af;">Total Platform Mentions</p>
  <p style="color: #2563eb;">2,847</p>
  <p><span style="color: #16a34a;">+15.3%</span></p>
</div>
```

---

## Common Issues & Solutions

### Issue: PDF still black & white

**Cause:** html_template is NULL or empty

**Solution:**
1. Delete old template
2. Create NEW template (after fixes)
3. Verify html_template saved in database

### Issue: "WeasyPrint not found"

**Cause:** Not installed in virtual environment

**Solution:**
```bash
source .venv/bin/activate
pip install weasyprint==62.3
```

### Issue: Gradients not rendering in PDF

**Cause:** WeasyPrint not enabled or CSS not inline

**Solution:**
- Verify "Using WeasyPrint" in logs
- Check HTML has inline styles (not classes)
- Gradients must be in `style="..."` not CSS classes

### Issue: "Using ReportLab" in logs (fallback)

**Causes:**
1. `html_template` is None/empty in request
2. WeasyPrint import failed
3. Exception during WeasyPrint generation

**Debug:**
```python
# Add to views.py
if html_template:
    logger.info(f"✓ HTML template received: {len(html_template)} chars")
else:
    logger.warning("✗ html_template is None/empty - will use ReportLab fallback")
```

---

## Success Criteria

✅ Backend logs show: **"Using WeasyPrint for PDF generation"**
✅ PDF has **colored backgrounds** (purple, blue, green, orange)
✅ PDF has **colored text** matching UI (not black!)
✅ PDF has **gradients** (light backgrounds)
✅ PDF has **growth indicators** (▲ with green %)
✅ PDF looks **EXACTLY** like UI preview

---

## Quick Visual Comparison

**UI Preview:**
- Light purple card with gradient
- Purple "5" in large font
- "Active platforms" in gray
- "+15.3% across all platforms" in green with ▲

**PDF (Expected):**
- ✅ Same light purple gradient background
- ✅ Same purple "5"
- ✅ Same gray subtitle
- ✅ Same green growth with ▲

**PDF (Before Fix - BAD):**
- ❌ Plain white/gray background
- ❌ Black text
- ❌ No growth visible
- ❌ Boring basic style

---

## After Testing

If PDF matches UI:
1. 🎉 **Success!** WeasyPrint is working
2. Update all existing templates (re-save them)
3. Test with more widget types
4. Test with charts and tables

If PDF still doesn't match:
1. Share screenshots
2. Share backend logs
3. Share browser Network tab (request payload)
4. Check database (html_template content)

---

The fix is complete - just need to test with a NEW template! 🚀
