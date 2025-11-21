# Engine API Endpoints Reference

Base URL: `http://localhost:8001/api/`

All endpoints use `AllowAny` permission (no authentication required).

---

## 📊 Processing Status

### GET `/api/status/`
Get overall processing status (active threads, domain counts, etc.)

**Response:**
```json
{
  "success": true,
  "data": {
    "active_threads": 0,
    "max_concurrent": 10,
    "available_slots": 10,
    "active_domain_ids": [],
    "domain_counts": {
      "INIT": 0,
      "SCHD": 1,
      "PROC": 0,
      "COMP": 0,
      "FAIL": 1
    }
  }
}
```

---

## 🏢 Domain Processing APIs

### POST `/api/start/`
**Start domain processing** (keywords → prompts → grouping)

**Request Body:**
```json
{
  "domain_id": 1,
  "sync": false  // Optional: true for synchronous processing, false for async (default)
}
```

**Response:**
```json
{
  "success": true,
  "message": "Started processing for domain: example.com",
  "domain_id": 1,
  "mode": "async"  // or "sync" or "loop"
}
```

**Modes:**
- `sync=true`: Processes inline (blocks until complete)
- `sync=false`: Uses Celery (if available) or processing loop
- If Celery unavailable: Falls back to processing loop automatically

---

### POST `/api/domains/schedule/`
**Schedule a domain for processing** (sets status to SCHD)

**Request Body:**
```json
{
  "domain_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Domain example.com scheduled for processing",
  "domain_id": 1
}
```

**Note:** Only works if domain is in `INIT` status.

---

### POST `/api/domains/reset/`
**Reset domain to INIT status** (for reprocessing)

**Request Body:**
```json
{
  "domain_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Domain example.com reset to INIT status",
  "domain_id": 1
}
```

---

### GET `/api/domains/`
**List all domains** with their processing status

**Query Parameters:**
- `status`: Filter by status (INIT, SCHD, PROC, COMP, FAIL)

**Response:**
```json
{
  "success": true,
  "domains": [
    {
      "id": 1,
      "name": "example.com",
      "processing_status": "SCHD",
      "track_message": "Queued for initial processing",
      ...
    }
  ]
}
```

---

### GET `/api/domains/<domain_id>/`
**Get domain details** including keywords and prompt groups

**Response:**
```json
{
  "success": true,
  "domain": {
    "id": 1,
    "name": "example.com",
    "processing_status": "PROC",
    "keywords": [...],
    "prompt_groups": [...]
  }
}
```

---

## 📝 Prompt Analytics Processing APIs

### POST `/api/prompts/process/`
**Start prompt analytics processing for a domain** (processes all prompts for a domain)

**Request Body:**
```json
{
  "domain_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Started prompt analytics processing for domain: example.com",
  "domain_id": 1,
  "prompts_count": 10
}
```

**Note:** Requires domain to have prompts. Uses Celery task queue.

---

### POST `/api/prompts/process-single/`
**Start analytics processing for a single prompt**

**Request Body:**
```json
{
  "prompt_id": 123
}
```

**Response:**
```json
{
  "message": "Single prompt analytics processing started",
  "task_id": "abc-123",
  "prompt_id": 123
}
```

---

### POST `/api/prompts/start/`
**Start processing for a specific prompt** (sync or async)

**Request Body:**
```json
{
  "prompt_id": 123,
  "sync": false  // Optional: true for synchronous, false for async (default)
}
```

**Response (async):**
```json
{
  "success": true,
  "mode": "async",
  "task_id": "abc-123",
  "prompt_id": 123
}
```

**Response (sync):**
```json
{
  "success": true,
  "mode": "sync",
  "prompt_id": 123,
  "status": "completed",
  ...
}
```

---

### GET `/api/prompts/status/<domain_id>/`
**Get prompt analytics processing status for a domain**

**Response:**
```json
{
  "success": true,
  "data": {
    "domain": {
      "id": 1,
      "name": "example.com",
      "processing_status": "PROC"
    },
    "prompts": {
      "total": 10,
      "status_counts": {
        "INIT": 2,
        "SCHD": 1,
        "PROC": 3,
        "COMP": 4,
        "FAIL": 0
      }
    },
    "analytics": {
      "total": 30,
      "platform_status": {
        "chatgpt": {
          "pending": 2,
          "processing": 1,
          "completed": 7,
          "failed": 0
        },
        "gemini": {...},
        "perplexity": {...}
      },
      "progress_percentage": 76.67
    }
  }
}
```

---

### GET `/api/prompts/summary/<domain_id>/`
**Get aggregated prompt analytics summary for a domain**

**Response:**
```json
{
  "success": true,
  "data": {
    "domain": {
      "id": 1,
      "name": "example.com"
    },
    "aggregated_metrics": {
      "total_citations": 150,
      "total_mentions": 75,
      "avg_position": 3.5,
      "avg_sentiment_score": 0.65
    },
    "platform_metrics": {
      "ChatGPT": {...},
      "Google Gemini": {...},
      "Perplexity": {...}
    },
    "group_summaries": [...]
  }
}
```

---

## 🔄 Processing Flow

### Domain Processing Flow:
```
1. Create domain with keywords (via backend API)
   ↓
2. Domain status: INIT → SCHD (automatic)
   ↓
3. POST /api/start/ (or processing loop picks it up)
   ↓
4. Domain status: SCHD → PROC
   ↓
5. Process keywords → Generate prompts → Group prompts
   ↓
6. Domain status: PROC (waiting for prompt analytics)
   ↓
7. POST /api/prompts/process/ (or automatic)
   ↓
8. Process prompts → Query LLMs → Store analytics
   ↓
9. Domain status: PROC → COMP (when all prompts done)
```

### Prompt Processing Flow:
```
1. Prompts created (via domain processing)
   ↓
2. Prompt status: INIT
   ↓
3. POST /api/prompts/process/ or /api/prompts/start/
   ↓
4. Prompt status: INIT → SCHD → PROC
   ↓
5. Query ChatGPT, Gemini, Perplexity
   ↓
6. Store analytics results
   ↓
7. Prompt status: PROC → COMP
```

---

## 📋 Example cURL Commands

### Start Domain Processing (Async)
```bash
curl -X POST http://localhost:8001/api/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1, "sync": false}'
```

### Start Domain Processing (Sync)
```bash
curl -X POST http://localhost:8001/api/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1, "sync": true}'
```

### Schedule Domain
```bash
curl -X POST http://localhost:8001/api/domains/schedule/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'
```

### Reset Domain
```bash
curl -X POST http://localhost:8001/api/domains/reset/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'
```

### Start Prompt Analytics Processing
```bash
curl -X POST http://localhost:8001/api/prompts/process/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'
```

### Start Single Prompt Processing
```bash
curl -X POST http://localhost:8001/api/prompts/start/ \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": 123, "sync": false}'
```

### Get Processing Status
```bash
curl http://localhost:8001/api/status/
```

### Get Domain List
```bash
curl http://localhost:8001/api/domains/?status=SCHD
```

### Get Prompt Analytics Status
```bash
curl http://localhost:8001/api/prompts/status/1/
```

---

## ⚙️ Notes

1. **Processing Loop**: If Celery is not available, the processing loop (`start_engine.py`) automatically picks up `SCHD` domains every 30 seconds.

2. **Status Transitions**:
   - Domain: `INIT` → `SCHD` → `PROC` → `COMP` (or `FAIL`)
   - Prompt: `INIT` → `SCHD` → `PROC` → `COMP` (or `FAIL`)

3. **Concurrent Processing**: Maximum 10 concurrent domains (configurable via `MAX_CONCURRENT_DOMAINS` setting).

4. **Automatic Processing**: The processing loop automatically handles domains in `SCHD` status, so manual API calls are optional.

5. **Error Handling**: All endpoints return JSON with `success` and `error` fields for error cases.


