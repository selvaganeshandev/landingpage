"""
Topic Processor: Groups keywords into topics using NLP when domain completes
"""
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from difflib import SequenceMatcher
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shared_models.models import Domain, Keyword, Topic, TopicKeyword
from core.chatgpt_client import ChatGPTClient

logger = logging.getLogger(__name__)


class TopicProcessor:
    """
    Processor for grouping keywords into topics using NLP
    Triggered when domain processing_status becomes COMP
    """
    
    def __init__(self):
        self.chatgpt_client = ChatGPTClient()
    
    def process_topics_for_domain(self, domain: Domain) -> Dict[str, Any]:
        """
        Process topics for a domain by grouping keywords using NLP
        
        Args:
            domain: Domain to process topics for
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Starting topic processing for domain {domain.id} ({domain.name})")

            # Use the domain's organisation BYOK key (with .env fallback) for all
            # ChatGPT calls in this run.
            self.chatgpt_client = ChatGPTClient(org_id=getattr(domain, 'organisation_id', None))

            # Fetch only unused keywords for this domain (keywords not yet used for topic generation)
            keywords = Keyword.objects.filter(
                domain=domain,
                last_used_for_topic_generation__isnull=True  # Only unused keywords
            )
            if not keywords.exists():
                logger.warning(f"No unused keywords found for domain {domain.id} - all keywords have been used for topic generation")
                return {
                    'success': False,
                    'message': 'No unused keywords found for domain - all keywords have been used for topic generation',
                    'topics_created': 0
                }
            
            logger.info(f"Found {keywords.count()} unused keywords for topic generation")
            
            # Group keywords into topics using ChatGPT/NLP
            keyword_list = [kw.keyword for kw in keywords]
            grouped_topics = self._group_keywords_into_topics(keyword_list, domain)
            
            if not grouped_topics:
                logger.warning(f"No topics could be generated for domain {domain.id}")
                return {
                    'success': False,
                    'message': 'Failed to generate topics from keywords',
                    'topics_created': 0
                }
            
            # Create Topic and TopicKeyword records
            topics_created = 0
            with transaction.atomic():
                for topic_data in grouped_topics:
                    topic = self._create_topic(domain, topic_data)
                    if topic:
                        # Link keywords to topic
                        self._link_keywords_to_topic(topic, topic_data['keywords'], keywords)
                        topics_created += 1
                
                logger.info(f"Successfully created {topics_created} topics for domain {domain.id}")
            
            return {
                'success': True,
                'message': f'Created {topics_created} topics',
                'topics_created': topics_created
            }
            
        except Exception as e:
            logger.error(f"Error processing topics for domain {domain.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'topics_created': 0
            }
    
    def _group_keywords_into_topics(self, keywords: List[str], domain: Domain) -> List[Dict[str, Any]]:
        """
        Use ChatGPT to group keywords into topics
        
        Args:
            keywords: List of keyword strings
            domain: Domain for context
            
        Returns:
            List of topic dictionaries with name and keywords
        """
        if not keywords:
            return []
        
        try:
            # Prepare system prompt for keyword grouping
            system_prompt = """You are an expert in natural language processing and content organization.
Your task is to group related keywords into logical topics based on their semantic similarity and themes.

For each group, provide:
1. A descriptive topic name (1-3 words, noun phrase)
2. List of keywords that belong to this topic

Group keywords that:
- Share similar meanings or themes
- Are semantically related
- Can be grouped under a common topic

Return ONLY a JSON array with this structure:
[
  {
    "topic_name": "Topic Name",
    "keywords": ["keyword1", "keyword2", "keyword3"]
  },
  ...
]

Ensure all keywords are included in exactly one topic."""
            
            # Prepare user message
            keywords_text = ", ".join(keywords)
            user_message = f"""Group these keywords into logical topics for domain: {domain.name}

Keywords: {keywords_text}

Return ONLY the JSON array, no markdown, no explanations."""
            
            # Call ChatGPT
            self.chatgpt_client._ensure_client()
            if not self.chatgpt_client.client:
                logger.warning("ChatGPT client not available, using fallback grouping")
                return self._fallback_group_keywords(keywords)
            
            response = self.chatgpt_client.client.chat.completions.create(
                model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=2000,
                timeout=60
            )
            
            content = response.choices[0].message.content.strip()
            return self._parse_topic_groups(content, keywords)
            
        except Exception as e:
            logger.error(f"Error grouping keywords with ChatGPT: {str(e)}", exc_info=True)
            return self._fallback_group_keywords(keywords)
    
    def _parse_topic_groups(self, content: str, original_keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Parse ChatGPT response to extract topic groups
        """
        import json
        import re
        
        try:
            # Remove markdown code blocks if present
            content_clean = content.strip()
            if content_clean.startswith('```json'):
                content_clean = content_clean[7:].strip()
            elif content_clean.startswith('```'):
                content_clean = content_clean[3:].strip()
            if content_clean.endswith('```'):
                content_clean = content_clean[:-3].strip()
            
            # Parse JSON
            parsed_data = json.loads(content_clean)
            
            if isinstance(parsed_data, list):
                topics = []
                used_keywords = set()
                
                for item in parsed_data:
                    if isinstance(item, dict) and 'topic_name' in item and 'keywords' in item:
                        topic_name = str(item['topic_name']).strip()
                        topic_keywords = [str(kw).strip() for kw in item['keywords'] if str(kw).strip()]
                        
                        if topic_name and topic_keywords:
                            topics.append({
                                'topic_name': topic_name,
                                'keywords': topic_keywords
                            })
                            used_keywords.update(topic_keywords)
                
                # Add any unused keywords to a "General" topic
                unused_keywords = [kw for kw in original_keywords if kw not in used_keywords]
                if unused_keywords:
                    topics.append({
                        'topic_name': 'General',
                        'keywords': unused_keywords
                    })
                
                return topics
                
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}, using fallback")
        
        return self._fallback_group_keywords(original_keywords)
    
    def _fallback_group_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Fallback grouping when ChatGPT is unavailable
        Groups all keywords into a single "General" topic
        """
        if not keywords:
            return []
        
        return [{
            'topic_name': 'General',
            'keywords': keywords
        }]
    
    def _find_similar_topic(self, domain: Domain, topic_name: str, similarity_threshold: float = 0.8) -> Optional[Topic]:
        """
        Find an existing topic with a similar name in the same domain
        
        Args:
            domain: Domain to search in
            topic_name: Topic name to match
            similarity_threshold: Minimum similarity ratio (0.0 to 1.0)
            
        Returns:
            Similar Topic instance or None
        """
        try:
            # Get all existing topics for this domain
            existing_topics = Topic.objects.filter(domain=domain)
            
            if not existing_topics.exists():
                return None
            
            topic_name_lower = topic_name.lower().strip()
            best_match = None
            best_ratio = 0.0
            
            for existing_topic in existing_topics:
                existing_name_lower = existing_topic.name.lower().strip()
                
                # Check exact match (case-insensitive)
                if topic_name_lower == existing_name_lower:
                    logger.info(f"Found exact match for topic '{topic_name}': '{existing_topic.name}' (ID: {existing_topic.id})")
                    return existing_topic
                
                # Calculate similarity ratio
                ratio = SequenceMatcher(None, topic_name_lower, existing_name_lower).ratio()
                
                # Also check if one name contains the other (for partial matches)
                if topic_name_lower in existing_name_lower or existing_name_lower in topic_name_lower:
                    ratio = max(ratio, 0.85)  # Boost partial matches
                
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = existing_topic
            
            # Return best match if it meets the threshold
            if best_match and best_ratio >= similarity_threshold:
                logger.info(f"Found similar topic '{topic_name}' → '{best_match.name}' (similarity: {best_ratio:.2f}, ID: {best_match.id})")
                return best_match
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding similar topic for '{topic_name}': {str(e)}", exc_info=True)
            return None
    
    def _create_topic(self, domain: Domain, topic_data: Dict[str, Any]) -> Optional[Topic]:
        """
        Create a Topic record or reuse existing similar topic
        
        Args:
            domain: Domain for the topic
            topic_data: Dictionary with topic_name and keywords
            
        Returns:
            Created or existing Topic instance or None
        """
        try:
            topic_name = topic_data['topic_name'].strip()
            
            # First, check if a similar topic already exists
            existing_topic = self._find_similar_topic(domain, topic_name)
            
            if existing_topic:
                # Update keyword_list to include new keywords (merge unique keywords)
                existing_keywords = set(existing_topic.keyword_list or [])
                new_keywords = set(topic_data['keywords'])
                merged_keywords = sorted(list(existing_keywords | new_keywords))
                
                if merged_keywords != existing_topic.keyword_list:
                    existing_topic.keyword_list = merged_keywords
                    existing_topic.save(update_fields=['keyword_list', 'modified_at'])
                    logger.info(f"Updated existing topic '{existing_topic.name}' (ID: {existing_topic.id}) with merged keywords: {len(merged_keywords)} total")
                
                return existing_topic
            
            # No similar topic found, create a new one
            with transaction.atomic():
                topic = Topic.objects.create(
                    domain=domain,
                    name=topic_name,
                    keyword_list=topic_data['keywords'],
                    track_status='INIT',
                    track_message='Topic created, waiting for analytics processing',
                    tracked_at=timezone.now()
                )
                logger.info(f"Created new topic: {topic.name} (ID: {topic.id})")
                return topic
                
        except Exception as e:
            logger.error(f"Error creating topic {topic_data['topic_name']}: {str(e)}", exc_info=True)
            return None
    
    def _link_keywords_to_topic(self, topic: Topic, keyword_strings: List[str], keyword_objects: List[Keyword]) -> None:
        """
        Link keywords to topic by creating TopicKeyword records
        Also marks keywords as used for topic generation (can be used multiple times)
        
        Args:
            topic: Topic instance
            keyword_strings: List of keyword strings
            keyword_objects: QuerySet or list of Keyword objects
        """
        try:
            # Create a mapping of keyword strings to Keyword objects
            keyword_map = {kw.keyword: kw for kw in keyword_objects}
            
            with transaction.atomic():
                for keyword_str in keyword_strings:
                    keyword_obj = keyword_map.get(keyword_str)
                    if keyword_obj:
                        # Check if link already exists
                        if not TopicKeyword.objects.filter(topic=topic, keyword=keyword_obj).exists():
                            TopicKeyword.objects.create(
                                topic=topic,
                                keyword=keyword_obj,
                                relevance_score=Decimal('100.00'),  # Default relevance
                                track_status='INIT'
                            )
                            logger.debug(f"Linked keyword '{keyword_str}' to topic '{topic.name}'")
                        
                        # Mark keyword as used for topic generation (can be used multiple times)
                        # Update the timestamp to track when it was last used
                        keyword_obj.last_used_for_topic_generation = timezone.now()
                        keyword_obj.save(update_fields=['last_used_for_topic_generation', 'modified_at'])
                        logger.debug(f"Marked keyword '{keyword_str}' as used for topic generation")
        except Exception as e:
            logger.error(f"Error linking keywords to topic {topic.id}: {str(e)}", exc_info=True)
    
    def match_keyword_to_existing_topics(self, keyword: Keyword) -> Optional[Topic]:
        """
        Match a newly added keyword to existing topics based on semantic similarity
        
        Args:
            keyword: Keyword to match
            
        Returns:
            Matching Topic or None
        """
        try:
            # Get all existing topics for this domain
            topics = Topic.objects.filter(domain=keyword.domain, track_status='COMP')
            
            if not topics.exists():
                return None
            
            # Use ChatGPT to find the best matching topic
            topic_names = [t.name for t in topics]
            topic_keywords = {t.name: t.keyword_list for t in topics}
            
            system_prompt = """You are an expert in semantic similarity matching.
Given a keyword and a list of topics with their keywords, determine which topic the keyword best matches.

Return ONLY a JSON object with this structure:
{
  "matched_topic": "Topic Name",
  "confidence": 0.95
}

If no good match exists (confidence < 0.7), return:
{
  "matched_topic": null,
  "confidence": 0.0
}"""
            
            user_message = f"""Keyword to match: {keyword.keyword}

Available topics:
{chr(10).join([f"- {name}: {', '.join(kws)}" for name, kws in topic_keywords.items()])}

Return ONLY the JSON object."""
            
            self.chatgpt_client._ensure_client()
            if not self.chatgpt_client.client:
                return None
            
            response = self.chatgpt_client.client.chat.completions.create(
                model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2,
                max_tokens=200,
                timeout=30
            )
            
            import json
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content[7:].strip()
            elif content.startswith('```'):
                content = content[3:].strip()
            if content.endswith('```'):
                content = content[:-3].strip()
            
            result = json.loads(content)
            
            if result.get('matched_topic') and result.get('confidence', 0) >= 0.7:
                matched_topic = topics.get(name=result['matched_topic'])
                
                # Mark keyword as used for topic generation when matched to existing topic
                keyword.last_used_for_topic_generation = timezone.now()
                keyword.save(update_fields=['last_used_for_topic_generation', 'modified_at'])
                logger.debug(f"Marked keyword '{keyword.keyword}' as used for topic generation (matched to {matched_topic.name})")
                
                return matched_topic
            
            return None
            
        except Exception as e:
            logger.error(f"Error matching keyword {keyword.keyword} to topics: {str(e)}", exc_info=True)
            return None

