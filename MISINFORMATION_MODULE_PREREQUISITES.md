# Misinformation Alerts Module - Prerequisites

## Overview

Detect and correct AI hallucinations about your brand by analyzing LLM responses, crawling cited sources, and comparing claims against actual content.

### Summary Cards (Dashboard)
- **Total Detected** - Total misinformation instances detected
- **Broken Links** - Citation URLs that return 404/5xx or are inaccessible
- **Misinformation** - Factually incorrect claims about the brand
- **Outdated Information** - Information that is no longer current

---

## Database Schema

### New Tables

#### 1. `misinformation_scans`
Track scan runs per domain.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BigInt PK | Primary key |
| `domain_id` | FK → domains | Domain being scanned |
| `status` | varchar(20) | pending/running/completed/failed |
| `started_at` | timestamp | Scan start time |
| `completed_at` | timestamp | Scan completion time |
| `total_prompts_scanned` | integer | Number of prompts processed |
| `total_citations_found` | integer | Number of URLs found |
| `total_alerts_generated` | integer | Number of alerts created |
| `created_at` | timestamp | Record creation time |

#### 2. `citation_urls`
Store all cited URLs from LLM responses.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BigInt PK | Primary key |
| `domain_id` | FK → domains | Associated domain |
| `prompt_analytics_id` | FK → prompt_analytics | Source prompt result |
| `url` | text | Full URL |
| `url_hash` | varchar(64) | SHA256 hash for deduplication |
| `is_crawlable` | boolean | Whether URL can be crawled |
| `crawl_status` | varchar(20) | pending/success/failed/blocked |
| `crawl_error` | text | Error message if failed |
| `http_status_code` | integer | HTTP response code |
| `last_crawled_at` | timestamp | Last successful crawl time |
| `created_at` | timestamp | Record creation time |
| `modified_at` | timestamp | Last modification time |

#### 3. `citation_content`
Cached content from crawled URLs (overwritten on updates, no history).

| Column | Type | Description |
|--------|------|-------------|
| `id` | BigInt PK | Primary key |
| `citation_url_id` | FK → citation_urls | Associated URL (OneToOne) |
| `raw_html` | text | Original HTML content |
| `extracted_text` | text | Clean extracted text |
| `page_title` | varchar(500) | Page title |
| `meta_description` | text | Meta description |
| `publish_date` | date | Content publish date (if found) |
| `content_hash` | varchar(64) | SHA256 hash of extracted_text |
| `crawled_at` | timestamp | When content was fetched |

#### 4. `misinformation_alerts`
Detected issues and their status.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BigInt PK | Primary key |
| `domain_id` | FK → domains | Associated domain |
| `prompt_id` | FK → prompts | Source prompt |
| `prompt_analytics_id` | FK → prompt_analytics | Source prompt result |
| `citation_url_id` | FK → citation_urls | Related citation (nullable) |
| `alert_type` | varchar(20) | misinformation/broken_link/outdated |
| `severity` | varchar(10) | low/medium/high/critical |
| `llm_claim` | text | What the LLM stated |
| `source_content` | text | Relevant content from source |
| `explanation` | text | AI-generated explanation of the issue |
| `status` | varchar(20) | new/reviewed/resolved/dismissed |
| `reviewed_by_id` | FK → accounts | User who reviewed (nullable) |
| `reviewed_at` | timestamp | When reviewed (nullable) |
| `created_at` | timestamp | Record creation time |
| `modified_at` | timestamp | Last modification time |

#### 5. `misinformation_analytics`
Daily aggregated metrics per domain.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BigInt PK | Primary key |
| `domain_id` | FK → domains | Associated domain |
| `date` | date | Analytics date |
| `total_detected` | integer | Total alerts for the day |
| `broken_links_count` | integer | Broken link alerts |
| `misinformation_count` | integer | Misinformation alerts |
| `outdated_count` | integer | Outdated info alerts |
| `by_severity` | jsonb | {low: x, medium: x, high: x, critical: x} |
| `created_at` | timestamp | Record creation time |

---

## Source Data (Existing Tables)

| Table | Usage |
|-------|-------|
| `prompt_analytics` | LLM responses with `response_text`, `citations` (jsonb), `brand_mentioned`, `domain_id`, `prompt_id` |
| `prompts` | Prompt definitions |
| `domains` | Brand/domain context for comparison |

---

## Backend Services

### 1. URL Extraction Service
- Parse `response_text` and `citations` from `prompt_analytics`
- Extract all URLs using regex patterns
- Deduplicate URLs using hash

### 2. Web Crawler Service
- Crawl URLs with Cloudflare bypass support
- Rate limiting (configurable, default: 10 requests/minute)
- Timeout handling (default: 30 seconds)
- User-agent rotation
- Skip URLs that fail after 3 retries

### 3. Content Comparison Service
- Use Claude API to compare LLM claims vs source content
- Detect factual misinformation
- Detect outdated information (dates, versions, pricing, features)
- Generate severity rating and explanation

### 4. Link Validator
- Check HTTP status codes
- Detect 404s, 5xx errors, timeouts
- Mark as broken_link alert

### 5. Celery Task (Periodic)
- Triggered when `prompt_analytics` is updated
- Runs via Django signal on `prompt_analytics` post_save
- Can also be triggered manually via API

---

## External Dependencies

### Already Installed (Verify)
| Package | Purpose |
|---------|---------|
| `beautifulsoup4` | HTML parsing |
| `httpx` | Async HTTP client |
| `celery` | Task queue |
| `anthropic` | Claude API |

### New Dependencies Required
| Package | Purpose | Notes |
|---------|---------|-------|
| `cloudscraper` | Cloudflare bypass | Successor to cloudflare-scrape, actively maintained |
| `trafilatura` | Article text extraction | Better than newspaper3k for modern sites |
| `lxml` | Fast HTML/XML parsing | Required by trafilatura |

#### About Cloudscraper
- **Repository**: https://github.com/VeNoMouS/cloudscraper
- **PyPI**: https://pypi.org/project/cloudscraper/
- **Features**:
  - Bypasses Cloudflare's anti-bot page ("Checking your browser...")
  - Supports Cloudflare v1, v2, and v3 challenges
  - Works like standard requests library
  - JavaScript challenge solving via Node.js (recommended) or native Python
- **Limitations**:
  - May not bypass Cloudflare Turnstile CAPTCHA
  - ~70% success rate with Node.js, ~30% with native Python
  - For sites with advanced protection, URLs will be marked as `blocked`
- **Installation**: `pip install cloudscraper`

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     prompt_analytics updated                      │
│                  (new LLM results from engine)                   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Django Signal triggers Celery task                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Extract Citation URLs from response_text            │
│                    and citations jsonb field                     │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Crawl new/updated URLs                        │
│         (using cloudscraper for Cloudflare bypass)              │
│         (skip if content_hash unchanged)                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Compare LLM Claims vs Source Content                │
│                    (using Claude API)                            │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Generate/Update Alerts                         │
│        (misinformation / broken_link / outdated)                │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Update misinformation_analytics                     │
│                   (daily aggregates)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Severity Levels

| Severity | Criteria | Examples |
|----------|----------|----------|
| **Critical** | Completely false claims about brand | Wrong products, false legal issues, fabricated partnerships |
| **High** | Significant factual errors | Wrong pricing, incorrect features, false contact info |
| **Medium** | Outdated information | Old versions, discontinued products, expired promotions |
| **Low** | Minor issues | Broken citation links, minor inaccuracies, typos in brand name |

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/misinformation/dashboard/` | Summary cards data (totals by type) |
| GET | `/misinformation/alerts/` | List alerts with filters (type, severity, status, date range) |
| GET | `/misinformation/alerts/<id>/` | Alert detail with full context |
| PATCH | `/misinformation/alerts/<id>/` | Update status (reviewed/resolved/dismissed) |
| POST | `/misinformation/scan/` | Trigger manual scan for a domain |
| GET | `/misinformation/scan/<id>/` | Get scan status and progress |
| GET | `/misinformation/analytics/` | Historical trends (daily/weekly/monthly) |

---

## File Structure

```
backend/
├── misinformation/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py              # Database models
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # API views
│   ├── urls.py                # URL routing
│   ├── signals.py             # Django signals for prompt_analytics
│   ├── tasks.py               # Celery tasks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_extractor.py   # Extract URLs from LLM responses
│   │   ├── crawler.py         # Web crawler with cloudscraper
│   │   ├── content_parser.py  # Extract text using trafilatura
│   │   ├── comparator.py      # Claude-based comparison
│   │   └── link_validator.py  # HTTP status checker
│   └── migrations/
│       └── 0001_initial.py
```

---

## Configuration (Environment Variables)

```env
# Misinformation Module
MISINFO_CRAWL_RATE_LIMIT=10          # Requests per minute
MISINFO_CRAWL_TIMEOUT=30             # Seconds
MISINFO_CRAWL_MAX_RETRIES=3          # Retry attempts
MISINFO_CONTENT_MAX_LENGTH=50000     # Max chars to store
MISINFO_COMPARISON_MODEL=claude-3-haiku-20240307  # Claude model for comparison
```

---

## Open Decisions

1. **History Retention**: Currently designed to overwrite content (no history). Should we add versioning for citation_content?
2. **Notifications**: Should critical/high severity alerts trigger email notifications?
3. **Rate Limiting**: Default 10 req/min - adjust based on testing?

---

## References

- [cloudscraper GitHub](https://github.com/VeNoMouS/cloudscraper)
- [cloudscraper PyPI](https://pypi.org/project/cloudscraper/)
- [Bypassing Cloudflare with Cloudscraper (2024)](https://datawookie.dev/blog/2024/07/bypassing-cloudflare-with-cloudscraper/)
- [Cloudscraper for Python (2025 Guide)](https://evomi.com/blog/cloudscraper-python-cloudflare-proxies-2025)
- [trafilatura Documentation](https://trafilatura.readthedocs.io/)
