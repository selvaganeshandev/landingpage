# Competitor API Testing Guide

## 🚀 **Quick Start**

**Base URL:** `http://127.0.0.1:8001/api`

**Prerequisites:**
1. Make sure engine is running: `python manage.py runserver 0.0.0.0:8001`
2. Domain must have completed prompts with PromptAnalytics (`track_status='COMP'`)
3. Celery worker should be running for async processing

---

## 📋 **Complete API Test Sequence**

### **1. Create Competitor (POST)**

```bash
curl -X POST http://127.0.0.1:8001/api/competitors/ \
  -H "Content-Type: application/json" \
  -d '{
    "domain": 1,
    "name": "Nike",
    "url": "https://www.nike.com"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "domain": 1,
  "domain_name": "Adidas",
  "name": "Nike",
  "url": "https://www.nike.com",
  "track_status": "INIT",
  "track_message": null,
  "tracked_at": null,
  "total_mentions": 0,
  "visibility_score": "0.00",
  "sentiment_score": "0.00",
  "average_position": "0.00",
  "share_of_voice_percentage": "0.00",
  "trend_percentage": "0.00",
  "created_by": null,
  "created_at": "2025-01-15T10:00:00Z",
  "modified_at": "2025-01-15T10:00:00Z"
}
```

---

### **2. List All Competitors (GET)**

```bash
curl http://127.0.0.1:8001/api/competitors/
```

**Filter by Domain:**
```bash
curl "http://127.0.0.1:8001/api/competitors/?domain_id=1"
```

---

### **3. Get Competitor Details (GET)**

```bash
curl http://127.0.0.1:8001/api/competitors/1/
```

---

### **4. Update Competitor (PUT)**

```bash
curl -X PUT http://127.0.0.1:8001/api/competitors/1/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nike Inc",
    "url": "https://www.nike.com"
  }'
```

---

### **5. Trigger Competitor Processing - Single (POST)**

**New Endpoint (Similar to `start_single_prompt_processing`):**

```bash
curl -X POST http://127.0.0.1:8001/api/competitors/process-single/ \
  -H "Content-Type: application/json" \
  -d '{"competitor_id": 1}'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Single competitor processing started for Nike",
  "task_id": "abc123-def456-...",
  "competitor_id": 1,
  "competitor_name": "Nike",
  "track_status": "INIT"
}
```

**Alternative (URL Parameter Version):**

```bash
curl -X POST http://127.0.0.1:8001/api/competitors/1/process/
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Processing started for competitor Nike",
  "competitor_id": 1,
  "track_status": "INIT",
  "task_id": "abc123-def456-..."
}
```

**Note:** Both endpoints trigger Celery task. Processing happens asynchronously.

---

### **6. Check Competitor Status (GET)**

```bash
curl http://127.0.0.1:8001/api/competitors/1/
```

**Status Values:**
- `INIT` - Just created, waiting to be processed
- `SCHD` - Scheduled for processing
- `PROC` - Currently being processed
- `COMP` - Processing completed
- `FAIL` - Processing failed

---

### **7. Get Competitor Analytics (GET)**

```bash
curl http://127.0.0.1:8001/api/competitors/1/analytics/
```

**Expected Response:**
```json
{
  "competitor": {
    "id": 1,
    "name": "Nike",
    "track_status": "COMP",
    "total_mentions": 120,
    "average_position": "1.50",
    "visibility_score": "45.50",
    "sentiment_score": "0.75",
    "share_of_voice_percentage": "30.00"
  },
  "statistics": {
    "total_prompts_tested": 100,
    "times_mentioned": 50,
    "mention_rate": 50.0,
    "average_position": 1.5,
    "average_sentiment": 0.75,
    "total_mention_count": 120
  },
  "recent_prompts": [
    {
      "id": 1,
      "competitor_name": "Nike",
      "prompt_text": "What are the best running shoes?",
      "is_mentioned": true,
      "position": 1,
      "mention_count": 2,
      "sentiment_category": "positive",
      "sentiment_score": "0.80"
    }
  ]
}
```

---

### **8. List Competitor-Prompt Analytics (GET)**

```bash
curl http://127.0.0.1:8001/api/competitor-prompt-analytics/
```

**Filter by Competitor:**
```bash
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/?competitor_id=1"
```

**Filter by Domain:**
```bash
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/?domain_id=1"
```

**Combined Filter:**
```bash
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/?competitor_id=1&domain_id=1"
```

---

### **9. Find Opportunity Gaps (GET)**

**Prompts where competitor ranks in top 5:**

```bash
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/gaps/?domain_id=1"
```

**Filter by Competitor:**
```bash
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/gaps/?domain_id=1&competitor_id=1"
```

**Expected Response:**
```json
[
  {
    "id": 1,
    "competitor": 1,
    "competitor_name": "Nike",
    "prompt": 5,
    "prompt_text": "Best running shoes for marathon training",
    "is_mentioned": true,
    "position": 1,
    "mention_count": 3,
    "sentiment_category": "positive",
    "sentiment_score": "0.85"
  }
]
```

---

### **10. Get Share of Voice Analytics (GET)**

```bash
curl "http://127.0.0.1:8001/api/share-of-voice/?domain_id=1"
```

**Expected Response:**
```json
{
  "domain_id": 1,
  "timestamp": "2025-01-15",
  "platform": "ChatGPT",
  "players": [
    {
      "id": 1,
      "domain_name": "Adidas",
      "competitor": null,
      "competitor_name": "Adidas (Your Brand)",
      "share_percentage": "37.50",
      "mention_count": 150,
      "market_position": 1
    },
    {
      "id": 2,
      "domain_name": "Adidas",
      "competitor": 1,
      "competitor_name": "Nike",
      "share_percentage": "30.00",
      "mention_count": 120,
      "market_position": 2
    },
    {
      "id": 3,
      "domain_name": "Adidas",
      "competitor": 2,
      "competitor_name": "Puma",
      "share_percentage": "20.00",
      "mention_count": 80,
      "market_position": 3
    }
  ]
}
```

---

### **11. Get Competitor Analytics Trends (GET)**

```bash
curl "http://127.0.0.1:8001/api/competitor-analytics/trends/?competitor_id=1&days=30"
```

**Parameters:**
- `competitor_id` (required) - Competitor ID
- `days` (optional, default: 30) - Number of days to look back

---

### **12. Delete Competitor (DELETE)**

```bash
curl -X DELETE http://127.0.0.1:8001/api/competitors/1/
```

---

## 🧪 **Complete Test Flow**

### **Step-by-Step Test Sequence**

```bash
# 1. Create Competitor
COMPETITOR_ID=$(curl -s -X POST http://127.0.0.1:8001/api/competitors/ \
  -H "Content-Type: application/json" \
  -d '{"domain": 1, "name": "Nike", "url": "https://www.nike.com"}' \
  | jq -r '.id')

echo "Created competitor ID: $COMPETITOR_ID"

# 2. Check Status (should be INIT)
curl http://127.0.0.1:8001/api/competitors/$COMPETITOR_ID/

# 3. Trigger Processing (Single Competitor)
curl -X POST http://127.0.0.1:8001/api/competitors/process-single/ \
  -H "Content-Type: application/json" \
  -d "{\"competitor_id\": $COMPETITOR_ID}"

# 4. Wait a few seconds, then check status
sleep 5
curl http://127.0.0.1:8001/api/competitors/$COMPETITOR_ID/

# 5. Get Analytics (after processing completes)
curl http://127.0.0.1:8001/api/competitors/$COMPETITOR_ID/analytics/

# 6. List Competitor-Prompt Analytics
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/?competitor_id=$COMPETITOR_ID"

# 7. Find Opportunity Gaps
DOMAIN_ID=1
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/gaps/?domain_id=$DOMAIN_ID&competitor_id=$COMPETITOR_ID"

# 8. Get Share of Voice
curl "http://127.0.0.1:8001/api/share-of-voice/?domain_id=$DOMAIN_ID"
```

---

## 📊 **Using Python Requests**

```python
import requests

BASE_URL = "http://127.0.0.1:8001/api"

# 1. Create Competitor
response = requests.post(
    f"{BASE_URL}/competitors/",
    json={
        "domain": 1,
        "name": "Nike",
        "url": "https://www.nike.com"
    }
)
competitor = response.json()
competitor_id = competitor['id']
print(f"Created competitor ID: {competitor_id}")

# 2. Trigger Processing (Single Competitor)
response = requests.post(
    f"{BASE_URL}/competitors/process-single/",
    json={"competitor_id": competitor_id}
)
print(f"Processing started: {response.json()}")

# 3. Check Status (poll until COMP)
import time
while True:
    response = requests.get(f"{BASE_URL}/competitors/{competitor_id}/")
    status = response.json()['track_status']
    print(f"Status: {status}")
    if status in ['COMP', 'FAIL']:
        break
    time.sleep(2)

# 4. Get Analytics
response = requests.get(f"{BASE_URL}/competitors/{competitor_id}/analytics/")
analytics = response.json()
print(f"Analytics: {analytics}")

# 5. List Competitor-Prompt Analytics
response = requests.get(
    f"{BASE_URL}/competitor-prompt-analytics/",
    params={"competitor_id": competitor_id}
)
print(f"Prompt Analytics: {response.json()[:5]}")  # First 5

# 6. Get Share of Voice
response = requests.get(
    f"{BASE_URL}/share-of-voice/",
    params={"domain_id": 1}
)
print(f"Share of Voice: {response.json()}")

# 7. Find Opportunity Gaps
response = requests.get(
    f"{BASE_URL}/competitor-prompt-analytics/gaps/",
    params={"domain_id": 1, "competitor_id": competitor_id}
)
print(f"Opportunity Gaps: {response.json()[:5]}")  # First 5
```

---

## 🔍 **Using HTTPie (htttp)**

```bash
# Install: pip install httpie

# Create Competitor
http POST http://127.0.0.1:8001/api/competitors/ \
  domain:=1 \
  name="Nike" \
  url="https://www.nike.com"

# List Competitors
http GET http://127.0.0.1:8001/api/competitors/

# Get Competitor Details
http GET http://127.0.0.1:8001/api/competitors/1/

# Trigger Processing (Single Competitor)
http POST http://127.0.0.1:8001/api/competitors/process-single/ \
  competitor_id:=1

# Get Analytics
http GET http://127.0.0.1:8001/api/competitors/1/analytics/

# Get Share of Voice
http GET http://127.0.0.1:8001/api/share-of-voice/ domain_id==1

# Find Gaps
http GET http://127.0.0.1:8001/api/competitor-prompt-analytics/gaps/ \
  domain_id==1 \
  competitor_id==1
```

---

## 📝 **Quick Reference Table**

| Method | Endpoint | Purpose | Example |
|--------|----------|---------|---------|
| **POST** | `/api/competitors/` | Create competitor | `{"domain": 1, "name": "Nike", "url": "..."}` |
| **GET** | `/api/competitors/` | List all competitors | `?domain_id=1` (filter) |
| **GET** | `/api/competitors/{id}/` | Get competitor details | |
| **PUT** | `/api/competitors/{id}/` | Update competitor | |
| **DELETE** | `/api/competitors/{id}/` | Delete competitor | |
| **POST** | `/api/competitors/process-single/` | **Trigger single competitor processing** | ⭐ `{"competitor_id": 1}` |
| **POST** | `/api/competitors/{id}/process/` | **Trigger processing (URL param)** | ⭐ |
| **GET** | `/api/competitors/{id}/analytics/` | **Get detailed analytics** | ⭐ |
| **GET** | `/api/competitor-prompt-analytics/` | List prompt analytics | `?competitor_id=1` |
| **GET** | `/api/competitor-prompt-analytics/gaps/` | **Find opportunity gaps** | `?domain_id=1` |
| **GET** | `/api/share-of-voice/` | **Get market share** | `?domain_id=1` |
| **GET** | `/api/competitor-analytics/trends/` | Get time-series trends | `?competitor_id=1&days=30` |

---

## ⚠️ **Common Issues & Solutions**

### **1. Competitor Stuck in INIT Status**
```bash
# Check if Celery worker is running
ps aux | grep celery

# Check competitor status
curl http://127.0.0.1:8001/api/competitors/1/

# Manually trigger processing
curl -X POST http://127.0.0.1:8001/api/competitors/1/process/
```

### **2. No Prompts Linked**
**Cause:** Domain doesn't have completed PromptAnalytics

**Solution:**
```bash
# Check if prompts have completed analytics
curl http://127.0.0.1:8001/api/prompts/status/1/
```

### **3. Processing Failed**
**Check Error:**
```bash
curl http://127.0.0.1:8001/api/competitors/1/
# Look at track_message field
```

### **4. Empty Analytics**
**Cause:** No competitor mentions found in responses

**Solution:** This is normal if competitor isn't mentioned. Check individual prompt analytics:
```bash
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/?competitor_id=1"
```

---

## ✅ **Testing Checklist**

- [ ] Create competitor
- [ ] List competitors
- [ ] Get competitor details
- [ ] Trigger processing
- [ ] Wait for processing to complete
- [ ] Check competitor status (should be COMP)
- [ ] Get competitor analytics
- [ ] List competitor-prompt analytics
- [ ] Find opportunity gaps
- [ ] Get share of voice analytics
- [ ] Get trends (if time-series data exists)

---

## 🎯 **Quick Test Script**

Save as `test_competitor_api.sh`:

```bash
#!/bin/bash

BASE_URL="http://127.0.0.1:8001/api"
DOMAIN_ID=1

echo "=== Creating Competitor ==="
COMPETITOR=$(curl -s -X POST $BASE_URL/competitors/ \
  -H "Content-Type: application/json" \
  -d "{\"domain\": $DOMAIN_ID, \"name\": \"Nike\", \"url\": \"https://www.nike.com\"}")

COMPETITOR_ID=$(echo $COMPETITOR | jq -r '.id')
echo "Created competitor ID: $COMPETITOR_ID"
echo ""

echo "=== Triggering Processing ==="
curl -s -X POST $BASE_URL/competitors/$COMPETITOR_ID/process/ | jq
echo ""

echo "=== Checking Status ==="
sleep 3
curl -s $BASE_URL/competitors/$COMPETITOR_ID/ | jq '.track_status, .track_message'
echo ""

echo "=== Getting Analytics ==="
curl -s $BASE_URL/competitors/$COMPETITOR_ID/analytics/ | jq '.statistics'
echo ""

echo "=== Share of Voice ==="
curl -s "$BASE_URL/share-of-voice/?domain_id=$DOMAIN_ID" | jq '.players[] | {name: .competitor_name, share: .share_percentage, position: .market_position}'
```

**Run:**
```bash
chmod +x test_competitor_api.sh
./test_competitor_api.sh
```

---

## 📚 **Documentation**

- **Full System Guide:** `COMPETITOR_PROCESSING_SYSTEM.md`
- **Implementation Summary:** `COMPETITOR_IMPLEMENTATION_SUMMARY.md`
- **API Migration:** `COMPETITOR_API_MIGRATION.md`
- **Optimization Details:** `COMPETITOR_ANALYTICS_OPTIMIZATION.md`

---

**Happy Testing!** 🚀

