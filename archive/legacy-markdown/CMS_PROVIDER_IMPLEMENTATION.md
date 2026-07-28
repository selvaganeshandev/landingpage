# CMS Provider Management Implementation

## Overview
This document describes the implementation of CMS provider management system that allows managing multiple WordPress (and future CMS) providers per domain, with scheduling support for content publishing.

## Backend Implementation

### Models Created

#### 1. CMSProvider (`backend/content/models.py`)
- Stores CMS provider configurations per domain
- Supports multiple providers per domain
- Fields:
  - `domain`: ForeignKey to Domain
  - `provider_type`: Choice field (currently 'wordpress')
  - `name`: Display name for the provider
  - `settings`: JSONField for provider-specific settings (API URL, username, app_password, etc.)
  - `is_active`: Boolean for enabling/disabling
  - `is_default`: Boolean for default provider (only one per domain)

#### 2. ScheduledPublication (`backend/content/models.py`)
- Stores scheduled publications
- Fields:
  - `content`: ForeignKey to GeneratedContent
  - `cms_provider`: ForeignKey to CMSProvider
  - `scheduled_at`: DateTime for when to publish
  - `status`: Choice field (scheduled, publishing, published, failed, cancelled)
  - `wordpress_post_id`: ID after publication
  - `wordpress_url`: URL of published content
  - `error_message`: Error tracking
  - `published_at`: Actual publication time

### API Endpoints

#### CMS Provider Management
- `GET /api/content/cms-providers/` - List all CMS providers (optional `?domain_id=X`)
- `POST /api/content/cms-providers/` - Create new CMS provider
- `GET /api/content/cms-providers/{id}/` - Get specific provider
- `PUT /api/content/cms-providers/{id}/` - Update provider
- `DELETE /api/content/cms-providers/{id}/` - Delete provider
- `POST /api/content/cms-providers/{id}/test/` - Test connection

#### Publishing
- `POST /api/content/publish/` - Publish content (replaces old `/content/publish/`)
  - Request body:
    ```json
    {
      "content_id": 123,
      "cms_provider_id": 456,
      "publish_now": true,
      "scheduled_at": "2025-12-10T00:00:00Z" // optional if publish_now is true
    }
    ```

### Removed
- Old static `publish_to_wordpress` endpoint (removed hardcoded credentials)

## Frontend Implementation

### Components Created

#### 1. CMSProviderManager (`frontend/src/components/CMSProviderManager.tsx`)
- Manages CMS providers for selected domain
- Features:
  - List all providers for domain
  - Add new provider (WordPress)
  - Edit existing provider
  - Delete provider
  - Test connection
  - Set default provider
  - Enable/disable providers

#### 2. PublishDialog (`frontend/src/components/PublishDialog.tsx`)
- Publishing dialog with scheduling UI (similar to YouTube)
- Features:
  - Select CMS provider
  - "Publish Now" checkbox
  - Date picker (when scheduling)
  - Time picker (when scheduling)
  - Timezone display
  - Status information
  - Validation

### Pages Updated

#### 1. AutomationSettings (`frontend/src/pages/AutomationSettings.tsx`)
- Added CMS Provider Management section
- Removed old "Preferred CMS Provider" dropdown
- Integrated CMSProviderManager component

#### 2. ContentEditor (`frontend/src/pages/ContentEditor.tsx`)
- Updated publish button to open PublishDialog
- Removed old direct publish function
- Auto-saves content before opening publish dialog

### API Methods Added (`frontend/src/services/api.ts`)
- `getCMSProviders(params?)` - Get CMS providers
- `createCMSProvider(data)` - Create provider
- `updateCMSProvider(id, data)` - Update provider
- `deleteCMSProvider(id)` - Delete provider
- `testCMSProviderConnection(id)` - Test connection
- `publishContent(data)` - Publish with scheduling

## Database Migration

Run the following to create the new tables:

```bash
cd backend
python3 manage.py makemigrations content
python3 manage.py migrate content
```

## Usage Flow

### 1. Configure CMS Provider
1. Navigate to `/automation`
2. Select a domain (if not already selected)
3. Click "Add Provider" in CMS Provider Management section
4. Fill in WordPress credentials:
   - Provider Name
   - WordPress Site URL
   - WordPress API URL
   - Username
   - Application Password
   - Content Type (Pages/Posts)
5. Optionally set as default and active
6. Click "Create"
7. Test connection using the test button

### 2. Publish Content
1. Open content in Content Editor (`/content-editor/{id}`)
2. Click "Publish" button
3. Select CMS provider from dropdown
4. Choose:
   - **Publish Now**: Check "Publish Now" checkbox → Click "Publish Now"
   - **Schedule**: Uncheck "Publish Now" → Select date and time → Click "Schedule"
5. Content will be published or scheduled accordingly

## Scheduled Publications

- Scheduled publications are stored in `ScheduledPublication` model
- Status tracking: `scheduled` → `publishing` → `published` or `failed`
- WordPress scheduled posts use `status: "future"` with `date` field
- A background task (Celery) should be set up to process scheduled publications

## Future Enhancements

1. **Celery Task for Scheduled Publishing**
   - Create periodic task to check and publish scheduled content
   - Update status accordingly

2. **Additional CMS Providers**
   - Ghost CMS
   - Contentful
   - Strapi
   - Webflow

3. **Bulk Publishing**
   - Publish multiple content items at once

4. **Publishing History**
   - View all published content with timestamps
   - Retry failed publications

5. **Content Mapping**
   - Map content fields to CMS-specific fields
   - Category/tag assignment
   - Featured image upload

## Security Notes

- Application passwords are stored in JSONField (should be encrypted in production)
- Consider using Django's `cryptography` or environment variables for sensitive data
- Validate domain ownership before allowing CMS provider configuration
- Test connections before saving credentials

