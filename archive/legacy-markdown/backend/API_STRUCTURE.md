# LLM Monitor Backend - New App Structure

## Overview
The backend has been restructured into separate Django apps for better organization and maintainability. Each app handles specific functionality with its own models, views, serializers, and URLs.

## App Structure

### 1. **accounts** App
**Purpose**: User and organization management
**Models**: 
- `Organisation` - Companies/entities using the system
- `Account` - Custom user model with roles

**Endpoints**:
- `GET /accounts/organisations/` - List organisations
- `POST /accounts/organisations/` - Create organisation
- `GET /accounts/organisations/{id}/` - Get organisation details
- `PUT /accounts/organisations/{id}/` - Update organisation
- `DELETE /accounts/organisations/{id}/` - Delete organisation
- `GET /accounts/organisations/{id}/accounts/` - Get organisation's accounts
- `GET /accounts/accounts/` - List accounts
- `POST /accounts/accounts/` - Create account
- `GET /accounts/accounts/{id}/` - Get account details
- `PUT /accounts/accounts/{id}/` - Update account
- `DELETE /accounts/accounts/{id}/` - Delete account
- `POST /accounts/login/` - User login
- `POST /accounts/logout/` - User logout
- `GET /accounts/profile/` - Get user profile
- `PUT /accounts/profile/update/` - Update user profile

### 2. **domains** App
**Purpose**: Domain monitoring and management
**Models**: 
- `Domain` - Websites/domains being monitored

**Endpoints**:
- `GET /domains/` - List domains
- `POST /domains/` - Create domain
- `GET /domains/{id}/` - Get domain details
- `PUT /domains/{id}/` - Update domain
- `DELETE /domains/{id}/` - Delete domain
- `GET /domains/{id}/keywords/` - Get domain's keywords

### 3. **keywords** App
**Purpose**: Keyword tracking and management
**Models**: 
- `Keyword` - Keywords being tracked

**Endpoints**:
- `GET /keywords/` - List keywords
- `POST /keywords/` - Create keyword
- `GET /keywords/{id}/` - Get keyword details
- `PUT /keywords/{id}/` - Update keyword
- `DELETE /keywords/{id}/` - Delete keyword

### 4. **prompts** App
**Purpose**: Prompt management and analytics
**Models**: 
- `PromptCluster` - Clusters of prompts
- `Prompt` - Individual prompts
- `PromptAnalytics` - Analytics data for prompts

**Endpoints**:
- `GET /prompts/clusters/` - List prompt clusters
- `POST /prompts/clusters/` - Create prompt cluster
- `GET /prompts/clusters/{id}/` - Get cluster details
- `PUT /prompts/clusters/{id}/` - Update cluster
- `DELETE /prompts/clusters/{id}/` - Delete cluster
- `GET /prompts/clusters/{id}/prompts/` - Get cluster's prompts
- `GET /prompts/` - List prompts
- `POST /prompts/` - Create prompt
- `GET /prompts/{id}/` - Get prompt details
- `PUT /prompts/{id}/` - Update prompt
- `DELETE /prompts/{id}/` - Delete prompt
- `GET /prompts/{id}/analytics/` - Get prompt's analytics
- `GET /prompts/analytics/` - List prompt analytics
- `POST /prompts/analytics/` - Create prompt analytics
- `GET /prompts/analytics/{id}/` - Get analytics details
- `PUT /prompts/analytics/{id}/` - Update analytics
- `DELETE /prompts/analytics/{id}/` - Delete analytics

## Database Models

### Organisation Model
- `id` (Primary Key)
- `name` (CharField, max_length=255)
- `industry` (CharField, max_length=100)
- `team_count` (PositiveIntegerField, default=1)
- `created_at` (DateTimeField, auto_now_add=True)
- `modified_at` (DateTimeField, auto_now=True)

### Account Model (Custom User)
- `id` (Primary Key)
- `email` (EmailField, unique=True)
- `first_name`, `last_name` (CharField)
- `role` (CharField, choices: 'admin', 'user')
- `organisation` (ForeignKey to Organisation)
- `created_at` (DateTimeField, auto_now_add=True)
- `modified_at` (DateTimeField, auto_now=True)
- Standard Django User fields

### Domain Model
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

### Keyword Model
- `id` (Primary Key)
- `keyword` (CharField, max_length=255)
- `domain` (ForeignKey to Domain)
- `organisation` (ForeignKey to Organisation)
- `created_at` (DateTimeField, auto_now_add=True)
- `modified_at` (DateTimeField, auto_now=True)

### PromptCluster Model
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

### Prompt Model
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

### PromptAnalytics Model
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

## Features

### ✅ **Modular Architecture**
- Separate apps for different functionalities
- Clean separation of concerns
- Easy to maintain and extend

### ✅ **Function-Based Views**
- All endpoints use function-based views
- Consistent error handling
- Easy to understand and modify

### ✅ **PostgreSQL Naming Conventions**
- All tables use snake_case naming
- Proper foreign key relationships
- Unique constraints where appropriate

### ✅ **Django Admin Integration**
- All models registered with admin
- Custom list displays and search
- Proper field organization

### ✅ **REST API**
- Full CRUD operations for all models
- Nested endpoints for relationships
- JSON responses with proper serialization

### ✅ **Authentication System**
- Custom user model with roles
- Login/logout endpoints
- Profile management

## Example API Usage

### Create an Organisation
```bash
curl -X POST http://localhost:8000/accounts/organisations/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Corp",
    "industry": "Technology",
    "team_count": 50
  }'
```

### Create a Domain
```bash
curl -X POST http://localhost:8000/domains/ \
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
curl -X POST http://localhost:8000/keywords/ \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "AI technology",
    "domain": 1,
    "organisation": 1
  }'
```

### Create a Prompt Cluster
```bash
curl -X POST http://localhost:8000/prompts/clusters/ \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_id": "cluster_001",
    "domain": 1,
    "organisation": 1,
    "total_mentions": 50,
    "visibility_score": 75.5
  }'
```

## Development Setup

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

4. **Run development server:**
   ```bash
   python manage.py runserver
   ```

## Admin Interface
Access the Django admin at: `http://localhost:8000/admin/`

All models are registered with comprehensive admin interfaces for easy management.
