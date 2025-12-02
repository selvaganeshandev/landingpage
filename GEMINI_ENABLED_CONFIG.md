# Google Gemini Platform Configuration

## Overview

Google Gemini has been enabled in the domain processor. The system will now process prompts with both ChatGPT and Google Gemini by default.

## Configuration

### Settings File

**File:** `engine/llm_monitor_engine/settings.py`

```python
ENABLED_PLATFORMS = config('ENABLED_PLATFORMS', default='chatgpt,gemini', cast=lambda v: [p.strip() for p in v.split(',')])
```

**Default Value:** `'chatgpt,gemini'` (both platforms enabled)

### Environment Variable

You can override this in `.env` file:

```bash
# Enable both ChatGPT and Gemini (default)
ENABLED_PLATFORMS=chatgpt,gemini

# Enable only Gemini
ENABLED_PLATFORMS=gemini

# Enable all platforms
ENABLED_PLATFORMS=chatgpt,gemini,perplexity
```

## How It Works

### 1. Domain Processor

When a domain is processed:

1. **Prompt Generation**: Prompts are generated using ChatGPT
2. **Analytics Creation**: Default `PromptAnalytics` records are created for each enabled platform
   - For `gemini` → Creates analytics with platform `'Google Gemini'`
   - For `chatgpt` → Creates analytics with platform `'ChatGPT'`

**File:** `engine/core/domain_processor.py`

```python
def _create_default_analytics_for_prompt(self, prompt: Prompt, domain: Domain):
    enabled_platforms = getattr(settings, 'ENABLED_PLATFORMS', ['chatgpt'])
    
    platform_map = {
        'chatgpt': 'ChatGPT',
        'gemini': 'Google Gemini',  # ✅ Enabled
        'perplexity': 'Perplexity'
    }
    
    for platform_key in enabled_platforms:
        platform_name = platform_map.get(platform_key, platform_key.title())
        # Creates PromptAnalytics for 'Google Gemini'
```

### 2. Prompt Analytics Processor

When prompts are processed:

1. **Platform Processing**: Each enabled platform processes the prompt
2. **Gemini Processing**: Uses `process_prompt_with_gemini()` function
3. **Results Storage**: Stores results in `PromptAnalytics` with platform `'Google Gemini'`

**File:** `engine/core/prompt_analytics_processor.py`

```python
platforms = getattr(settings, 'ENABLED_PLATFORMS', ['chatgpt'])

for platform in platforms:
    if platform == 'gemini' and self.gemini_client is not None:
        result = self._process_prompt_with_gemini(
            prompt.prompt, user_domain, self.gemini_client, group
        )
```

### 3. Gemini Client Initialization

**File:** `engine/core/prompt_analytics_processor.py`

```python
try:
    self.gemini_client = self._get_gemini_client()
except Exception as e:
    logger.warning(f"Gemini client unavailable: {str(e)}")
```

**Requirements:**
- `GEMINI_API_KEY` must be set in environment variables
- Google Generative AI library must be installed

## Platform Mapping

| Setting Key | Database Platform Name |
|-------------|----------------------|
| `chatgpt` | `ChatGPT` |
| `gemini` | `Google Gemini` |
| `perplexity` | `Perplexity` |

## Verification

### Check Enabled Platforms

```python
from django.conf import settings
print(settings.ENABLED_PLATFORMS)
# Output: ['chatgpt', 'gemini']
```

### Check Gemini Client

```python
from engine.core.prompt_analytics_processor import PromptAnalyticsProcessor

processor = PromptAnalyticsProcessor()
processor._load_helpers()
print(f"Gemini client available: {processor.gemini_client is not None}")
```

### Check Analytics Records

```python
from shared_models.models import PromptAnalytics

# Check for Google Gemini analytics
gemini_analytics = PromptAnalytics.objects.filter(platform='Google Gemini')
print(f"Total Gemini analytics: {gemini_analytics.count()}")
```

## Environment Variables Required

```bash
# Gemini API Key (required for Gemini processing)
GEMINI_API_KEY=your-gemini-api-key-here
```

## Processing Flow

```
Domain Processing
  ↓
Generate Prompts (ChatGPT)
  ↓
Create PromptAnalytics for each enabled platform:
  ├─ ChatGPT (platform='ChatGPT')
  └─ Google Gemini (platform='Google Gemini') ✅
  ↓
Prompt Analytics Processing
  ↓
For each platform:
  ├─ Process with ChatGPT
  └─ Process with Gemini ✅
  ↓
Store results in respective PromptAnalytics records
```

## What Changed

### Before
- Only ChatGPT was enabled by default
- `ENABLED_PLATFORMS = 'chatgpt'`
- Gemini processing was available but not enabled

### After
- Both ChatGPT and Gemini are enabled by default
- `ENABLED_PLATFORMS = 'chatgpt,gemini'`
- Gemini processing is automatically included

## Impact

1. **New Prompts**: Will have analytics records created for both ChatGPT and Google Gemini
2. **Existing Prompts**: Will continue to work as before (only ChatGPT if not reprocessed)
3. **Processing Time**: Slightly longer as both platforms process each prompt
4. **Data**: More comprehensive analytics data with Gemini results

## Disabling Gemini

If you want to disable Gemini and use only ChatGPT:

**Option 1: Environment Variable**
```bash
ENABLED_PLATFORMS=chatgpt
```

**Option 2: Update Settings**
```python
ENABLED_PLATFORMS = config('ENABLED_PLATFORMS', default='chatgpt', ...)
```

## Troubleshooting

### Gemini Not Processing

1. **Check API Key:**
   ```bash
   echo $GEMINI_API_KEY
   ```

2. **Check Client Initialization:**
   ```python
   from engine.core.analytics_helpers import get_gemini_client
   client = get_gemini_client()
   ```

3. **Check Logs:**
   ```bash
   tail -f logs/engine.log | grep -i gemini
   ```

### Missing Analytics Records

1. **Verify Platform in Settings:**
   ```python
   from django.conf import settings
   assert 'gemini' in settings.ENABLED_PLATFORMS
   ```

2. **Check Domain Processing:**
   - Ensure domain was processed after Gemini was enabled
   - Reprocess domain to create Gemini analytics records

## Summary

✅ **Google Gemini is now enabled** in the domain processor by default.

- Default: Both ChatGPT and Gemini process prompts
- Configuration: Via `ENABLED_PLATFORMS` setting
- Database: Stored as `'Google Gemini'` platform
- Processing: Automatic via prompt analytics processor

The system will now generate analytics for both platforms, providing more comprehensive LLM response data.

