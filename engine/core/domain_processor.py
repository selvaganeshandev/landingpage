import threading
import time
import uuid
from typing import List, Dict, Any, Tuple
import re
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shared_models.models import Domain, Keyword, PromptGroup, Prompt, PromptAnalytics, Organisation, SentimentAnalytics
from .rest_client import DataForSEOClient
from .chatgpt_client import ChatGPTClient
import numpy as np
try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None

try:
    from sklearn.cluster import KMeans
except ImportError:  # pragma: no cover
    KMeans = None
from datetime import date


class DomainProcessor:
    """
    Main domain processor class that handles domain processing with multithreading
    """
    
    def __init__(self):
        self.max_concurrent_domains = getattr(settings, 'MAX_CONCURRENT_DOMAINS', 10)
        self.dataforseo_client = DataForSEOClient(
            username=getattr(settings, 'DATAFORSEO_USERNAME', ''),
            password=getattr(settings, 'DATAFORSEO_PASSWORD', '')
        )
        self.chatgpt_client = ChatGPTClient()
        self.active_threads = {}
        self.lock = threading.Lock()
    
    def start_processing_loop(self):
        """
        Start the main processing loop that runs continuously
        """
        print("Starting domain processing loop...")
        while True:
            try:
                self._process_domains()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"Error in processing loop: {str(e)}")
                time.sleep(60)  # Wait longer on error
    
    def _process_domains(self):
        """
        Process domains that are ready for processing
        """
        with self.lock:
            # Count currently processing domains
            currently_processing = len(self.active_threads)
            
            if currently_processing >= self.max_concurrent_domains:
                print(f"Maximum concurrent domains ({self.max_concurrent_domains}) reached")
                return
            
            # Get domains with SCHD status
            available_slots = self.max_concurrent_domains - currently_processing
            domains_to_process = Domain.objects.filter(
                processing_status='SCHD'
            )[:available_slots]
            
            if not domains_to_process:
                print("No domains scheduled for processing")
                return
            
            print(f"Starting processing for {len(domains_to_process)} domains")
            
            # Start processing each domain in a separate thread
            for domain in domains_to_process:
                thread = threading.Thread(
                    target=self._process_single_domain,
                    args=(domain.id,),
                    daemon=True
                )
                thread.start()
                self.active_threads[domain.id] = thread
    
    def _process_single_domain(self, domain_id: int):
        """
        Process a single domain
        """
        try:
            domain = Domain.objects.get(id=domain_id)
            print(f"Processing domain: {domain.name}")
            
            # Update status to processing
            domain.processing_status = 'PROC'
            domain.track_message = 'Starting domain processing...'
            domain.tracked_at = timezone.now()
            domain.save()
            print(f"🔵 LOG: Domain {domain.id} ({domain.name}) - Status set to PROC, starting processing...")
            
            # Step 1: Check if domain has any keywords at all
            all_keywords_exist = Keyword.objects.filter(domain=domain).exists()
            
            if not all_keywords_exist:
                # First time: Fetch keywords from DataForSEO (only once per domain)
                print(f"Initial keyword fetch for {domain.name} from DataForSEO")
                domain.track_message = 'Scraping keywords from search data...'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['track_message', 'tracked_at', 'modified_at'])

                kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
                keywords_from_api = self.dataforseo_client.scrape_target_domain(domain.name, limit=kw_limit)
                
                if not keywords_from_api:
                    domain.processing_status = 'FAIL'
                    domain.track_message = 'No keywords found from DataForSEO API'
                    domain.tracked_at = timezone.now()
                    domain.save()
                    return
                
                # Store unique keywords in database (get_or_create ensures uniqueness per domain)
                print(f"Storing {len(keywords_from_api)} unique keywords for {domain.name}")
                self._store_keywords(domain, keywords_from_api)
            
            # Step 2: Get only unused keywords (where last_used_for_generation is NULL)
            # These are unique keywords that haven't been used for prompt generation yet
            unused_keywords_qs = Keyword.objects.filter(
                domain=domain,
                auto_generate_prompts=True,
                last_used_for_generation__isnull=True  # Only unused keywords
            ).order_by('-priority', 'created_at')
            
            # Step 3: If all keywords are used, fetch new keywords from DataForSEO
            if not unused_keywords_qs.exists():
                # Check if there are any keywords at all (used or unused)
                total_keywords = Keyword.objects.filter(domain=domain).count()
                
                if total_keywords > 0:
                    # All existing keywords have been used, fetch new keywords from DataForSEO
                    print(f"All {total_keywords} keywords have been used for {domain.name}. Fetching new keywords from DataForSEO.")
                    kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
                    keywords_from_api = self.dataforseo_client.scrape_target_domain(domain.name, limit=kw_limit)
                    
                    if not keywords_from_api:
                        domain.processing_status = 'COMP'
                        domain.track_message = 'All keywords have been used. No new keywords found from DataForSEO API.'
                        domain.tracked_at = timezone.now()
                        domain.save()
                        print(f"No new keywords found from DataForSEO API for {domain.name}.")
                        return
                    
                    # Store new unique keywords in database
                    print(f"Storing {len(keywords_from_api)} new unique keywords for {domain.name}")
                    self._store_keywords(domain, keywords_from_api)
                    
                    # Re-query for unused keywords after fetching new ones
                    unused_keywords_qs = Keyword.objects.filter(
                        domain=domain,
                        auto_generate_prompts=True,
                        last_used_for_generation__isnull=True  # Only unused keywords
                    ).order_by('-priority', 'created_at')
                    
                    # If still no unused keywords after fetching (shouldn't happen, but safety check)
                    if not unused_keywords_qs.exists():
                        domain.processing_status = 'COMP'
                        domain.track_message = 'All keywords have been used. No unused keywords available after fetching new ones.'
                        domain.tracked_at = timezone.now()
                        domain.save()
                        print(f"No unused keywords available for {domain.name} after fetching new keywords.")
                        return
                else:
                    # No keywords at all (shouldn't happen after Step 1, but safety check)
                    domain.processing_status = 'COMP'
                    domain.track_message = 'No keywords available for prompt generation.'
                    domain.tracked_at = timezone.now()
                    domain.save()
                    print(f"No keywords available for {domain.name}.")
                    return
            
            # Step 4: Use only unused, unique keywords for prompt generation
            keywords = list(unused_keywords_qs.values_list('keyword', flat=True))
            keyword_ids_to_update = list(unused_keywords_qs.values_list('id', flat=True))
            print(f"Using {len(keywords)} unused keywords for prompt generation for {domain.name}")
            
            # Step 5: Generate prompts using ChatGPT
            print(f"Generating prompts for {domain.name}")
            domain.track_message = f'Generating AI prompts from {len(keywords)} keywords...'
            domain.tracked_at = timezone.now()
            domain.save(update_fields=['track_message', 'tracked_at', 'modified_at'])

            prompts = self.chatgpt_client.generate_prompts_from_keywords(keywords, domain.name)

            # Ensure distinct prompts and ensure we have PROMPT_MIN_COUNT prompts per keyword
            prompts = self._deduplicate_prompts(prompts)
            prompts_per_keyword = getattr(settings, 'PROMPT_MIN_COUNT', 2)
            expected_total = len(keywords) * prompts_per_keyword
            if len(prompts) < expected_total:
                prompts = self._supplement_prompts_to_minimum(prompts, keywords, min_count=expected_total)

            # Sanitize generic boilerplate from prompt texts
            for p in prompts:
                text = p.get('prompt_text') or p.get('prompt') or ''
                p['prompt_text'] = self._sanitize_prompt_text(text)

            print(f"Total prompts generated: {len(prompts)} from {len(keywords)} keywords")

            # Log expert-level prompt template (not stored in DB)
            if keywords:
                example_kw = keywords[0]
                expert_prompt = self._build_expert_prompt_template(example_kw, domain.name)
                print(f"Expert-level template example: {expert_prompt}")
            
            if not prompts:
                domain.processing_status = 'FAIL'
                domain.track_message = 'Failed to generate prompts with ChatGPT'
                domain.tracked_at = timezone.now()
                domain.save()
                return
            
            # Step 6: Group prompts using SentenceTransformer-based NLP
            print(f"Grouping prompts for {domain.name}")
            domain.track_message = f'Grouping {len(prompts)} prompts using NLP clustering...'
            domain.tracked_at = timezone.now()
            domain.save(update_fields=['track_message', 'tracked_at', 'modified_at'])

            grouped_prompts = self._group_prompts_with_sentence_transformers(prompts)
            
            if not grouped_prompts:
                domain.processing_status = 'FAIL'
                domain.track_message = 'Failed to group prompts'
                domain.tracked_at = timezone.now()
                domain.save()
                return
            
            # Step 7: Store prompts and groups in database
            print(f"Storing {len(grouped_prompts)} prompt groups for {domain.name}")
            self._store_prompt_groups(domain, grouped_prompts)
            
            # Step 8: Mark keywords as used after successful prompt generation
            # This prevents reuse of keywords in the next cycle
            # Set auto_generate_prompts=False and update last_used_for_generation
            if keyword_ids_to_update:
                try:
                    updated_count = Keyword.objects.filter(id__in=keyword_ids_to_update).update(
                        last_used_for_generation=timezone.now(),
                        auto_generate_prompts=False  # Disable auto-generation after usage
                    )
                    print(f"Marked {updated_count} keywords as used (set auto_generate_prompts=False and updated last_used_for_generation)")
                except Exception as update_error:
                    print(f"Error updating keyword usage status: {str(update_error)}")
            
            # Step 9: Competitor extraction happens AFTER prompt analytics are completed
            # (moved to prompt_analytics_processor.py _check_and_aggregate_group method)
            # This ensures competitor_mention_list has been populated before extraction

            # Step 10: Keep domain in PROC status - analytics processor will set to COMP when done
            # Do NOT set to COMP here - we need to wait for LLM queries and analytics
            domain.processing_status = 'PROC'
            domain.track_message = f'Prompts ready: {len(keywords)} keywords and {len(grouped_prompts)} groups. Queuing for LLM analysis...'
            domain.tracked_at = timezone.now()
            domain.save()

            print(f"Domain keyword/prompt processing complete: {domain.name}. Waiting for analytics processing...")
            
        except Exception as e:
            print(f"Error processing domain {domain_id}: {str(e)}")
            try:
                domain = Domain.objects.get(id=domain_id)
                domain.processing_status = 'FAIL'
                domain.track_message = f'Processing failed: {str(e)}'
                domain.tracked_at = timezone.now()
                domain.save()
            except:
                pass
        finally:
            # Remove from active threads
            with self.lock:
                if domain_id in self.active_threads:
                    del self.active_threads[domain_id]
    
    def _store_keywords(self, domain: Domain, keywords: List[str]):
        """
        Store unique keywords in the database (per domain).
        Uses get_or_create to ensure uniqueness - same keyword won't be stored twice for the same domain.
        """
        with transaction.atomic():
            created_count = 0
            for keyword_text in keywords:
                keyword, created = Keyword.objects.get_or_create(
                    keyword=keyword_text,
                    domain=domain,
                    defaults={
                        'keyword': keyword_text,
                        'domain': domain,
                        'auto_generate_prompts': True,  # Enable auto-generation by default
                        'priority': 0,  # Default priority
                    }
                )
                if created:
                    created_count += 1
                    print(f"Created unique keyword: {keyword_text}")
            print(f"Stored {created_count} new unique keywords (out of {len(keywords)} total) for domain {domain.name}")
    
    def _store_prompt_groups(self, domain: Domain, grouped_prompts: List[Dict[str, Any]]):
        """
        Store prompt groups and prompts in the database
        """
        with transaction.atomic():
            for group_data in grouped_prompts:
                # Create prompt group with interpretable group_id (title)
                desired_group_id = group_data.get('title', 'Untitled').strip() or 'Untitled'
                group_id = self._unique_group_id_for_domain(domain, desired_group_id)
                
                # Extract theme from the group
                theme = self._extract_theme_from_group(group_data)
                
                prompt_group = PromptGroup.objects.create(
                    group_id=group_id,
                    domain=domain,
                    theme=theme,  # Store extracted theme
                    total_mentions=0,
                    total_citations=0,
                    average_position=0.00
                )
                
                # NOTE: We no longer create initial SentimentAnalytics records with platform=None
                # SentimentAnalytics records are only created with valid platform names
                # when prompt analytics are processed
                
                # Create primary prompts (limit to 1) and convert the rest to secondary
                primary_prompts = group_data.get('primary_prompts', [])
                if len(primary_prompts) > 1:
                    # Keep only the first as primary, move the rest to secondary list
                    extra_primaries = primary_prompts[1:]
                    primary_prompts = primary_prompts[:1]
                    # Merge extras into secondary list
                    group_data['secondary_prompts'] = extra_primaries + group_data.get('secondary_prompts', [])
                for prompt_text in primary_prompts:
                    if prompt_text.strip():
                        prompt = Prompt.objects.create(
                            prompt=prompt_text.strip(),
                            group=prompt_group,
                            type='primary',
                            track_status='INIT'
                        )
                        print(f"Created primary prompt: {prompt_text[:50]}...")
                        self._create_default_analytics_for_prompt(prompt, domain)
                
                # Create secondary prompts
                secondary_prompts = group_data.get('secondary_prompts', [])
                for prompt_text in secondary_prompts:
                    if prompt_text.strip():
                        prompt = Prompt.objects.create(
                            prompt=prompt_text.strip(),
                            group=prompt_group,
                            type='secondary',
                            track_status='INIT'
                        )
                        print(f"Created secondary prompt: {prompt_text[:50]}...")
                        self._create_default_analytics_for_prompt(prompt, domain)
                
                # Ensure at least one primary prompt exists
                if not primary_prompts and secondary_prompts:
                    # Convert first secondary to primary
                    first_secondary = Prompt.objects.filter(
                        group=prompt_group,
                        type='secondary'
                    ).first()
                    if first_secondary:
                        first_secondary.type = 'primary'
                        first_secondary.save()
                        print("Converted first secondary prompt to primary")
                
                print(f"Created prompt group: {group_data.get('title', 'Untitled')} with {len(primary_prompts)} primary and {len(secondary_prompts)} secondary prompts")

    def _create_default_analytics_for_prompt(self, prompt: Prompt, domain: Domain) -> None:
        """
        Create default analytics records for a prompt for all enabled platforms.
        Maps lowercase platform keys from settings to proper database platform names.
        """
        # Get enabled platforms from settings (lowercase keys)
        enabled_platforms = getattr(settings, 'ENABLED_PLATFORMS', ['chatgpt'])
        
        # Map lowercase platform keys to database platform names
        platform_map = {
            'chatgpt': 'ChatGPT',
            'gemini': 'Google Gemini',
            'perplexity': 'Perplexity'
        }
        
        # Create default analytics for each enabled platform
        for platform_key in enabled_platforms:
            platform_key = platform_key.strip().lower()
            platform_name = platform_map.get(platform_key, platform_key.title())
            
            PromptAnalytics.objects.get_or_create(
                prompt=prompt,
                platform=platform_name,
                defaults={
                    'is_mention': False,
                    'total_mentions': 0,
                    'total_citations': 0,
                    'position': 0.00,
                    'sentiment_category': 'neutral',
                    'sentiment_score': 0.00,
                    'context_summary': '',
                    'citation_list': [],
                    'views': 0,
                    'shares': 0,
                    'engagement_score': 0.00,
                    'competitor_mention_list': [],
                    'topic_list': [],
                    'position_history_list': []
                }
            )

    def _unique_group_id_for_domain(self, domain: Domain, base_id: str) -> str:
        # truncate base to 90 chars to allow suffixes within 100-char field limit
        base = (base_id or 'Group').strip()
        base = base[:90].rstrip()
        candidate = base
        suffix = 1
        while PromptGroup.objects.filter(domain=domain, group_id=candidate).exists():
            suffix += 1
            candidate = f"{base} ({suffix})"
            if len(candidate) > 100:
                candidate = candidate[:100]
        return candidate

    def _deduplicate_prompts(self, prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique: List[Dict[str, Any]] = []
        for p in prompts:
            text = p.get('prompt_text') or p.get('prompt') or ''
            key = text.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            # normalize shape
            unique.append({
                'prompt_text': text.strip(),
                'keyword': p.get('keyword', ''),
                'category': p.get('category', 'General'),
                'priority': p.get('priority', 'Medium')
            })
        return unique

    def _supplement_prompts_to_minimum(self, prompts: List[Dict[str, Any]], keywords: List[str], min_count: int = 10) -> List[Dict[str, Any]]:
        existing_keywords = {p.get('keyword', '').lower() for p in prompts}
        for kw in keywords:
            if len(prompts) >= min_count:
                break
            if kw.lower() in existing_keywords:
                continue
            prompts.append({
                'prompt_text': f"What are the key objectives, constraints, and next steps for {kw}?",
                'keyword': kw,
                'category': 'General',
                'priority': 'Medium'
            })
        return prompts

    def _sanitize_prompt_text(self, text: str) -> str:
        if not text:
            return text
        lowered = text.strip()
        # Remove generic leading boilerplate phrases
        boilerplates = [
            'Create an actionable, expert-level prompt for',
            'Provide an expert-level, actionable brief on',
            'For the domain',
            'Draft a comprehensive brief on'
        ]
        for phrase in boilerplates:
            if lowered.lower().startswith(phrase.lower()):
                lowered = lowered[len(phrase):].strip(" :'-\"")
        # Remove unwanted trailing phrase anywhere
        patterns_to_remove = [
            r"\bcovering\s+strategy,\s+pitfalls,\s+KPIs,\s+and\s+examples\b",
        ]
        for pat in patterns_to_remove:
            lowered = re.sub(pat, '', lowered, flags=re.IGNORECASE)
        # Cleanup duplicate spaces and stray punctuation
        lowered = re.sub(r"\s{2,}", ' ', lowered)
        lowered = re.sub(r"\s+([,.;:])", r"\1", lowered)
        lowered = lowered.strip().strip('"\'')
        return lowered

    def _group_prompts_with_sentence_transformers(self, prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not prompts:
            return []

        if SentenceTransformer is None:
            raise RuntimeError("sentence_transformers is required but not installed.")

        # Force CPU usage to avoid MPS crashes on macOS
        import os
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        model = SentenceTransformer('paraphrase-MiniLM-L6-v2', device='cpu')
        texts = [p.get('prompt_text') or p.get('prompt') for p in prompts]
        embeddings = model.encode(texts, convert_to_numpy=True)

        n = len(texts)
        # heuristic for clusters: ~1 cluster per 5 prompts; ensure 1 <= k <= n
        if n >= 10:
            k = max(1, min(10, n // 5))
        else:
            k = max(1, min(2, n))
        if KMeans is None:
            raise RuntimeError("scikit-learn is required but not installed.")
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = kmeans.fit_predict(embeddings)

        groups: Dict[int, Dict[str, Any]] = {}
        for idx, label in enumerate(labels):
            if label not in groups:
                groups[label] = {
                    'title': '',
                    'description': '',
                    'primary_prompts': [],
                    'secondary_prompts': [],
                    'indices': []
                }
            groups[label]['indices'].append(idx)

        # compute titles per cluster using smart NLP-based extraction
        for label, info in groups.items():
            inds = info['indices']
            centroid = kmeans.cluster_centers_[label]
            cluster_vecs = embeddings[inds]
            dists = np.linalg.norm(cluster_vecs - centroid, axis=1)

            # Get all prompts in this cluster for smart title extraction
            cluster_prompts = [texts[i] for i in inds]

            # Use smart NLP-based title extraction
            smart_title = self._extract_smart_title_from_prompts(cluster_prompts)
            info['title'] = smart_title or f"Cluster {label+1}"

            # Primary = top 1-3 closest; Secondary = rest
            sorted_within = [inds[i] for i in np.argsort(dists)]
            primary_count = min(3, len(sorted_within))
            primary_indices = sorted_within[:primary_count]
            secondary_indices = sorted_within[primary_count:]
            info['primary_prompts'] = [texts[i] for i in primary_indices]
            info['secondary_prompts'] = [texts[i] for i in secondary_indices]

        # finalize structure
        result: List[Dict[str, Any]] = []
        for label, info in groups.items():
            # Ensure at least one primary prompt
            if not info['primary_prompts'] and info['secondary_prompts']:
                info['primary_prompts'].append(info['secondary_prompts'].pop(0))
            result.append({
                'title': info['title'],
                'description': f"Clustered group for semantically similar prompts (k={k}).",
                'primary_prompts': info['primary_prompts'],
                'secondary_prompts': info['secondary_prompts']
            })
        return result

    def _extract_smart_title_from_prompts(self, prompts_texts: List[str]) -> str:
        """
        Extract a smart, concise title from a list of prompts using NLP techniques.
        Uses noun phrase extraction, frequency analysis, and stop word filtering.

        Args:
            prompts_texts: List of prompt text strings from a cluster

        Returns:
            A clean, professional 2-4 word title
        """
        from collections import Counter
        import re

        # Comprehensive stop words and question words to filter out
        stop_words = {
            'what', 'how', 'why', 'when', 'where', 'who', 'which', 'whose', 'whom',
            'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'a', 'an', 'and', 'or', 'but', 'if', 'for', 'to', 'of', 'in', 'on', 'at',
            'from', 'with', 'by', 'as', 'that', 'this', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'do', 'does', 'did', 'have', 'has', 'had', 'can', 'could', 'will', 'would',
            'should', 'may', 'might', 'must', 'shall',
            'some', 'any', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'get', 'make', 'find', 'use', 'help', 'know', 'need', 'want', 'tell', 'show'
        }

        # Extract all words and bigrams/trigrams from prompts
        all_words = []
        all_phrases = []

        for prompt in prompts_texts:
            # Clean and normalize text - preserve word boundaries
            # Remove punctuation but keep spacing
            cleaned = re.sub(r'[^\w\s]', ' ', prompt.lower())
            # Remove extra whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            words = cleaned.split()

            # Extract individual meaningful words
            for word in words:
                # Filter: length > 2, not a stop word, not a digit, not just punctuation remnants
                if (len(word) > 2 and
                    word not in stop_words and
                    not word.isdigit() and
                    word.isalpha()):  # Only keep alphabetic words
                    all_words.append(word)

            # Extract 2-word and 3-word phrases (noun phrases heuristic)
            for i in range(len(words) - 1):
                # Bigrams: only if both words are valid (alphabetic, length > 2)
                if (len(words[i]) > 2 and len(words[i+1]) > 2 and
                    words[i].isalpha() and words[i+1].isalpha()):
                    # Skip if first word is a stop word (unless second word is content-rich)
                    if words[i] not in stop_words or words[i+1] not in stop_words:
                        bigram = f"{words[i]} {words[i+1]}"
                        # Only keep if at least one word is not a stop word
                        if words[i] not in stop_words or words[i+1] not in stop_words:
                            all_phrases.append(bigram)

                # Trigrams: only if all words are valid
                if i < len(words) - 2:
                    if (len(words[i]) > 2 and len(words[i+1]) > 2 and len(words[i+2]) > 2 and
                        words[i].isalpha() and words[i+1].isalpha() and words[i+2].isalpha()):
                        # Keep if it has meaningful content (at least 2 non-stop words)
                        meaningful_count = sum(1 for w in [words[i], words[i+1], words[i+2]]
                                             if w not in stop_words and len(w) > 2)
                        if meaningful_count >= 2:
                            trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
                            all_phrases.append(trigram)

        # Count frequencies
        word_freq = Counter(all_words)
        phrase_freq = Counter(all_phrases)

        # Prefer multi-word phrases if they appear frequently
        if phrase_freq:
            # Get most common phrases
            most_common_phrases = phrase_freq.most_common(10)

            # Clean all phrases and score them
            scored_phrases = []
            for phrase, count in most_common_phrases:
                # Accept phrases if: count >= 2, OR small cluster (<=3 prompts)
                if count >= 2 or len(prompts_texts) <= 3:
                    # Clean up the phrase
                    phrase_words = phrase.split()
                    # Filter out remaining stop words at boundaries
                    while phrase_words and phrase_words[0] in stop_words:
                        phrase_words.pop(0)
                    while phrase_words and phrase_words[-1] in stop_words:
                        phrase_words.pop()

                    if len(phrase_words) >= 2:  # Only keep multi-word phrases
                        # Score: prioritize longer phrases and higher counts
                        # Score = count * 10 + word_count * 2
                        score = count * 10 + len(phrase_words) * 2
                        scored_phrases.append((score, phrase_words, count))

            # Sort by score (highest first)
            scored_phrases.sort(reverse=True, key=lambda x: x[0])

            # Take the best scored phrase
            if scored_phrases:
                _, title_words, _ = scored_phrases[0]
                title_words = title_words[:4]  # Limit to 4 words
                title = ' '.join(title_words).title()

                # Additional cleanup: remove trailing prepositions
                trailing_preps = {'Of', 'In', 'On', 'At', 'To', 'For', 'With', 'By'}
                if title.split()[-1] in trailing_preps and len(title.split()) > 1:
                    title = ' '.join(title.split()[:-1])

                return title

        # Fallback: use most common individual words to construct title
        if word_freq:
            top_words = [word for word, _ in word_freq.most_common(4)]
            # Limit to 3 words for individual word titles
            title_words = top_words[:3]
            title = ' '.join(title_words).title()
            return title

        # Last resort: use first few words from first prompt (filtered)
        if prompts_texts:
            first_prompt = prompts_texts[0]
            words = first_prompt.lower().split()
            meaningful = [w for w in words if w not in stop_words and len(w) > 2][:3]
            if meaningful:
                return ' '.join(meaningful).title()

        return "General Topics"

    def _extract_theme_from_group(self, group_data: Dict[str, Any]) -> str:
        """
        Extract a concise theme from the prompt group using NLP
        Uses the title and primary prompts to identify the common theme
        """
        title = group_data.get('title', '').strip()
        primary_prompts = group_data.get('primary_prompts', [])

        # Use the title as base (it's already derived from representative prompt)
        if title and title != 'Untitled':
            # Extract key noun phrases (simple approach: first 2-4 meaningful words)
            words = title.split()
            # Filter out common stop words
            stop_words = {'what', 'how', 'why', 'when', 'where', 'who', 'the', 'is', 'are', 'a', 'an', 'for', 'to', 'of', 'in', 'on', 'at'}
            meaningful_words = [w for w in words if w.lower() not in stop_words]

            # Take first 2-4 meaningful words as theme
            theme_words = meaningful_words[:min(4, len(meaningful_words))]
            if theme_words:
                theme = ' '.join(theme_words).title()
                # Limit to 50 chars for clean themes
                if len(theme) > 50:
                    theme = theme[:50].rsplit(' ', 1)[0]
                return theme

        # Fallback: if no meaningful theme, use "General" with number
        return "General Topics"
    
    def _build_expert_prompt_template(self, keyword: str, domain_name: str) -> str:
        return (
            f"For the domain {domain_name}, draft an expert-level, actionable brief on '{keyword}'. "
            f"Cover: 1) strategy and step-by-step approach, 2) common pitfalls and mitigation, "
            f"3) KPIs and measurement framework, 4) 2-3 practical examples with outcomes."
        )
    
    def get_processing_status(self) -> Dict[str, Any]:
        """
        Get current processing status
        """
        with self.lock:
            return {
                'active_threads': len(self.active_threads),
                'max_concurrent': self.max_concurrent_domains,
                'available_slots': self.max_concurrent_domains - len(self.active_threads),
                'active_domain_ids': list(self.active_threads.keys())
            }
    
    def force_process_domain(self, domain_id: int) -> bool:
        """
        Force process a specific domain (for API calls)
        """
        try:
            domain = Domain.objects.get(id=domain_id)
            
            # Check if domain is already being processed
            with self.lock:
                if domain_id in self.active_threads:
                    return False  # Already processing
            
            # Update status to scheduled
            domain.processing_status = 'SCHD'
            domain.track_message = 'Scheduled for processing by API request'
            domain.tracked_at = timezone.now()
            domain.save()
            
            # Start processing in a separate thread
            thread = threading.Thread(
                target=self._process_single_domain,
                args=(domain_id,),
                daemon=True
            )
            thread.start()
            
            with self.lock:
                self.active_threads[domain_id] = thread
            
            return True
            
        except Exception as e:
            print(f"Error force processing domain {domain_id}: {str(e)}")
            return False
