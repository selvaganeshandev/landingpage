# Track Status Usage in Prompt Processing

## 📊 **Overview**

The system uses `track_status` field in **TWO models** but **NOT in PromptAnalytics**:

| Model | Has `track_status`? | Used For |
|-------|-------------------|----------|
| **Domain** | ❌ No | Uses `processing_status` instead |
| **PromptGroup** | ✅ Yes | Track group processing lifecycle |
| **Prompt** | ✅ Yes | Track individual prompt processing |
| **PromptAnalytics** | ❌ **NOT USED** | Has field but never set/checked |

---

## 🔍 **Detailed Analysis**

### **1. PromptGroup.track_status** ✅ USED

**Purpose:** Track the processing lifecycle of a prompt group

**Status Values:**
- `INIT` - Initial state, ready for processing
- `SCHD` - Scheduled for processing
- `COMP` - Completed (all prompts processed)
- `FAIL` - Failed (critical error)

**Flow:**
```python
# In schedule_tick()
group.track_status = 'INIT'   # Created by domain_processor
      ↓
group.track_status = 'SCHD'   # Marked when scheduler picks it up
      ↓
# Process all prompts...
      ↓
group.track_status = 'COMP'   # When all prompts are done
```

**Usage in Code:**

```python
# Check if any group is in progress (line 77)
if PromptGroup.objects.filter(track_status='SCHD').exists():
    return  # Don't schedule another group

# Mark group as scheduled (line 97)
group.track_status = 'SCHD'
group.save()

# Mark group as complete (line 336)
group.track_status = 'COMP'
group.save()
```

---

### **2. Prompt.track_status** ✅ USED

**Purpose:** Track the processing lifecycle of individual prompts

**Status Values:**
- `INIT` - Initial state, not yet processed
- `SCHD` - Scheduled for processing
- `PROC` - Currently processing
- `COMP` - Completed successfully
- `FAIL` - Failed during processing

**Flow:**
```python
prompt.track_status = 'INIT'   # Created by domain_processor
      ↓
prompt.track_status = 'SCHD'   # Marked when scheduler picks it
      ↓
prompt.track_status = 'PROC'   # When process_single_prompt() starts
      ↓
prompt.track_status = 'COMP'   # When successfully completed
      or
prompt.track_status = 'FAIL'   # If error occurs
```

**Usage in Code:**

```python
# Mark as scheduled (line 129)
prompt.track_status = 'SCHD'
prompt.save()

# Mark as processing (line 181)
prompt.track_status = 'PROC'
prompt.save()

# Mark as completed (line 224)
prompt.track_status = 'COMP'
prompt.save()

# Mark as failed (line 243)
prompt.track_status = 'FAIL'
prompt.save()
```

---

### **3. PromptAnalytics.track_status** ❌ **NOT USED**

**Model Definition:**
```python
# In shared_models/models.py (line 402)
class PromptAnalytics(models.Model):
    track_status = models.CharField(
        max_length=50,
        default='INIT',
        help_text="Detailed tracking status of the analytics"
    )
```

**Reality:** This field **exists in the database** but is **NEVER used** in the code!

**Evidence:**

1. **NOT set when creating analytics** (line 279-294):
```python
analytics_obj, _ = PromptAnalytics.objects.update_or_create(
    prompt=prompt,
    platform=platform_label,
    defaults={
        'is_mention': ...,
        'total_mentions': ...,
        'sentiment_category': ...,
        # ❌ track_status is NOT set!
        'tracked_at': timezone.now(),
        'is_published': True,
    }
)
```

2. **Only checked in views for display** (line 349-352):
```python
# In views.py - only for showing status counts
platform_status[key] = {
    'pending': analytics.filter(platform=label, track_status='INIT').count(),
    'processing': analytics.filter(platform=label, track_status='PROC').count(),
    'completed': analytics.filter(platform=label, track_status='COMP').count(),
    'failed': analytics.filter(platform=label, track_status='FAIL').count(),
}
```

3. **Filtered in aggregation** (line 350):
```python
# Uses track_status='COMP' but this is always default 'INIT'!
domain_analytics = PromptAnalytics.objects.filter(
    prompt__domain=domain,
    track_status='COMP'  # ⚠️ This filter returns NOTHING!
)
```

---

## 🐛 **Problem: PromptAnalytics.track_status is Broken**

### **Current Behavior**

1. PromptAnalytics records are created with `track_status='INIT'` (default)
2. The field is **NEVER updated** to 'COMP'
3. Aggregation queries filter by `track_status='COMP'`
4. **Result:** Aggregation finds NO records! 💥

### **Example:**

```python
# PromptAnalytics created
analytics = PromptAnalytics.objects.create(
    prompt=prompt,
    platform='ChatGPT',
    # track_status defaults to 'INIT'
    # ❌ Never updated to 'COMP'
)

# Later, trying to aggregate...
completed_analytics = PromptAnalytics.objects.filter(
    track_status='COMP'  # ❌ Finds NOTHING because never updated!
)

# Aggregation is EMPTY!
```

---

## ✅ **Solution: Two Options**

### **Option 1: Use Prompt Status Instead (Recommended)**

Stop using `PromptAnalytics.track_status` entirely, use `Prompt.track_status` instead:

```python
# CURRENT (Broken)
domain_analytics = PromptAnalytics.objects.filter(
    prompt__domain=domain,
    track_status='COMP'  # ❌ Never finds anything
)

# FIXED
domain_analytics = PromptAnalytics.objects.filter(
    prompt__domain=domain,
    prompt__track_status='COMP'  # ✅ Uses Prompt status
)
```

**Why this works:**
- Prompt status IS properly maintained
- PromptAnalytics has 1-to-1 relationship with Prompt
- Can traverse the relationship: `prompt__track_status`

---

### **Option 2: Set PromptAnalytics Status (More Complex)**

Update the field when creating analytics:

```python
# In _create_analytics_record() - line 279
analytics_obj, _ = PromptAnalytics.objects.update_or_create(
    prompt=prompt,
    platform=platform_label,
    defaults={
        'is_mention': ...,
        'track_status': 'COMP',  # ✅ Add this
        'tracked_at': timezone.now(),
        'is_published': True,
    }
)
```

**Downside:** More fields to maintain, redundant with Prompt.track_status

---

## 🔧 **Recommended Fix**

Replace all `PromptAnalytics.objects.filter(track_status='COMP')` with `PromptAnalytics.objects.filter(prompt__track_status='COMP')`:

### **File: `engine/core/prompt_analytics_processor.py`**

**Line 316-318:**
```python
# BEFORE (Broken)
analytics = PromptAnalytics.objects.filter(
    prompt__group=group,
    track_status='COMP'  # ❌
)

# AFTER (Fixed)
analytics = PromptAnalytics.objects.filter(
    prompt__group=group,
    prompt__track_status='COMP'  # ✅
)
```

**Line 350:**
```python
# BEFORE (Broken)
domain_analytics = PromptAnalytics.objects.filter(
    prompt__domain=domain,
    track_status='COMP'  # ❌
)

# AFTER (Fixed)
domain_analytics = PromptAnalytics.objects.filter(
    prompt__domain=domain,
    prompt__track_status='COMP'  # ✅
)
```

---

## 📊 **Summary Table**

| Model | track_status | Status |
|-------|-------------|--------|
| **PromptGroup** | Has field ✅ | **Properly used** ✓ |
| **Prompt** | Has field ✅ | **Properly used** ✓ |
| **PromptAnalytics** | Has field ⚠️ | **NEVER updated, causing broken aggregation** ❌ |

---

## 🎯 **Status Flow Diagram**

```
Domain Processing:
  ↓
PromptGroup (track_status: INIT → SCHD → COMP)
  ↓ contains
Prompt (track_status: INIT → SCHD → PROC → COMP)
  ↓ generates
PromptAnalytics (track_status: INIT ... never changes ❌)
```

---

## 💡 **Best Practice**

**Use `Prompt.track_status` as the source of truth:**

```python
# ✅ CORRECT: Use Prompt status
completed_analytics = PromptAnalytics.objects.filter(
    prompt__track_status='COMP',
    is_published=True
)

# ❌ WRONG: Use PromptAnalytics status (never updated)
completed_analytics = PromptAnalytics.objects.filter(
    track_status='COMP'  # Always returns empty!
)
```

---

## 🚀 **Action Items**

1. **Fix aggregation queries** to use `prompt__track_status` instead of `track_status`
2. **Consider removing** `PromptAnalytics.track_status` field (not needed)
3. **Or update** the field when creating analytics if you want to use it

---

**Conclusion:** `track_status` is used in PromptGroup and Prompt, but the PromptAnalytics.track_status field is a **vestigial field** that exists but is never updated, causing aggregation to fail! 🐛

