# Competitor API Migration - Backend to Engine

## 📋 **Summary**

All competitor management APIs have been **moved from backend to engine** to centralize processing logic.

---

## 🔄 **API Endpoint Changes**

### **Before (Backend)**
```
http://127.0.0.1:8000/api/competitors/
http://127.0.0.1:8000/api/competitor-analytics/
http://127.0.0.1:8000/api/competitor-prompt-analytics/
```

### **After (Engine)**
```
http://127.0.0.1:8001/api/competitors/
http://127.0.0.1:8001/api/competitor-analytics/trends/
http://127.0.0.1:8001/api/competitor-prompt-analytics/
http://127.0.0.1:8001/api/share-of-voice/
```

**Key Change:** Use port **8001** (engine) instead of port **8000** (backend)

---

## 🌐 **Complete API Reference**

### **Competitor Management**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/competitors/` | List all competitors |
| GET | `/api/competitors/?domain_id=X` | Filter by domain |
| POST | `/api/competitors/` | Create competitor (auto-sets INIT) |
| GET | `/api/competitors/{id}/` | Get competitor details |
| PUT | `/api/competitors/{id}/` | Update competitor |
| DELETE | `/api/competitors/{id}/` | Delete competitor |
| **POST** | `/api/competitors/{id}/process/` | **Trigger processing** |
| **GET** | `/api/competitors/{id}/analytics/` | **Get detailed analytics** |

---

### **Competitor-Prompt Analytics**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/competitor-prompt-analytics/` | List all analytics |
| GET | `/api/competitor-prompt-analytics/?competitor_id=X` | Filter by competitor |
| GET | `/api/competitor-prompt-analytics/?domain_id=X` | Filter by domain |
| **GET** | `/api/competitor-prompt-analytics/gaps/?domain_id=X` | **Find opportunity gaps** |

---

### **Share of Voice & Trends**

| Method | Endpoint | Description |
|--------|----------|-------------|
| **GET** | `/api/share-of-voice/?domain_id=X` | **Get market share breakdown** |
| GET | `/api/competitor-analytics/trends/?competitor_id=X&days=30` | Get time-series data |

---

## 📝 **Example Usage**

### **1. Create Competitor (NEW BASE URL)**

```bash
curl -X POST http://127.0.0.1:8001/api/competitors/ \
  -H "Content-Type: application/json" \
  -d '{
    "domain": 1,
    "name": "Nike",
    "url": "https://www.nike.com"
  }'
```

**Response:**
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
  "created_at": "2025-11-05T12:00:00Z",
  "modified_at": "2025-11-05T12:00:00Z"
}
```

---

### **2. Trigger Processing**

```bash
curl -X POST http://127.0.0.1:8001/api/competitors/1/process/
```

**Response:**
```json
{
  "success": true,
  "message": "Processing started for competitor Nike",
  "competitor_id": 1,
  "track_status": "INIT",
  "task_id": "abc123..."
}
```

---

### **3. Get Detailed Analytics**

```bash
curl http://127.0.0.1:8001/api/competitors/1/analytics/
```

**Response:**
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

### **4. Find Opportunity Gaps**

```bash
curl "http://127.0.0.1:8001/api/competitor-prompt-analytics/gaps/?domain_id=1&competitor_id=1"
```

**Returns:** Prompts where competitor ranks in top 5

---

### **5. Get Share of Voice**

```bash
curl "http://127.0.0.1:8001/api/share-of-voice/?domain_id=1"
```

**Response:**
```json
{
  "domain_id": 1,
  "timestamp": "2025-11-05",
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
      "competitor": 1,
      "competitor_name": "Nike",
      "share_percentage": "30.00",
      "mention_count": 120,
      "market_position": 2
    }
  ]
}
```

---

## 📁 **Files Modified**

### **Engine (Added)**

| File | Changes |
|------|---------|
| `engine/core/serializers.py` | ✅ Added 4 competitor serializers |
| `engine/core/views.py` | ✅ Added 8 competitor endpoints |
| `engine/core/urls.py` | ✅ Added 8 URL patterns |

### **Backend (No Changes Required)**

- ✅ Models remain in backend (Competitor, CompetitorPromptAnalytics)
- ✅ Migrations remain in backend
- ✅ Backend views/serializers/URLs can be **removed** (optional cleanup)

---

## 🔧 **Migration Steps**

### **1. No Code Changes Needed**

All changes are already implemented! Just update your API calls.

### **2. Update Frontend/Client Code**

**Before:**
```javascript
const API_BASE = 'http://127.0.0.1:8000/api';
fetch(`${API_BASE}/competitors/`);
```

**After:**
```javascript
const API_BASE = 'http://127.0.0.1:8001/api';  // Changed port
fetch(`${API_BASE}/competitors/`);
```

---

## ✅ **Advantages of Engine-Based API**

1. ✅ **Centralized Processing**: All processing logic in one place
2. ✅ **Consistent with Domain/Prompt APIs**: Same pattern
3. ✅ **Direct Access to Processor**: No need to import across projects
4. ✅ **Simpler Architecture**: Backend = models, Engine = processing + API
5. ✅ **Better Performance**: No cross-project calls

---

## 📊 **Port Reference**

| Service | Port | Purpose |
|---------|------|---------|
| **Backend** | 8000 | Authentication, Organizations, Base Models |
| **Engine** | 8001 | **Processing, Analytics, Competitors** ⭐ |

---

## 🚀 **Quick Test**

```bash
# 1. Make sure engine is running
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
python manage.py runserver 0.0.0.0:8001

# 2. Test the endpoint
curl http://127.0.0.1:8001/api/competitors/

# Expected: List of competitors or empty array
```

---

## 📝 **Summary**

✅ **All competitor APIs moved to engine (port 8001)**
✅ **Models remain in backend**
✅ **Processing logic in engine/core/competitor_processor.py**
✅ **Consistent with existing domain/prompt APIs**
✅ **No database changes needed**
✅ **Update your client code to use port 8001**

**The migration is complete!** 🎉

