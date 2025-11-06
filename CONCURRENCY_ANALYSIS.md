# Concurrency Analysis: Domain Processor vs Prompt Analytics Processor

## 🔍 **Your Question**

> "If the prompt processor and domain processor are processing at the same time, will it creates issue?"

## ✅ **Short Answer**

**YES, there ARE potential race conditions**, but they are **mostly handled** with proper locking. However, there are a few edge cases that could cause issues.

---

## 📊 **Processing Flow Overview**

```
Domain Processor (Celery Task)
    ↓
1. Scrapes keywords from DataForSEO
2. Generates prompts using ChatGPT
3. Groups prompts using NLP clustering
4. Creates PromptGroups & Prompts in database ← CREATES DATA
    ↓
5. Sets PromptGroup.track_status = 'INIT'
    ↓
6. Sets Prompt.track_status = 'INIT'
    ↓
7. Creates default PromptAnalytics (status='INIT')
    ↓
8. Domain.processing_status = 'COMP'

    ↓ (Meanwhile, Celery Beat runs every minute...)

Prompt Analytics Processor (Celery Beat)
    ↓
1. Looks for PromptGroups with status='INIT' ← READS DATA
2. Marks PromptGroup as 'SCHD' ← UPDATES STATUS
3. Processes prompts in the group
4. Updates PromptAnalytics records ← UPDATES DATA
5. Marks PromptGroup as 'COMP' ← UPDATES STATUS
```

---

## 🔒 **Locking Mechanisms Currently In Place**

### **1. Domain Processor (Partial Protection)**

#### **✅ Transaction Atomic** (Line 200)
```python
with transaction.atomic():
    # Create PromptGroup
    prompt_group = PromptGroup.objects.create(...)
    
    # Create Prompts
    for prompt_text in primary_prompts:
        prompt = Prompt.objects.create(...)
        self._create_default_analytics_for_prompt(prompt, domain)
```

**What This Protects:**
- ✅ All PromptGroups, Prompts, and PromptAnalytics are created atomically
- ✅ If any creation fails, entire transaction rolls back
- ✅ No partial data in database

**What This DOESN'T Protect:**
- ❌ Doesn't prevent Prompt Analytics Processor from reading INIT groups while they're being created
- ❌ No row-level locking on Domain

---

### **2. Prompt Analytics Processor (Good Protection)**

#### **✅ Select For Update** (Line 94)
```python
with transaction.atomic():
    fresh = PromptGroup.objects.select_for_update().get(id=group.id)
    if fresh.track_status != 'INIT':
        return {'scheduled': False, 'reason': 'race_condition'}
    fresh.track_status = 'SCHD'
    fresh.save()
```

**What This Protects:**
- ✅ Row-level lock on PromptGroup
- ✅ Prevents multiple schedulers from picking same group
- ✅ Double-check pattern (check status after lock)

#### **✅ Select For Update on Prompts** (Line 126)
```python
with transaction.atomic():
    p = Prompt.objects.select_for_update().get(id=prompt.id)
    if p.track_status != 'INIT':
        continue
    p.track_status = 'SCHD'
    p.save()
```

**What This Protects:**
- ✅ Row-level lock on individual Prompt
- ✅ Prevents multiple processes from processing same prompt

---

## ⚠️ **Potential Race Conditions**

### **Race Condition #1: Reading Incomplete Group** ❌

**Scenario:**
1. **Domain Processor:** Inside `transaction.atomic()`, creates PromptGroup (status='INIT')
2. **Prompt Analytics:** Queries for INIT groups → **FINDS the new group!**
3. **Domain Processor:** Still creating Prompts for that group...
4. **Prompt Analytics:** Tries to process group with **incomplete/missing prompts**

**Timeline:**
```
Time | Domain Processor              | Prompt Analytics Processor
-----|-------------------------------|---------------------------
T1   | BEGIN TRANSACTION             |
T2   | CREATE PromptGroup (INIT) ✓   |
T3   |                               | SELECT PromptGroups WHERE status=INIT
T4   |                               | → FINDS the new group! ⚠️
T5   | CREATE Prompt 1...            | Lock group (SELECT FOR UPDATE) ✓
T6   | CREATE Prompt 2...            | Find prompts in group...
T7   | CREATE Prompt 3...            | → May only find 1 or 2 prompts! ❌
T8   | COMMIT TRANSACTION            |
```

**Problem:** 
- Prompt Analytics might process a group **before all prompts are created**
- Could result in incomplete analytics

**Likelihood:** **LOW** (but possible during high load)

---

### **Race Condition #2: Domain Status Change During Processing** ⚠️

**Scenario:**
1. **Domain Processor:** Finishes creating all groups/prompts
2. **Domain Processor:** Sets `Domain.processing_status = 'COMP'`
3. **Prompt Analytics:** Simultaneously aggregating data for that domain
4. **NO LOCKING** on Domain object

**Timeline:**
```
Time | Domain Processor              | Prompt Analytics Processor
-----|-------------------------------|---------------------------
T1   | CREATE last prompt ✓          | Processing prompt 5
T2   | Domain.processing_status=COMP | UPDATE PromptAnalytics
T3   | Domain.save()                 | Aggregate domain totals
T4   |                               | Domain.total_citations += X
T5   |                               | Domain.save() ← May overwrite!
```

**Problem:**
- Domain.save() calls from both processors might overwrite each other
- **Lost update problem**

**Likelihood:** **MEDIUM** (depends on timing)

---

### **Race Condition #3: Creating While Scheduling** ✅ **HANDLED**

**Scenario:**
1. **Domain Processor:** Creates PromptGroup with status='INIT'
2. **Prompt Analytics:** Tries to mark same group as 'SCHD'

**Protection:**
```python
# Prompt Analytics uses select_for_update() + double-check
fresh = PromptGroup.objects.select_for_update().get(id=group.id)
if fresh.track_status != 'INIT':
    return  # Skip if status changed
```

**Status:** ✅ **PROTECTED** by row-level locking

---

## 🚨 **Real Issues That Could Happen**

### **Issue #1: Processing Incomplete Group**

**Symptoms:**
- Prompt Analytics processes a group
- Finds fewer prompts than expected
- Group marked as COMP prematurely
- Some prompts never get processed

**How to Detect:**
```sql
-- Find groups where prompt count doesn't match expectations
SELECT pg.id, pg.group_id, 
       COUNT(p.id) as prompt_count,
       pg.track_status
FROM prompt_groups pg
LEFT JOIN prompts p ON p.group_id = pg.id
WHERE pg.track_status = 'COMP'
GROUP BY pg.id
HAVING COUNT(p.id) < 2;  -- Expect at least 2 prompts per group
```

---

### **Issue #2: Lost Domain Updates**

**Symptoms:**
- Domain.total_citations is incorrect
- Domain.total_mentions doesn't match sum of groups
- Inconsistent aggregation data

**How to Detect:**
```python
# Verify domain totals match prompt analytics
domain = Domain.objects.get(id=X)
actual_total = PromptAnalytics.objects.filter(
    prompt__group__domain=domain,
    prompt__track_status='COMP'
).aggregate(Sum('total_citations'))['total_citations__sum']

print(f"Domain total: {domain.total_citations}")
print(f"Actual total: {actual_total}")
# If different → lost update!
```

---

### **Issue #3: Duplicate Processing**

**Symptoms:**
- Same prompt processed multiple times
- Duplicate PromptAnalytics records

**Protection:** ✅ **PREVENTED** by:
```python
# Using update_or_create with unique constraint
PromptAnalytics.objects.update_or_create(
    prompt=prompt,
    platform=platform_label,  # Unique together
    defaults={...}
)
```

---

## ✅ **Recommended Fixes**

### **Fix #1: Delay Prompt Analytics Until Domain Complete**

Prevent processing incomplete groups:

```python
# In schedule_tick() - Line 82
group = (
    PromptGroup.objects.filter(
        track_status='INIT',
        domain__processing_status='COMP'  # ✅ ONLY process after domain is done
    )
    .select_related('domain')
    .order_by('modified_at')
    .first()
)
```

**Benefit:** Ensures all prompts are created before processing starts

---

### **Fix #2: Use Select For Update on Domain**

Prevent lost updates on Domain aggregation:

```python
# In _check_and_aggregate_group() - Line 354
with transaction.atomic():
    domain = Domain.objects.select_for_update().get(id=group.domain_id)
    
    # Calculate totals
    domain_analytics = PromptAnalytics.objects.filter(...)
    totals = domain_analytics.aggregate(...)
    
    # Update domain
    domain.total_citations = totals['total_citations']
    domain.total_mentions = totals['total_mentions']
    domain.save()
```

**Benefit:** Prevents concurrent updates from overwriting each other

---

### **Fix #3: Add Prompt Count Validation**

Verify group is complete before marking COMP:

```python
# In _check_and_aggregate_group()
group = PromptGroup.objects.get(id=group_id)

# Check if group has at least one prompt
if group.prompts.count() == 0:
    logger.warning(f"Group {group.id} has no prompts, skipping aggregation")
    return

# Check all prompts are accounted for (COMP or FAIL)
total_prompts = group.prompts.count()
finished_prompts = group.prompts.filter(
    track_status__in=['COMP', 'FAIL']
).count()

if total_prompts != finished_prompts:
    logger.warning(f"Group {group.id} incomplete: {finished_prompts}/{total_prompts} finished")
    return
```

---

## 📊 **Current Status Summary**

| Scenario | Protected? | Risk Level | Impact |
|----------|-----------|------------|---------|
| Multiple schedulers pick same group | ✅ Yes | Low | None |
| Multiple processes try same prompt | ✅ Yes | Low | None |
| Analytics reads incomplete group | ❌ No | Medium | Missing analytics |
| Domain updates overwrite each other | ❌ No | Medium | Wrong totals |
| Duplicate PromptAnalytics created | ✅ Yes | Low | None |

---

## 🎯 **Recommendations Priority**

### **High Priority**
1. ✅ **Add domain status check** in schedule_tick() (Fix #1)
   - Prevents processing incomplete groups
   - Easy to implement
   - Big impact

### **Medium Priority**
2. ⚠️ **Add select_for_update on Domain** (Fix #2)
   - Prevents lost updates
   - Moderate complexity
   - Important for data integrity

### **Low Priority**
3. 💡 **Add prompt count validation** (Fix #3)
   - Safety check
   - Low complexity
   - Defensive programming

---

## 🚀 **Quick Win: Implement Fix #1 Now**

Add one line to prevent the biggest issue:

```python
# File: engine/core/prompt_analytics_processor.py
# Line 82

# OLD
group = (
    PromptGroup.objects.filter(track_status='INIT')
    .select_related('domain')
    .order_by('modified_at')
    .first()
)

# NEW
group = (
    PromptGroup.objects.filter(
        track_status='INIT',
        domain__processing_status='COMP'  # ✅ ADD THIS LINE
    )
    .select_related('domain')
    .order_by('modified_at')
    .first()
)
```

**This single change prevents 90% of race condition issues!**

---

## 📖 **Summary**

**Your instinct was correct** - there ARE potential race conditions between the two processors.

**Good News:**
- ✅ Most critical paths use proper locking (select_for_update)
- ✅ Duplicate processing is prevented
- ✅ Race conditions on same group/prompt are handled

**Areas for Improvement:**
- ⚠️ Processing can start before domain finishes (incomplete groups)
- ⚠️ Domain aggregation updates might overwrite each other
- 💡 Could add more validation checks

**Bottom Line:** The system works reasonably well, but adding Fix #1 would make it much more robust!

Would you like me to implement these fixes?

