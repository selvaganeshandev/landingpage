# LLM Monitor API Documentation

## Models Created

### 1. Organisation Model
- **Table**: `organisations`
- **Fields**:
  - `id` (Primary Key)
  - `name` (CharField, max_length=255)
  - `industry` (CharField, max_length=100)
  - `team_count` (PositiveIntegerField, default=1)
  - `created_at` (DateTimeField, auto_now_add=True)
  - `modified_at` (DateTimeField, auto_now=True)

### 2. Account Model (Custom User Model)
- **Table**: `accounts`
- **Fields**:
  - `id` (Primary Key)
  - `email` (EmailField, unique=True)
  - `first_name`, `last_name` (CharField)
  - `role` (CharField, choices: 'admin', 'user')
  - `organisation` (ForeignKey to Organisation)
  - `created_at` (DateTimeField, auto_now_add=True)
  - `modified_at` (DateTimeField, auto_now=True)
  - Standard Django User fields (password, is_active, etc.)

### 3. Domain Model
- **Table**: `domains`
- **Fields**:
  - `id` (Primary Key)
  - `name` (CharField, max_length=255)
  - `url` (URLField)
  - `organisation` (ForeignKey to Organisation)
  - `total_mentions` (PositiveIntegerField, default=0)
  - `total_citations` (PositiveIntegerField, default=0)
  - `visibility_score` (DecimalField, max_digits=5, decimal_places=2)
  - `average_position` (DecimalField, max_digits=8, decimal_places=2)
  - `active_alerts` (PositiveIntegerField, default=0)
  - `sentiment` (CharField, choices: 'positive', 'neutral', 'negative')
  - `sentiment_score` (DecimalField, max_digits=3, decimal_places=2)
  - `created_at` (DateTimeField, auto_now_add=True)
  - `modified_at` (DateTimeField, auto_now=True)

### 4. Keyword Model
- **Table**: `keywords`
- **Fields**:
  - `id` (Primary Key)
  - `keyword` (CharField, max_length=255)
  - `domain` (ForeignKey to Domain)
  - `organisation` (ForeignKey to Organisation)
  - `created_at` (DateTimeField, auto_now_add=True)
  - `modified_at` (DateTimeField, auto_now=True)

### 5. PromptCluster Model
- **Table**: `prompt_clusters`
- **Fields**:
  - `id` (Primary Key)
  - `cluster_id` (CharField, max_length=100, unique=True)
  - `domain` (ForeignKey to Domain)
  - `organisation` (ForeignKey to Organisation)
  - `total_mentions` (PositiveIntegerField, default=0)
  - `total_citations` (PositiveIntegerField, default=0)
  - `visibility_score` (DecimalField, max_digits=5, decimal_places=2)
  - `average_position` (DecimalField, max_digits=8, decimal_places=2)
  - `created_at` (DateTimeField, auto_now_add=True)
  - `modified_at` (DateTimeField, auto_now=True)

### 6. Prompt Model
- **Table**: `prompts`
- **Fields**:
  - `id` (Primary Key)
  - `prompt` (TextField)
  - `cluster` (ForeignKey to PromptCluster)
  - `domain` (ForeignKey to Domain)
  - `organisation` (ForeignKey to Organisation)
  - `track_status` (CharField, choices: 'active', 'paused', 'archived')
  - `type` (CharField, choices: 'primary', 'secondary')
  - `total_mentions` (PositiveIntegerField, default=0)
  - `total_citations` (PositiveIntegerField, default=0)
  - `visibility_score` (DecimalField, max_digits=5, decimal_places=2)
  - `average_position` (DecimalField, max_digits=8, decimal_places=2)
  - `created_at` (DateTimeField, auto_now_add=True)
  - `modified_at` (DateTimeField, auto_now=True)

### 7. PromptAnalytics Model
- **Table**: `prompt_analytics`
- **Fields**:
  - `id` (Primary Key)
  - `prompt` (ForeignKey to Prompt)
  - `domain` (ForeignKey to Domain)
  - `organisation` (ForeignKey to Organisation)
  - `model_name` (CharField, max_length=100)
  - `total_mentions` (PositiveIntegerField, default=0)
  - `total_citations` (PositiveIntegerField, default=0)
  - `visibility_score` (DecimalField, max_digits=5, decimal_places=2)
  - `average_position` (DecimalField, max_digits=8, decimal_places=2)
  - `sentiment` (CharField, choices: 'positive', 'neutral', 'negative')
  - `sentiment_score` (DecimalField, max_digits=3, decimal_places=2)
  - `context_summary` (TextField, blank=True)
  - `created_at` (DateTimeField, auto_now_add=True)
  - `modified_at` (DateTimeField, auto_now=True)

## API Endpoints

### Base URL: `http://localhost:8000/api/`

#### Test Endpoints
- `GET /api/test/` - Test endpoint
- `GET /api/health/` - Health check
- `POST /api/health/` - Health check with data

#### Organisations
- `GET /api/organisations/` - List all organisations
- `POST /api/organisations/` - Create organisation
- `GET /api/organisations/{id}/` - Get organisation details
- `PUT /api/organisations/{id}/` - Update organisation
- `DELETE /api/organisations/{id}/` - Delete organisation
- `GET /api/organisations/{id}/domains/` - Get organisation's domains
- `GET /api/organisations/{id}/accounts/` - Get organisation's accounts

#### Accounts
- `GET /api/accounts/` - List all accounts
- `POST /api/accounts/` - Create account
- `GET /api/accounts/{id}/` - Get account details
- `PUT /api/accounts/{id}/` - Update account
- `DELETE /api/accounts/{id}/` - Delete account

#### Domains
- `GET /api/domains/` - List all domains
- `POST /api/domains/` - Create domain
- `GET /api/domains/{id}/` - Get domain details
- `PUT /api/domains/{id}/` - Update domain
- `DELETE /api/domains/{id}/` - Delete domain
- `GET /api/domains/{id}/keywords/` - Get domain's keywords

#### Keywords
- `GET /api/keywords/` - List all keywords
- `POST /api/keywords/` - Create keyword
- `GET /api/keywords/{id}/` - Get keyword details
- `PUT /api/keywords/{id}/` - Update keyword
- `DELETE /api/keywords/{id}/` - Delete keyword

#### PromptClusters
- `GET /api/prompt-clusters/` - List all prompt clusters
- `POST /api/prompt-clusters/` - Create prompt cluster
- `GET /api/prompt-clusters/{id}/` - Get prompt cluster details
- `PUT /api/prompt-clusters/{id}/` - Update prompt cluster
- `DELETE /api/prompt-clusters/{id}/` - Delete prompt cluster
- `GET /api/prompt-clusters/{id}/prompts/` - Get cluster's prompts

#### Prompts
- `GET /api/prompts/` - List all prompts
- `POST /api/prompts/` - Create prompt
- `GET /api/prompts/{id}/` - Get prompt details
- `PUT /api/prompts/{id}/` - Update prompt
- `DELETE /api/prompts/{id}/` - Delete prompt
- `GET /api/prompts/{id}/analytics/` - Get prompt's analytics

#### PromptAnalytics
- `GET /api/prompt-analytics/` - List all prompt analytics
- `POST /api/prompt-analytics/` - Create prompt analytics
- `GET /api/prompt-analytics/{id}/` - Get prompt analytics details
- `PUT /api/prompt-analytics/{id}/` - Update prompt analytics
- `DELETE /api/prompt-analytics/{id}/` - Delete prompt analytics

## Example API Usage

### Create an Organisation
```bash
curl -X POST http://localhost:8000/api/organisations/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Corp",
    "industry": "Technology",
    "team_count": 50
  }'
```

### Create a Domain
```bash
curl -X POST http://localhost:8000/api/domains/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Corp Website",
    "url": "https://techcorp.com",
    "organisation": 1,
    "total_mentions": 100,
    "visibility_score": 85.5,
    "sentiment": "positive"
  }'
```

### Create a Keyword
```bash
curl -X POST http://localhost:8000/api/keywords/ \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "AI technology",
    "domain": 1,
    "organisation": 1
  }'
```

### Create a Prompt Cluster
```bash
curl -X POST http://localhost:8000/api/prompt-clusters/ \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_id": "cluster_001",
    "domain": 1,
    "organisation": 1,
    "total_mentions": 50,
    "visibility_score": 75.5
  }'
```

### Create a Prompt
```bash
curl -X POST http://localhost:8000/api/prompts/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the future of artificial intelligence?",
    "cluster": 1,
    "domain": 1,
    "organisation": 1,
    "track_status": "active",
    "type": "primary"
  }'
```

### Create Prompt Analytics
```bash
curl -X POST http://localhost:8000/api/prompt-analytics/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": 1,
    "domain": 1,
    "organisation": 1,
    "model_name": "GPT-4",
    "total_mentions": 25,
    "sentiment": "positive",
    "sentiment_score": 0.8,
    "context_summary": "Discussion about AI future prospects"
  }'
```

## Database Configuration

### Current Setup (SQLite)
The project is currently configured to use SQLite for development. The database file is located at `backend/db.sqlite3`.

### PostgreSQL Setup
To switch to PostgreSQL, uncomment the PostgreSQL configuration in `settings.py` and ensure:

1. PostgreSQL is installed and running
2. Create the database: `CREATE DATABASE llm_monitor;`
3. Grant permissions to the user: `arun`
4. Update the `.env` file with correct credentials

## Admin Interface

Access the Django admin at: `http://localhost:8000/admin/`

All models are registered with the admin interface for easy management.

## Naming Conventions

- **Database Tables**: Snake_case (e.g., `organisations`, `accounts`, `domains`, `keywords`)
- **Model Fields**: Snake_case (e.g., `created_at`, `modified_at`, `total_mentions`)
- **API Endpoints**: Kebab-case (e.g., `/api/organisations/`, `/api/accounts/`)
- **Foreign Keys**: Descriptive names (e.g., `organisation`, `domain`)

## Features

- ✅ Custom User Model (Account)
- ✅ Proper Foreign Key Relationships
- ✅ Timestamps on all models
- ✅ Django Admin Integration
- ✅ REST API with ViewSets
- ✅ Serializers for JSON responses
- ✅ Pagination support
- ✅ CORS configuration
- ✅ PostgreSQL naming conventions
