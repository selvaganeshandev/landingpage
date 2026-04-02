"""
Views for Agentic ChatBot
Handles chat conversations with function calling capabilities
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.conf import settings
from openai import OpenAI
import json
import logging

from .models import ChatConversation, ChatMessage
from .serializers import (
    ChatConversationSerializer,
    ChatConversationListSerializer,
    ChatMessageSerializer
)
from .tools import CHAT_TOOLS
from .services import ChatbotService
from domains.models import Domain, DomainAccess
from alerts.models import AlertRule

logger = logging.getLogger(__name__)


class ChatViewSet(viewsets.ViewSet):
    """
    ViewSet for Agentic ChatBot operations
    Provides intelligent chat interface with function calling
    """
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if api_key:
            self.openai_client = OpenAI(api_key=api_key, timeout=60)
        else:
            self.openai_client = None
            logger.warning("OpenAI API key not configured")

    def _validate_domain_access(self, user, domain_id):
        """
        Validate user has access to the domain
        Returns Domain object or raises PermissionDenied
        """
        try:
            domain = Domain.objects.get(
                id=domain_id,
                organisation=user.organisation
            )
        except Domain.DoesNotExist:
            raise PermissionDenied("Domain not found or access denied")

        # Super admins and admins have access to all domains in their org
        if user.role in ('super_admin', 'admin'):
            return domain

        # Regular users need explicit access
        has_access = DomainAccess.objects.filter(
            user=user,
            domain=domain
        ).exists()

        if not has_access:
            raise PermissionDenied("You don't have access to this domain")

        return domain

    def _build_system_prompt(self, domain):
        """Build system prompt with domain context"""
        return f"""You are an intelligent AI assistant for {domain.name}, an LLM monitoring platform user.

Your role is to help users understand their domain's performance across AI platforms (ChatGPT, Gemini, Perplexity).

Domain Context:
- Name: {domain.name}
- URL: {domain.url}
- Description: {domain.short_description or 'N/A'}
- Current Visibility Score: {domain.visibility_score}
- Average Position: {domain.average_position}
- Sentiment: {domain.sentiment_category} ({domain.sentiment_score})

You have access to function calling tools to retrieve real-time data about:
- Domain analytics (mentions, trends, visibility)
- Competitor analysis
- Prompt performance
- Content gaps and opportunities
- Sentiment analysis
- Platform-specific breakdowns

Guidelines:
1. Always use function calls to get real data when answering questions about metrics
2. Provide actionable insights and recommendations
3. Be concise but comprehensive
4. When suggesting actions, explain why
5. Use specific numbers from function results
6. If asked to create alerts or rules, use the appropriate function
7. Be proactive in suggesting improvements

Content Generation Quality Guidelines (when asked to write/generate content):
- If the user asks you to write an article, blog post, or any content, ask clarifying questions first:
  * What is the target word count?
  * Any specific keywords to target?
  * What tone/style do they prefer?
  * Who is the target audience?
- Write in clean HTML format with proper <h2>, <h3> headings (never markdown #)
- Use <table> for tabular data (never markdown pipe tables)
- Follow SEO best practices: keyword placement, heading hierarchy, meta-friendly structure
- Include an introduction with a hook and a conclusion with key takeaways
- Suggest using the "Generate Content" button for full-featured article generation with SEO optimization, internal linking, and reference integration

Remember: You're helping users improve their visibility in AI-generated responses."""

    def _build_message_history(self, conversation, limit=20):
        """Build message history for OpenAI API"""
        messages = conversation.messages.order_by('created_at')[:limit]
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def _execute_function(self, function_name, arguments, domain, user):
        """Execute a single function call"""
        try:
            logger.info(f"Executing function: {function_name} with args: {arguments}")

            if function_name == "get_domain_analytics":
                return ChatbotService.get_domain_analytics(
                    domain,
                    date_range=arguments.get('date_range', '30d'),
                    include_trends=arguments.get('include_trends', False)
                )

            elif function_name == "get_competitor_analysis":
                return ChatbotService.get_competitor_analysis(
                    domain,
                    competitor_names=arguments.get('competitor_names'),
                    metric=arguments.get('metric', 'all')
                )

            elif function_name == "get_prompt_performance":
                return ChatbotService.get_prompt_performance(
                    domain,
                    platform=arguments.get('platform', 'all'),
                    sort_by=arguments.get('sort_by', 'mentions'),
                    limit=arguments.get('limit', 10)
                )

            elif function_name == "get_content_gaps":
                return ChatbotService.get_content_gaps(
                    domain,
                    limit=arguments.get('limit', 10),
                    focus_area=arguments.get('focus_area', 'all')
                )

            elif function_name == "get_sentiment_analysis":
                return ChatbotService.get_sentiment_analysis(
                    domain,
                    date_range=arguments.get('date_range', '30d'),
                    by_platform=arguments.get('by_platform', False)
                )

            elif function_name == "get_top_mentions":
                return ChatbotService.get_top_mentions(
                    domain,
                    limit=arguments.get('limit', 5),
                    sort_by=arguments.get('sort_by', 'recent'),
                    platform=arguments.get('platform', 'all')
                )

            elif function_name == "get_platform_breakdown":
                return ChatbotService.get_platform_breakdown(
                    domain,
                    metric=arguments.get('metric', 'all'),
                    date_range=arguments.get('date_range', '30d')
                )

            elif function_name == "create_monitoring_rule":
                return self._create_monitoring_rule(domain, user, arguments)

            elif function_name == "suggest_prompts":
                return self._suggest_prompts(domain, arguments)

            elif function_name == "get_insights_dashboard":
                return ChatbotService.get_insights_dashboard(
                    domain,
                    date_range=arguments.get('date_range', '30d')
                )

            elif function_name == "get_mentions_list":
                return ChatbotService.get_mentions_list(
                    domain,
                    platform=arguments.get('platform', 'all'),
                    sentiment=arguments.get('sentiment', 'all'),
                    search_query=arguments.get('search_query'),
                    limit=arguments.get('limit', 10),
                    sort_by=arguments.get('sort_by', 'recent')
                )

            elif function_name == "get_citations_list":
                return ChatbotService.get_citations_list(
                    domain,
                    platform=arguments.get('platform', 'all'),
                    status=arguments.get('status', 'all'),
                    limit=arguments.get('limit', 10)
                )

            elif function_name == "get_alerts_list":
                return ChatbotService.get_alerts_list(
                    domain,
                    status=arguments.get('status', 'all'),
                    severity=arguments.get('severity', 'all'),
                    limit=arguments.get('limit', 10)
                )

            elif function_name == "get_topics_analysis":
                return ChatbotService.get_topics_analysis(
                    domain,
                    date_range=arguments.get('date_range', '30d'),
                    limit=arguments.get('limit', 10)
                )

            elif function_name == "get_share_of_voice":
                return ChatbotService.get_share_of_voice(
                    domain,
                    date_range=arguments.get('date_range', '30d'),
                    include_competitors=arguments.get('include_competitors', False)
                )

            elif function_name == "get_historical_trends":
                return ChatbotService.get_historical_trends(
                    domain,
                    metric=arguments.get('metric', 'all'),
                    period=arguments.get('period', 'daily'),
                    months=arguments.get('months', 3)
                )

            elif function_name == "get_prompt_groups":
                return ChatbotService.get_prompt_groups(
                    domain,
                    limit=arguments.get('limit', 10),
                    sort_by=arguments.get('sort_by', 'mentions')
                )

            elif function_name == "get_misinformation_alerts":
                return ChatbotService.get_misinformation_alerts(
                    domain,
                    status=arguments.get('status', 'all'),
                    limit=arguments.get('limit', 10)
                )

            elif function_name == "get_domain_summary":
                return ChatbotService.get_domain_summary(domain)

            else:
                return {"error": f"Unknown function: {function_name}"}

        except Exception as e:
            logger.error(f"Error executing function {function_name}: {str(e)}")
            return {"error": f"Failed to execute {function_name}: {str(e)}"}

    def _create_monitoring_rule(self, domain, user, arguments):
        """Create a new monitoring rule"""
        try:
            # Map condition to metric and operator
            condition_map = {
                'position_drop': {'metric': 'average_position', 'operator': 'greater_than'},
                'mention_spike': {'metric': 'mention_count', 'operator': 'greater_than'},
                'sentiment_negative': {'metric': 'sentiment_score', 'operator': 'less_than'},
                'new_competitor': {'metric': 'competitor_count', 'operator': 'greater_than'}
            }

            condition = arguments.get('condition')
            mapped = condition_map.get(condition, {'metric': 'mention_count', 'operator': 'greater_than'})

            # Create conditions dict based on AlertRule model
            conditions = {
                'metric': mapped['metric'],
                'operator': mapped['operator'],
                'threshold': arguments.get('threshold', 0)
            }

            rule = AlertRule.objects.create(
                domain=domain,
                name=arguments.get('rule_name'),
                description=f"Auto-created monitoring rule for {condition}",
                conditions=conditions,
                notification_channel_list=arguments.get('notification_channel', ['email']),
                created_by=user
            )

            return {
                'success': True,
                'rule_id': rule.id,
                'rule_name': rule.name,
                'message': f"Monitoring rule '{rule.name}' created successfully"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _suggest_prompts(self, domain, arguments):
        """Suggest new prompts to track"""
        from prompts.models import PromptGroup

        count = arguments.get('count', 5)
        strategy = arguments.get('strategy', 'niche_based')

        # Get existing prompts to avoid duplicates
        existing_prompts = list(
            PromptGroup.objects.filter(domain=domain)
            .values_list('name', flat=True)
        )

        suggestions = []

        if strategy == 'niche_based' and domain.niches:
            # Suggest based on domain niches
            for niche in domain.niches[:count]:
                suggestions.append({
                    'prompt': f"What are the best tools for {niche}?",
                    'reason': f"Targets your niche: {niche}",
                    'strategy': 'niche_based'
                })

        elif strategy == 'competitor_based':
            from competitors.models import Competitor
            competitors = Competitor.objects.filter(domain=domain)[:3]
            for comp in competitors:
                suggestions.append({
                    'prompt': f"Compare {domain.name} vs {comp.name}",
                    'reason': f"Direct comparison with competitor {comp.name}",
                    'strategy': 'competitor_based'
                })

        # Add generic high-value prompts
        if len(suggestions) < count:
            generic = [
                f"What is {domain.name}?",
                f"How does {domain.name} work?",
                f"Is {domain.name} worth it?",
                f"Best alternatives to {domain.name}",
                f"{domain.name} review"
            ]
            for prompt in generic:
                if prompt not in existing_prompts and len(suggestions) < count:
                    suggestions.append({
                        'prompt': prompt,
                        'reason': 'High-value generic query',
                        'strategy': 'best_practices'
                    })

        return {
            'suggested_prompts': suggestions[:count],
            'strategy': strategy,
            'total_suggestions': len(suggestions)
        }

    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """
        Send a message to the chatbot and get AI response with function calling
        """
        if not self.openai_client:
            return Response(
                {'error': 'ChatBot is not configured. Please contact administrator.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        user_message = request.data.get('message')
        conversation_id = request.data.get('conversation_id')
        domain_id = request.data.get('domain_id')

        if not user_message:
            return Response(
                {'error': 'message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate domain access
        domain = self._validate_domain_access(request.user, domain_id)

        # Get or create conversation
        if conversation_id:
            try:
                conversation = ChatConversation.objects.get(
                    id=conversation_id,
                    user=request.user,
                    domain=domain
                )
            except ChatConversation.DoesNotExist:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            conversation = ChatConversation.objects.create(
                user=request.user,
                domain=domain,
                title=user_message[:100]  # Use first message as title
            )

        # Save user message
        ChatMessage.objects.create(
            conversation=conversation,
            role='user',
            content=user_message
        )

        # Build message history
        messages = self._build_message_history(conversation)

        # Add system prompt
        system_prompt = self._build_system_prompt(domain)
        messages.insert(0, {"role": "system", "content": system_prompt})

        try:
            # Call ChatGPT with function calling
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model
                messages=messages,
                tools=CHAT_TOOLS,
                tool_choice="auto",
                temperature=0.7
            )

            assistant_message = response.choices[0].message
            total_tokens = response.usage.total_tokens

            # Handle function calls
            if assistant_message.tool_calls:
                logger.info(f"Function calls detected: {len(assistant_message.tool_calls)}")

                # Execute all function calls
                function_results = []
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    result = self._execute_function(
                        function_name,
                        arguments,
                        domain,
                        request.user
                    )

                    function_results.append({
                        'name': function_name,
                        'arguments': arguments,
                        'result': result
                    })

                    # Add to messages for final response
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": json.dumps(arguments)
                            }
                        }]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                # Get final response from ChatGPT
                final_response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7
                )

                assistant_content = final_response.choices[0].message.content
                total_tokens += final_response.usage.total_tokens

                # Save assistant message with function calls
                ChatMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=assistant_content,
                    function_calls=function_results,
                    model_used='gpt-4o-mini',
                    tokens_used=total_tokens
                )

            else:
                # No function calls - direct response
                assistant_content = assistant_message.content

                ChatMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=assistant_content,
                    model_used='gpt-4o-mini',
                    tokens_used=total_tokens
                )

            return Response({
                'message': assistant_content,
                'conversation_id': conversation.id,
                'tokens_used': total_tokens,
                'function_calls_made': len(assistant_message.tool_calls) if assistant_message.tool_calls else 0
            })

        except Exception as e:
            logger.error(f"ChatBot error: {str(e)}")
            return Response(
                {'error': f'ChatBot error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def conversations(self, request):
        """List all conversations for the user"""
        domain_id = request.query_params.get('domain_id')

        conversations = ChatConversation.objects.filter(user=request.user)

        if domain_id:
            # Validate domain access
            domain = self._validate_domain_access(request.user, domain_id)
            conversations = conversations.filter(domain=domain)

        serializer = ChatConversationListSerializer(conversations, many=True)
        return Response({'conversations': serializer.data})

    @action(detail=True, methods=['get'])
    def conversation_detail(self, request, pk=None):
        """Get a specific conversation with all messages"""
        try:
            conversation = ChatConversation.objects.get(
                id=pk,
                user=request.user
            )
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ChatConversationSerializer(conversation)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'])
    def delete_conversation(self, request, pk=None):
        """Delete a conversation"""
        try:
            conversation = ChatConversation.objects.get(
                id=pk,
                user=request.user
            )
            conversation.delete()
            return Response({'message': 'Conversation deleted successfully'})
        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
