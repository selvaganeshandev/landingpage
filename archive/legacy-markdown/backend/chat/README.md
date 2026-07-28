# 🤖 Agentic ChatBot Module

Intelligent chat interface with function calling capabilities for the LLM Monitor platform.

## Overview

The Agentic ChatBot allows users to interact with their domain data using natural language. It uses OpenAI's GPT-4o-mini model with function calling to:

- Query domain analytics and metrics
- Analyze competitors
- Review prompt performance
- Identify content gaps
- Get sentiment analysis
- Create monitoring rules
- And more!

## Architecture

```
User Message → ChatViewSet → OpenAI GPT-4o-mini (with tools)
                  ↓
            Function Calls → ChatbotService
                  ↓
            Domain Data (PostgreSQL)
                  ↓
            AI Response → User
```

## Security

- **Domain Access Validation**: Users can only chat about domains they have access to
- **Multi-tenant Isolation**: All queries scoped to user's organisation
- **Role-based Access**: Respects super_admin/admin/user roles
- **DomainAccess Check**: Validates explicit domain permissions

## Available Functions

1. **get_domain_analytics** - Get comprehensive domain metrics
2. **get_competitor_analysis** - Compare with competitors
3. **get_prompt_performance** - Analyze tracked prompts
4. **get_content_gaps** - Identify opportunities
5. **get_sentiment_analysis** - Sentiment breakdown
6. **get_top_mentions** - Recent/relevant mentions
7. **get_platform_breakdown** - Platform-specific metrics
8. **create_monitoring_rule** - Set up alerts
9. **suggest_prompts** - AI-suggested prompts to track

## API Endpoints

### Send Message
```
POST /chat/send_message/
{
  "message": "How is my domain performing?",
  "domain_id": 1,
  "conversation_id": 123  // optional
}
```

### List Conversations
```
GET /chat/conversations/
GET /chat/conversations/?domain_id=1
```

### Get Conversation Detail
```
GET /chat/{id}/conversation_detail/
```

### Delete Conversation
```
DELETE /chat/{id}/delete_conversation/
```

## Models

### ChatConversation
- Links user + domain
- Stores conversation metadata
- Auto-generates title from first message

### ChatMessage
- Stores messages (user/assistant/system)
- Tracks function calls and results
- Records token usage and model used

## Configuration

Required environment variable:
```bash
OPENAI_API_KEY=sk-...
```

Model: GPT-4o-mini (cost-effective, excellent for function calling)

## Cost Estimation

- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens
- Typical message: ~$0.0002 (0.02 cents)
- 1,000 messages: ~$0.20

## Testing

```bash
# Run migrations
python manage.py migrate chat

# Test in shell
python manage.py shell
>>> from chat.models import ChatConversation
>>> from chat.services import ChatbotService
>>> # Test service methods
```

## Frontend Integration

```typescript
import { api } from '@/services/api';

// Send message
const response = await api.sendChatMessage({
  message: "Show me my analytics",
  domain_id: selectedDomain.id
});

console.log(response.message);
```

## Example Queries

- "How is my domain performing over the last 30 days?"
- "Compare my visibility with competitors"
- "What are my top performing prompts on ChatGPT?"
- "Identify content gaps where I have low visibility"
- "Create an alert when my position drops below 5"
- "Suggest new prompts I should track"
- "Show me recent negative sentiment mentions"

## Development

### Adding New Functions

1. Define function in `chat/tools.py`
2. Implement handler in `chat/services.py`
3. Add execution logic in `chat/views.py` → `_execute_function()`

### Example Function

```python
# tools.py
{
    "type": "function",
    "function": {
        "name": "my_custom_function",
        "description": "What this function does",
        "parameters": { ... }
    }
}

# services.py
@staticmethod
def my_custom_function(domain, params):
    # Your logic here
    return {"result": "data"}

# views.py
elif function_name == "my_custom_function":
    return ChatbotService.my_custom_function(domain, arguments)
```

## Files

- `models.py` - Database models
- `views.py` - API endpoints and function execution
- `services.py` - Business logic and data queries
- `tools.py` - Function definitions for OpenAI
- `serializers.py` - DRF serializers
- `admin.py` - Django admin interface
- `urls.py` - URL routing

## Notes

- Conversations are user + domain scoped
- All function calls are logged in ChatMessage.function_calls
- Token usage tracked per message
- Model is configurable (default: gpt-4o-mini)
- Domain access validated on every request
