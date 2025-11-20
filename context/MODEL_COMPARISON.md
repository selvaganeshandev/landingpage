# Model Comparison: Backend vs Engine

This document lists all differences between backend models and engine shared models.

## General Pattern
- **Backend**: Full Django models with `managed = True` (default), includes indexes, full Meta configuration
- **Engine**: Read-only models with `managed = False`, minimal Meta configuration, no indexes

---

## 1. Domain Model

### Backend (`backend/domains/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['organisation', 'processing_status'])`
  - `Index(fields=['organisation', '-visibility_score'])`
  - `Index(fields=['processing_status', 'tracked_at'])`
  - `Index(fields=['sentiment_category', '-sentiment_score'])`
- ✅ Includes `DomainAccess` model (not in engine)

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta
- ❌ No `DomainAccess` model

**Fields**: Identical

---

## 2. Organisation Model

### Backend (`backend/authentication/models.py`)
- ✅ Full Meta class
- ✅ Includes indexes:
  - `Index(fields=['organisation', 'role', 'is_active'])`
  - `Index(fields=['organisation', 'created_at'])`

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta

**Fields**: Identical

---

## 3. Account Model

### Backend (`backend/authentication/models.py`)
- ✅ Full Meta class with indexes
- ✅ `groups` and `user_permissions` use default related_name (may cause clashes)
- ✅ Includes additional models: `TeamInvitation`, `UserPermission`, `PasswordResetToken`

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta
- ✅ Custom related_name for `groups` and `user_permissions`:
  - `groups.related_name = "account_set"`
  - `user_permissions.related_name = "account_set"`
- ❌ No `TeamInvitation`, `UserPermission`, `PasswordResetToken` models

**Fields**: Identical

---

## 4. Keyword Model

### Backend (`backend/keywords/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['domain', 'created_at'])`

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta

**Fields**: Identical

---

## 5. PromptGroup Model

### Backend (`backend/prompts/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['domain', 'is_published'])`
  - `Index(fields=['domain', 'track_status'])`
  - `Index(fields=['domain', '-total_mentions'])`
- ✅ `track_status` max_length=10

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta
- ✅ `track_status` max_length=50 (different from backend)
- ✅ Has `PROCESSING_STATUS_CHOICES` defined in class (backend doesn't)

**Fields**: Identical (except `track_status` max_length)

---

## 6. Prompt Model

### Backend (`backend/prompts/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['group', 'track_status'])`
  - `Index(fields=['group', 'type'])`
  - `Index(fields=['tracked_at'])`

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta

**Fields**: Identical

---

## 7. PromptAnalytics Model

### Backend (`backend/prompts/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['prompt', 'platform', 'created_at'])`
  - `Index(fields=['prompt', 'is_mention', '-position'])`
  - `Index(fields=['platform', 'is_mention', 'created_at'])`
  - `Index(fields=['prompt', '-sentiment_score'])`
- ✅ `track_status` max_length=10

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta
- ✅ `track_status` max_length=50 (different from backend)

**Fields**: Identical (except `track_status` max_length)

---

## 8. Competitor Model

### Backend (`backend/competitors/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['domain'])`
  - `Index(fields=['track_status', 'modified_at'])`
  - `Index(fields=['domain', '-share_of_voice_percentage'])`
  - `Index(fields=['domain', '-visibility_score'])`
  - `Index(fields=['domain', '-total_mentions'])`
  - `Index(fields=['domain', 'created_at'])`
- ✅ Includes `CompetitorPrompt` model (deprecated, not in engine)

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta
- ❌ No `CompetitorPrompt` model

**Fields**: Identical

---

## 9. CompetitorAnalytics Model

### Backend (`backend/competitors/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['competitor', 'timestamp'])`
  - `Index(fields=['platform', 'timestamp'])`
  - `Index(fields=['competitor', 'platform', '-timestamp'])`
  - `Index(fields=['timestamp', '-total_mentions'])`

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta

**Fields**: Identical

---

## 10. CompetitorPromptAnalytics Model

### Backend (`backend/competitors/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['competitor', 'track_status'])`
  - `Index(fields=['prompt', 'track_status'])`
  - `Index(fields=['track_status', 'modified_at'])`
  - `Index(fields=['competitor', 'is_mentioned'])`
  - `Index(fields=['competitor', '-position'])`
  - `Index(fields=['competitor', 'platform', 'tracked_at'])`
- ✅ `__str__` method references `self.prompt.prompt_text` (WRONG - should be `prompt.prompt`)

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta
- ✅ `__str__` method references `self.prompt.prompt_text[:50]` (WRONG - should be `prompt.prompt`)

**Fields**: Identical

**Issue**: Both backend and engine have incorrect `__str__` method - `Prompt` model has field `prompt`, not `prompt_text`.

---

## 11. SentimentAnalytics Model

### Backend (`backend/analytics/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['domain', 'timestamp'])`
  - `Index(fields=['theme', 'timestamp'])`
  - `Index(fields=['domain', 'platform', 'timestamp'])`
  - `Index(fields=['domain', 'theme', '-negative_percentage'])`
  - `Index(fields=['timestamp', '-mention_count'])`
- ✅ Has help_text on all fields

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta
- ❌ No help_text on fields

**Fields**: Identical

---

## 12. ShareOfVoiceAnalytics Model

### Backend (`backend/analytics/models.py`)
- ✅ Full Meta class with indexes:
  - `Index(fields=['domain', 'timestamp'])`
  - `Index(fields=['competitor', 'timestamp'])`
  - `Index(fields=['domain', 'platform', 'timestamp'])`
  - `Index(fields=['timestamp', '-share_percentage'])`
  - `Index(fields=['domain', 'competitor', 'platform', 'timestamp'])`
  - `Index(fields=['market_position', 'timestamp'])`

### Engine (`engine/shared_models/models.py`)
- ❌ `managed = False`
- ❌ No indexes in Meta

**Fields**: Identical

---

## Summary of Key Differences

### 1. **Meta Configuration**
- **Backend**: Full `Meta` classes with indexes, verbose names, ordering
- **Engine**: Minimal `Meta` classes with `managed = False`, no indexes

### 2. **Indexes**
- **Backend**: All models have database indexes for performance
- **Engine**: No indexes (since tables are managed by backend)

### 3. **Field Differences**
- `PromptGroup.track_status`: Backend max_length=10, Engine max_length=50
- `PromptAnalytics.track_status`: Backend max_length=10, Engine max_length=50

### 4. **Model Availability**
- **Backend Only**: 
  - `DomainAccess`
  - `TeamInvitation`
  - `UserPermission`
  - `PasswordResetToken`
  - `CompetitorPrompt` (deprecated)

### 5. **Related Name Differences**
- **Account.groups**: Backend uses default, Engine uses `"account_set"` to avoid clashes
- **Account.user_permissions**: Backend uses default, Engine uses `"account_set"` to avoid clashes

### 6. **Bug in Both**
- `CompetitorPromptAnalytics.__str__()`: Both reference `prompt.prompt_text` but should be `prompt.prompt`

---

## Recommendations

1. **Align `track_status` max_length**: Make backend and engine consistent (recommend 50 for flexibility)
2. **Fix `CompetitorPromptAnalytics.__str__()`**: Change `prompt_text` to `prompt` in both
3. **Consider**: Engine models don't need indexes since they're read-only, but consistency in field definitions is important

