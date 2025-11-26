# Prompt-Keyword Linking Fix

## Issue
When generating prompts from keywords in the domain processor, the keyword-prompt relationships were not being stored in the `prompt_keywords` table.

## Root Causes Identified

1. **Missing `Decimal` import**: The `_link_prompt_to_keyword_direct` method used `Decimal('100.00')` but `Decimal` was not imported at the module level, causing a `NameError` when trying to create PromptKeyword records.

2. **Mapping timing issue**: The prompt-to-keyword mapping was built BEFORE prompt sanitization, but the lookup used sanitized prompt text. This caused mapping lookups to fail because the keys didn't match.

3. **Lack of error tracking**: No summary statistics were available to track how many links were created, skipped, or failed.

## Fixes Applied

### 1. Added `Decimal` Import
```python
from decimal import Decimal
```
Added at the top of `domain_processor.py` to fix the NameError.

### 2. Fixed Mapping Timing
Changed the mapping to be built **AFTER** sanitization:
```python
# Build prompt-to-keyword mapping AFTER sanitization (using sanitized prompt text)
# This ensures the mapping keys match the actual prompt text used for storage
prompt_to_keyword_map = {}
for p in prompts:
    prompt_text = (p.get('prompt_text') or p.get('prompt') or '').strip()
    keyword = (p.get('keyword') or '').strip()
    if prompt_text and keyword:
        prompt_to_keyword_map[prompt_text] = keyword
```

### 3. Enhanced Error Handling and Tracking
- Updated `_link_prompt_to_keyword_direct` to return status codes: `'created'`, `'exists'`, or `'failed'`
- Added tracking counters for links created, skipped, and failed
- Added summary output showing linking statistics
- Added warnings for prompts without keywords

### 4. Improved Logging
- Added debug output showing sample mappings
- Added warnings when prompts have no keyword association
- Added summary statistics after processing

## Code Changes

### File: `engine/core/domain_processor.py`

1. **Added import** (line ~6):
   ```python
   from decimal import Decimal
   ```

2. **Fixed mapping timing** (moved after sanitization, ~line 186-193)

3. **Updated `_link_prompt_to_keyword_direct` method**:
   - Changed return type from `None` to `str`
   - Returns `'created'`, `'exists'`, or `'failed'`
   - Better error messages

4. **Updated `_store_prompt_groups` method**:
   - Added tracking counters
   - Captures return values from linking function
   - Prints summary statistics

## Testing

### Manual Test Script
A test script is provided: `engine/test_prompt_keyword_linking.py`

**Usage:**
```bash
cd engine
python test_prompt_keyword_linking.py --domain-id <domain_id>
```

**Options:**
- `--domain-id`: Optional domain ID to test (defaults to most recently processed domain)
- `--distribution`: Show keyword-prompt distribution statistics

**Example Output:**
```
================================================================================
Testing Prompt-Keyword Linking
================================================================================

📋 Testing Domain: Example Domain (ID: 1)
   Status: COMP
   Modified: 2024-01-15 10:30:00

📊 Prompt Statistics:
   Total prompts: 20
   Total prompt-keyword links: 20
   Prompts with keyword links: 20
   Prompts without keyword links: 0
   Link coverage: 100.0%

✅ SUCCESS: All prompts are linked to keywords!
```

### API Testing

1. **Process a domain** (if not already processed):
   ```bash
   curl -X POST http://localhost:8000/api/engine/start-processing/ \
     -H "Content-Type: application/json" \
     -d '{"domain_id": 1, "sync": false}'
   ```

2. **Check the logs** for linking statistics:
   ```
   📊 Prompt-Keyword Linking Summary:
      ✅ Created: 20 links
      ⚠️  Already exists: 0 links
      ❌ Failed: 0 links
   ```

3. **Verify in database**:
   ```sql
   SELECT COUNT(*) FROM prompt_keywords 
   WHERE prompt_id IN (
     SELECT id FROM prompts WHERE group_id IN (
       SELECT id FROM prompt_groups WHERE domain_id = 1
     )
   );
   ```

## Expected Behavior

After the fix:
1. ✅ All prompts generated from keywords should have corresponding entries in `prompt_keywords` table
2. ✅ Each prompt should be linked to at least one keyword
3. ✅ The linking should work even if prompt text is sanitized
4. ✅ Clear logging shows linking success/failure statistics
5. ✅ No `NameError` exceptions when creating PromptKeyword records

## Verification Checklist

- [x] `Decimal` import added
- [x] Mapping built after sanitization
- [x] Linking function returns status codes
- [x] Tracking counters added
- [x] Summary statistics printed
- [x] Error handling improved
- [x] Test script created

## Notes

- The fix preserves backward compatibility
- Existing prompts without links will remain unlinked (they would need to be reprocessed)
- The linking uses case-insensitive keyword matching
- Keywords are normalized to lowercase in the database

