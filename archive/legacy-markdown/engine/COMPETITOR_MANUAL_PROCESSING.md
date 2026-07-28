# Competitor Processing - Manual Only

## 📋 **Summary**

Competitor processing has been reverted to **manual-only** mode. Automatic processing via Celery scheduler has been removed.

---

## ✅ **Changes Made**

### **1. Removed Celery Beat Schedule**
- **File**: `engine/llm_monitor_engine/settings.py`
- **Change**: Removed `competitor-scheduler-every-15s` from `CELERY_BEAT_SCHEDULE`
- **Impact**: Competitors will no longer be automatically processed

### **2. Deprecated Automatic Scheduler Task**
- **File**: `engine/core/processing_tasks.py`
- **Change**: `process_competitor_scheduler` now returns a deprecation message
- **Impact**: Task still exists for backward compatibility but does nothing

### **3. Removed Auto-Extraction After Domain Completion**
- **File**: `engine/core/prompt_analytics_processor.py`
- **Change**: Removed automatic competitor extraction when domain status becomes `COMP`
- **Impact**: Competitors must be manually created and processed

### **4. Updated Documentation**
- **File**: `engine/core/competitor_processor.py`
- **Change**: Updated module docstring and `schedule_tick` method to reflect manual-only processing
- **Impact**: Code comments now clearly indicate manual processing requirement

---

## 🔧 **How to Process Competitors (Manual)**

### **Option 1: Via API Endpoint (Recommended)**

```bash
# Process a specific competitor
POST /api/competitors/{id}/process/
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8001/api/competitors/1/process/ \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "success": true,
  "message": "Processing started for competitor Nike",
  "competitor_id": 1,
  "track_status": "SCHD",
  "task_id": "abc123..."
}
```

### **Option 2: Via Frontend**

1. Navigate to the Competitors page
2. Click on a competitor
3. Click "Process" or "Start Analysis" button
4. Processing will run in the background via Celery task

### **Option 3: Synchronous Processing (API)**

```bash
# Process synchronously (no Celery)
POST /api/competitors/start-processing/
Body: {
  "competitor_id": 1,
  "sync": true
}
```

---

## 📊 **Processing Flow**

1. **User creates competitor** → `track_status = 'INIT'`
2. **User triggers processing** → `track_status = 'SCHD'` → `'PROC'` → `'COMP'`
3. **Processing steps:**
   - Links prompts to competitor (creates `CompetitorPromptAnalytics` records)
   - Extracts mentions from existing `PromptAnalytics.context_summary`
   - Aggregates analytics
   - Calculates share of voice
   - Updates competitor metrics

---

## 🚫 **What Was Removed**

1. ❌ **Automatic scheduler** - No more periodic processing
2. ❌ **Auto-extraction** - Competitors are not automatically discovered after domain completion
3. ❌ **Background processing queue** - All processing is user-initiated

---

## ✅ **What Remains**

1. ✅ **Manual processing endpoint** - `POST /api/competitors/{id}/process/`
2. ✅ **Synchronous processing** - `POST /api/competitors/start-processing/` with `sync=true`
3. ✅ **CompetitorProcessor class** - All processing logic intact
4. ✅ **All analytics features** - Share of voice, metrics, etc. still work
5. ✅ **Competitor extraction function** - `_extract_competitors_for_domain()` still available for manual use

---

## 🔄 **Migration Notes**

### **For Existing Competitors**

- Competitors with `track_status = 'INIT'` will **not** be automatically processed
- Users must manually trigger processing via API or frontend
- No data loss - all existing competitor data remains intact

### **For New Competitors**

- Create competitors manually via API or frontend
- Trigger processing manually after creation
- No automatic discovery or processing

---

## 📝 **API Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/competitors/{id}/process/` | **Trigger processing (async via Celery)** |
| POST | `/api/competitors/start-processing/` | **Trigger processing (sync or async)** |
| GET | `/api/competitors/{id}/analytics/` | Get detailed analytics |
| GET | `/api/competitors/` | List all competitors |
| POST | `/api/competitors/` | Create new competitor |

---

## ⚠️ **Important Notes**

1. **No Automatic Processing**: Competitors will **never** be processed automatically
2. **User Control**: Users have full control over when processing happens
3. **Celery Still Used**: Manual processing still uses Celery tasks for async execution (if `sync=false`)
4. **Status Flow**: `INIT → SCHD → PROC → COMP` (or `FAIL`) - same as before, just manual trigger

---

## 🎯 **Benefits of Manual Processing**

1. ✅ **User Control** - Users decide when to process
2. ✅ **Cost Control** - No unexpected API calls
3. ✅ **Resource Management** - Processing happens on-demand
4. ✅ **Transparency** - Users know exactly when processing occurs

---

## 📚 **Related Files**

- `engine/core/competitor_processor.py` - Main processing logic
- `engine/core/processing_tasks.py` - Celery tasks (manual only)
- `engine/core/views.py` - API endpoints
- `engine/llm_monitor_engine/settings.py` - Celery Beat configuration

---

**Last Updated**: Manual processing mode enabled
**Status**: ✅ Active

