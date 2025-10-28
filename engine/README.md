# LLM Monitor Engine

A Django-based processing engine for the LLM Monitor system that handles domain processing, keyword scraping, and prompt generation using multithreading.

## Features

- **Domain Processing**: Processes domains with status "INIT" using multithreading (max 10 concurrent)
- **Keyword Scraping**: Uses DataForSEO API to retrieve 50 related keywords per domain
- **Prompt Generation**: Uses ChatGPT API to convert keywords into prompts
- **NLP Grouping**: Groups prompts into sets with primary and secondary prompts
- **REST API**: Provides API endpoints for monitoring and control
- **Database Integration**: Stores results in shared PostgreSQL database

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Main Django   │    │ Processing      │
│   Project       │◄──►│ Engine Django   │
│   (Web App)     │    │ Project         │
│                 │    │                 │
│ - Authentication│    │ - Domain        │
│ - UI/API        │    │   Processing    │
│ - Domain Mgmt   │    │ - Keyword       │
│ - User Mgmt     │    │   Scraping      │
└─────────────────┘    │ - Prompt        │
                       │   Generation    │
                       │ - NLP Grouping  │
                       └─────────────────┘
```

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Setup**:
   - Ensure PostgreSQL is running
   - The engine connects to the same database as the main project
   - Run migrations: `python manage.py migrate`

3. **Environment Variables**:
   - Set `DATAFORSEO_USERNAME` and `DATAFORSEO_PASSWORD` in settings
   - Set `OPENAI_API_KEY` in settings

## Usage

### Start the Engine

```bash
# Method 1: Using the startup script
python start_engine.py

# Method 2: Using Django management command
python manage.py start_processor

# Method 3: Run as daemon
python manage.py start_processor --daemon
```

### API Endpoints

- `GET /api/status/` - Get processing status
- `POST /api/start/` - Start processing a domain
- `GET /api/domains/` - List all domains
- `GET /api/domains/{id}/` - Get domain details
- `POST /api/domains/schedule/` - Schedule domain for processing
- `POST /api/domains/reset/` - Reset domain to INIT status

### Example API Usage

```bash
# Get processing status
curl http://localhost:8001/api/status/

# Start processing domain ID 1
curl -X POST http://localhost:8001/api/start/ \
  -H "Content-Type: application/json" \
  -d '{"domain_id": 1}'

# List domains with COMP status
curl http://localhost:8001/api/domains/?status=COMP
```

## Processing Flow

1. **Domain Selection**: Engine checks for domains with status "SCHD"
2. **Keyword Scraping**: Uses DataForSEO API to get 50 keywords
3. **Keyword Storage**: Stores keywords in the database
4. **Prompt Generation**: Uses ChatGPT to create prompts from keywords
5. **NLP Grouping**: Groups prompts using ChatGPT's NLP capabilities
6. **Database Storage**: Stores prompt groups and prompts
7. **Status Update**: Updates domain status to "COMP" or "FAIL"

## Configuration

### Settings

```python
# Maximum concurrent domains (default: 10)
MAX_CONCURRENT_DOMAINS = 10

# DataForSEO credentials
DATAFORSEO_USERNAME = "your_username"
DATAFORSEO_PASSWORD = "your_password"

# OpenAI API key
OPENAI_API_KEY = "your_api_key"

# Celery settings for background processing
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

### Domain Status Flow

```
INIT → SCHD → PROC → COMP
  ↓      ↓      ↓      ↓
Initial Scheduled Processing Completed
  ↓      ↓      ↓      ↓
Reset   Auto   Manual  Done
```

## Monitoring

The engine provides real-time monitoring through:

- **Processing Status API**: Shows active threads and domain counts
- **Domain Status Tracking**: Each domain has detailed status information
- **Error Handling**: Failed domains are marked with error messages
- **Logging**: Console output for debugging and monitoring

## Error Handling

- **API Failures**: DataForSEO and ChatGPT API failures are handled gracefully
- **Database Errors**: Transaction rollback on database errors
- **Thread Management**: Proper cleanup of failed threads
- **Status Updates**: Failed domains are marked with error details

## Development

### Project Structure

```
engine/
├── llm_monitor_engine/     # Django project settings
├── domain_processor/       # Main processing app
│   ├── management/         # Django management commands
│   ├── rest_client.py     # DataForSEO API client
│   ├── chatgpt_client.py  # OpenAI API client
│   ├── domain_processor.py # Main processing logic
│   ├── views.py           # API endpoints
│   └── serializers.py     # API serializers
├── shared_models/         # Shared database models
├── requirements.txt       # Python dependencies
├── start_engine.py       # Startup script
└── README.md             # This file
```

### Adding New Features

1. **New API Endpoints**: Add to `domain_processor/views.py`
2. **New Models**: Add to `shared_models/models.py`
3. **New Processing Logic**: Extend `DomainProcessor` class
4. **New External APIs**: Create new client classes

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and accessible
2. **API Keys**: Verify DataForSEO and OpenAI credentials
3. **Thread Limits**: Adjust `MAX_CONCURRENT_DOMAINS` if needed
4. **Memory Usage**: Monitor memory usage with high concurrent processing

### Logs

- Check console output for processing status
- Database logs for data storage issues
- API response logs for external service issues

## Production Deployment

1. **Use Process Manager**: Use systemd, supervisor, or similar
2. **Environment Variables**: Set production API keys and database URLs
3. **Monitoring**: Set up monitoring for the processing engine
4. **Scaling**: Deploy multiple engine instances for higher throughput
5. **Load Balancing**: Use load balancer for multiple engine instances
