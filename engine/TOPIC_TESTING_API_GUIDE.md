# Engine API Testing Guide for Topic Processing

## Base URL
```
http://localhost:8001/api/
```

---

## 📋 **Complete Topic Processing Flow APIs**

### **Step 1: Check System Status**

#### 1.1 Get Processing Status
```bash
GET /api/status/
```

**Response:**
```json
{
  "success": true,
  "data": {
    "active_threads": 0,
    "domain_counts": {
      "INIT": 5,
      "SCHD": 0,
      "PROC": 1,
      "COMP": 3,
      "FAIL": 0
    }
  }
}
```

**cURL:**
```bash
curl http://localhost:8001/api/status/
```

---

### **Step 2: Domain Management**

#### 2.1 List All Domains
```bash
GET /api/domains/
```

**Query Parameters:**
- `status` (optional): Filter by status (INIT, SCHD, PROC, COMP, FAIL)

**Example:**
```bash
# Get all domains
curl http://localhost:8001/api/domains/

# Get only completed domains
curl http://localhost:8001/api/domains/?status=COMP
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Example Domain",
      "url": "https://example.com",
      "processing_status": "COMP",
      "track_message": "Successfully completed...",
      "total_mentions": 150,
      "visibility_score": "85.50"
    }
  ],
  "count": 1
}
```

#### 2.2 Get Domain Details
```bash
GET /api/domains/{domain_id}/
```

**Example:**
```bash
curl http://localhost:8001/api/domains/1/
```

#### 2.3 Schedule Domain for Processing
```bash
POST /api/domains/schedule/
```

**Body:**
```json
{
  "domain_id": 1
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/api/domains/schedule/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'
```

#### 2.4 Reset Domain to INIT
```bash
POST /api/domains/reset/
```

**Body:**
```json
{
  "domain_id": 1
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/api/domains/reset/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'
```

---

### **Step 3: Start Domain Processing**

#### 3.1 Start Domain Processing (Async - Default)
```bash
POST /api/start/
```

**Body:**
```json
{
  "domain_id": 1
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/api/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'
```

**Response:**
```json
{
  "success": true,
  "mode": "async",
  "task_id": "abc123-def456-...",
  "domain_id": 1
}
```

#### 3.2 Start Domain Processing (Sync - For Testing)
```bash
POST /api/start/
```

**Body:**
```json
{
  "domain_id": 1,
  "sync": true
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/api/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1, "sync": true}'
```

**Response:**
```json
{
  "success": true,
  "mode": "sync",
  "domain_id": 1,
  "message": "Processing started"
}
```

**Note:** This will:
1. Generate prompts from keywords
2. Group prompts using NLP
3. Store prompt groups and prompts
4. Link prompts to keywords (for topic analytics)
5. Set domain status to PROC

---

### **Step 4: Prompt Analytics Processing**

#### 4.1 Start Prompt Analytics Processing
```bash
POST /api/prompts/process/
```

**Body:**
```json
{
  "domain_id": 1
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/api/prompts/process/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'
```

**Note:** This processes all prompts for the domain and creates PromptAnalytics records.

#### 4.2 Process Single Prompt
```bash
POST /api/prompts/process-single/
```

**Body:**
```json
{
  "prompt_id": 123
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/api/prompts/process-single/ \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": 123}'
```

#### 4.3 Start Prompt Processing (Sync/Async)
```bash
POST /api/prompts/start/
```

**Body:**
```json
{
  "prompt_id": 123,
  "sync": false
}
```

**cURL:**
```bash
curl -X POST http://localhost:8001/api/prompts/start/ \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": 123, "sync": false}'
```

#### 4.4 Get Prompt Analytics Status
```bash
GET /api/prompts/status/{domain_id}/
```

**Example:**
```bash
curl http://localhost:8001/api/prompts/status/1/
```

**Response:**
```json
{
  "domain_id": 1,
  "total_prompts": 50,
  "processed": 45,
  "pending": 5,
  "failed": 0,
  "completion_percentage": 90
}
```

#### 4.5 Get Prompt Analytics Summary
```bash
GET /api/prompts/summary/{domain_id}/
```

**Example:**
```bash
curl http://localhost:8001/api/prompts/summary/1/
```

---

### **Step 5: Topic Processing**

#### 5.1 Start Topic Processing (Manual - Recommended for Testing)
```bash
POST /api/topics/start/
```

**Body:**
```json
{
  "domain_id": 1,
  "sync": true
}
```

**Parameters:**
- `domain_id` (required): ID of domain to process topics for
- `sync` (optional, default=false): If `true`, runs synchronously without Celery

**cURL (Sync - for testing):**
```bash
curl -X POST http://localhost:8001/api/topics/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1, "sync": true}'
```

**Response (Sync):**
```json
{
  "success": true,
  "mode": "sync",
  "domain_id": 1,
  "topics_created": 5,
  "keywords_processed": 12,
  "topics_processed": 5
}
```

**cURL (Async - default):**
```bash
curl -X POST http://localhost:8001/api/topics/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'
```

**Response (Async):**
```json
{
  "success": true,
  "mode": "async",
  "task_id": "abc123-def456-...",
  "domain_id": 1,
  "message": "Topic processing scheduled"
}
```

**What it does:**
1. Groups keywords into topics using ChatGPT/NLP
2. Creates `Topic` and `TopicKeyword` records
3. Processes keyword analytics from prompts
4. Aggregates analytics to topic level
5. Creates `TopicAnalytics` time-series records

#### 5.2 Automatic Topic Processing

**Note:** Topic processing is **also automatically triggered** when:
- Domain `processing_status` becomes `COMP`
- All prompt groups are completed

**Flow:**
1. Domain completes → `processing_status = 'COMP'`
2. Topic Processor automatically runs (via Celery task)
3. Same processing steps as manual trigger

**To verify topic processing completed:**
- Check domain status is `COMP`
- Query topics in database (via backend API or Django admin)
- Check `Topic.track_status = 'COMP'`
- Check `KeywordAnalytics` records exist
- Check `TopicAnalytics` records exist

---

### **Step 6: Verify Topic Processing (Database Queries)**

Since topic processing is automatic, you can verify it worked by checking:

#### 6.1 Check Domain Status
```bash
GET /api/domains/{domain_id}/
```

**Expected:** `processing_status: "COMP"`

#### 6.2 Check Topics (via Backend API)
```bash
# Backend API (not engine)
GET http://localhost:8000/api/topics/?domain={domain_id}
```

**Expected Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "name": "Product & Features",
      "keyword_list": ["product", "features", "specifications"],
      "total_mentions": 89,
      "visibility_score": "92.50",
      "sentiment_score": "0.75",
      "trend_percentage": "15.20",
      "platform_list": ["ChatGPT", "Claude"],
      "domain": 1
    }
  ]
}
```

---

## 🔄 **Complete Testing Flow**

### **Full End-to-End Test:**

```bash
# 1. Check system status
curl http://localhost:8001/api/status/

# 2. List domains
curl http://localhost:8001/api/domains/

# 3. Start domain processing (sync for testing)
curl -X POST http://localhost:8001/api/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1, "sync": true}'

# 4. Wait for domain to reach PROC status, then start prompt analytics
curl -X POST http://localhost:8001/api/prompts/process/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'

# 5. Monitor prompt analytics status
curl http://localhost:8001/api/prompts/status/1/

# 6. Wait for domain to reach COMP status, then manually trigger topic processing
curl -X POST http://localhost:8001/api/topics/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1, "sync": true}'

# 7. Verify domain is COMP
curl http://localhost:8001/api/domains/1/

# 8. Check topics via backend API
curl http://localhost:8000/api/topics/?domain=1
```

---

## 🧪 **Testing Scenarios**

### **Scenario 1: New Domain with Keywords**

1. Create domain with keywords (via backend)
2. Start domain processing: `POST /api/start/` with `domain_id`
3. Wait for prompts to be generated
4. Start prompt analytics: `POST /api/prompts/process/`
5. Wait for domain to complete
6. **Manually trigger topic processing:** `POST /api/topics/start/` with `domain_id` and `sync: true`
7. **OR wait for automatic topic processing** (when domain reaches COMP)

### **Scenario 2: Reprocess Domain**

1. Reset domain: `POST /api/domains/reset/`
2. Start processing again: `POST /api/start/`
3. Topics will be regenerated (old topics may be updated)

### **Scenario 3: Check Topic Status**

1. Domain must be `COMP`
2. Check `Topic.track_status` in database
3. Should be `COMP` if processing succeeded
4. Check `KeywordAnalytics` records exist
5. Check `TopicAnalytics` records exist

---

## 📊 **Status Monitoring**

### **Domain Status Flow:**
```
INIT → SCHD → PROC → COMP
                      ↓
              Topic Processing (Automatic)
                      ↓
              Topics Created & Analytics Calculated
```

### **Topic Status Flow:**
```
INIT → PROC → COMP
```

### **KeywordAnalytics Status Flow:**
```
INIT → PROC → COMP (per keyword-platform pair)
```

---

## 🐛 **Troubleshooting**

### **Topics Not Created?**

1. Check domain status: `GET /api/domains/{domain_id}/`
   - Must be `COMP` for topics to be created
2. Check Celery is running (topic processing uses Celery)
3. Check logs for errors in topic processor
4. Verify keywords exist for the domain
5. Check OpenAI API key is configured

### **Topic Analytics Not Calculated?**

1. Check `Topic.track_status` - should be `COMP`
2. Check `PromptKeyword` records exist (prompts linked to keywords)
3. Check `PromptAnalytics` records exist and are `COMP`
4. Verify `KeywordAnalytics` records were created

### **Reset and Retry:**

```bash
# Reset domain
curl -X POST http://localhost:8001/api/domains/reset/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'

# Start again
curl -X POST http://localhost:8001/api/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1, "sync": true}'
```

---

## 📝 **Notes**

- **Topic processing is automatic** - no manual API call needed
- Topics are created when domain reaches `COMP` status
- All processing happens asynchronously via Celery
- Use `sync: true` for synchronous processing during testing
- Check backend API for topic data retrieval (not engine API)
- Engine API focuses on processing, backend API focuses on data retrieval

---

## 🔗 **Related Backend APIs**

For retrieving topic data, use the **backend API** (port 8000):

```bash
# List topics
GET http://localhost:8000/api/topics/?domain={domain_id}

# Get topic details
GET http://localhost:8000/api/topics/{topic_id}/

# Get topic analytics
GET http://localhost:8000/api/topics/{topic_id}/analytics/
```

