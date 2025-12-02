import threading
import time
import uuid
from typing import List, Dict, Any, Tuple
import re
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shared_models.models import Domain, Keyword, PromptGroup, Prompt, PromptAnalytics, Organisation, SentimentAnalytics, PromptKeyword
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
            # Use select_for_update to prevent race conditions
            with transaction.atomic():
                domain = Domain.objects.select_for_update().get(id=domain_id)
                
                # Verify domain is still in SCHD status (not already being processed)
                if domain.processing_status != 'SCHD':
                    print(f"Domain {domain.id} ({domain.name}) is not in SCHD status (current: {domain.processing_status}), skipping")
                    return
                
                # Update status to processing
                domain.processing_status = 'PROC'
                domain.track_message = 'Starting domain processing...'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])
                print(f"🔵 LOG: Domain {domain.id} ({domain.name}) - Status set to PROC, starting processing...")
            
            # Step 1: Get only unused keywords (where last_used_for_generation is NULL)
            # Keywords are now MANDATORY and must be provided during domain creation
            unused_keywords_qs = Keyword.objects.filter(
                domain=domain,
                auto_generate_prompts=True,
                last_used_for_generation__isnull=True  # Only unused keywords
            ).order_by('-priority', 'created_at')
            
            # Step 2: Check if domain has any keywords at all
            total_keywords = Keyword.objects.filter(domain=domain).count()
            
            if total_keywords == 0:
                # No keywords at all - this should not happen if validation works, but handle gracefully
                with transaction.atomic():
                    domain = Domain.objects.select_for_update().get(id=domain_id)
                    domain.processing_status = 'FAIL'
                    domain.track_message = 'No keywords found. Please add keywords before processing.'
                    domain.tracked_at = timezone.now()
                    domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])
                print(f"No keywords available for {domain.name}. Domain creation should require keywords.")
                return
            
            # Step 3: If all keywords are used, mark as COMP and wait for new keywords
            if not unused_keywords_qs.exists():
                # All existing keywords have been used
                print(f"All {total_keywords} keywords have been used for {domain.name}. Waiting for new keywords to be added.")
                with transaction.atomic():
                    domain = Domain.objects.select_for_update().get(id=domain_id)
                    domain.processing_status = 'COMP'
                    domain.track_message = 'All keywords have been processed. Add new keywords to continue processing.'
                    domain.tracked_at = timezone.now()
                    domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])
                print(f"Domain {domain.name} marked as COMP - all keywords processed. Add new keywords to reinit.")
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

            # Get country from domain, default to "United States" if not available
            country = getattr(domain, 'country', 'United States') or 'United States'
            prompts = self.chatgpt_client.generate_prompts_from_keywords(keywords, domain.name, country)

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

            # Build prompt-to-keyword mapping AFTER sanitization (using sanitized prompt text)
            # This ensures the mapping keys match the actual prompt text used for storage
            prompt_to_keyword_map = {}
            
            # First pass: collect keywords from prompt dicts
            for p in prompts:
                prompt_text = (p.get('prompt_text') or p.get('prompt') or '').strip()
                keyword = (p.get('keyword') or '').strip()
                if prompt_text and keyword:
                    prompt_to_keyword_map[prompt_text] = keyword
                    # Also ensure the dict has the keyword
                    p['keyword'] = keyword
            
            # Second pass: for prompts without keywords, try to match against original keywords
            # This handles cases where ChatGPT didn't include the keyword in the response
            prompts_fixed = 0
            for p in prompts:
                prompt_text = (p.get('prompt_text') or p.get('prompt') or '').strip()
                keyword = (p.get('keyword') or '').strip()
                
                if prompt_text and not keyword:
                    # Try to find matching keyword by checking if keyword appears in prompt text
                    prompt_lower = prompt_text.lower()
                    for kw in keywords:
                        kw_lower = kw.lower().strip()
                        # Check if keyword appears in prompt (as whole word or phrase)
                        if kw_lower in prompt_lower:
                            keyword = kw
                            p['keyword'] = keyword
                            prompt_to_keyword_map[prompt_text] = keyword
                            prompts_fixed += 1
                            print(f"✅ Auto-assigned keyword '{kw}' to prompt: '{prompt_text[:50]}...'")
                            break
                    
                    # If still no keyword, assign the first available keyword as fallback
                    if not keyword and keywords:
                        keyword = keywords[0]
                        p['keyword'] = keyword
                        prompt_to_keyword_map[prompt_text] = keyword
                        prompts_fixed += 1
                        print(f"⚠️ Fallback: assigned keyword '{keyword}' to prompt: '{prompt_text[:50]}...'")
            
            print(f"Built prompt-to-keyword mapping with {len(prompt_to_keyword_map)} entries after sanitization")
            if prompts_fixed > 0:
                print(f"✅ Auto-assigned keywords to {prompts_fixed} prompts that were missing keywords")
            
            # Debug: Show first 5 mappings
            if prompt_to_keyword_map:
                print("Sample prompt-to-keyword mappings:")
                for i, (prompt, kw) in enumerate(list(prompt_to_keyword_map.items())[:5]):
                    print(f"  {i+1}. '{prompt[:60]}...' → '{kw}'")
            else:
                print("❌ ERROR: No prompt-to-keyword mappings found! This will cause linking to fail.")
            
            # Store the mapping in domain for later use
            self._prompt_keyword_map = prompt_to_keyword_map

            grouped_prompts = self._group_prompts_with_sentence_transformers(prompts)
            
            if not grouped_prompts:
                domain.processing_status = 'FAIL'
                domain.track_message = 'Failed to group prompts'
                domain.tracked_at = timezone.now()
                domain.save()
                return
            
            # Step 7: Store prompts and groups in database
            print(f"Storing {len(grouped_prompts)} prompt groups for {domain.name}")
            self._store_prompt_groups(domain, grouped_prompts, self._prompt_keyword_map)
            
            # Step 7.5: Phase 2 - Safety net: Link any prompts that weren't linked during storage
            # This ensures all prompts from ChatGPT JSON are linked, even if Phase 1 missed some
            safety_stats = self._link_prompts_from_chatgpt_json(domain, prompts)
            if safety_stats['created'] > 0:
                print(f"✅ Phase 2 safety net created {safety_stats['created']} additional links")
            
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
        Keywords are normalized to lowercase before storage.
        """
        with transaction.atomic():
            created_count = 0
            for keyword_text in keywords:
                # Normalize keyword to lowercase and trim whitespace
                normalized_keyword = keyword_text.strip().lower()
                if not normalized_keyword or len(normalized_keyword) > 255:
                    continue  # Skip invalid keywords
                
                keyword, created = Keyword.objects.get_or_create(
                    keyword=normalized_keyword,
                    domain=domain,
                    defaults={
                        'keyword': normalized_keyword,
                        'domain': domain,
                        'auto_generate_prompts': True,  # Enable auto-generation by default
                        'priority': 0,  # Default priority
                    }
                )
                if created:
                    created_count += 1
                    print(f"Created unique keyword: {normalized_keyword}")
            print(f"Stored {created_count} new unique keywords (out of {len(keywords)} total) for domain {domain.name}")
    
    def _link_prompt_to_keyword_immediate(self, prompt: Prompt, keyword_text: str, domain: Domain) -> bool:
        """
        Phase 1: Immediately link a prompt to a keyword right after prompt creation.
        This is the PRIMARY linking method - most reliable.
        
        Args:
            prompt: The Prompt object just created
            keyword_text: The keyword text from ChatGPT response
            domain: Domain instance
            
        Returns:
            True if linked successfully, False otherwise
        """
        from shared_models.models import Keyword, PromptKeyword
        from decimal import Decimal
        
        if not keyword_text or not keyword_text.strip():
            return False
        
        keyword_text = keyword_text.strip()
        
        try:
            # Find keyword in database - sorted by priority desc, then created_at desc
            keyword = Keyword.objects.filter(
                domain=domain,
                keyword__iexact=keyword_text
            ).order_by('-priority', '-created_at').first()
            
            if not keyword:
                # Try to find by partial match (keyword contains the text)
                keyword = Keyword.objects.filter(
                    domain=domain
                ).filter(
                    keyword__icontains=keyword_text
                ).order_by('-priority', '-created_at').first()
            
            if not keyword:
                print(f"❌ Keyword '{keyword_text}' not found for domain {domain.name}")
                # Show available keywords for debugging
                available = list(Keyword.objects.filter(domain=domain).values_list('keyword', flat=True)[:5])
                print(f"   Available keywords: {available}")
                return False
            
            # Create link
            prompt_keyword, created = PromptKeyword.objects.get_or_create(
                prompt=prompt,
                keyword=keyword,
                defaults={'relevance_score': Decimal('100.00')}
            )
            
            if created:
                print(f"✅ Phase 1: Linked prompt (ID:{prompt.id}) → keyword '{keyword.keyword}' (ID:{keyword.id})")
            else:
                print(f"⚠️ Phase 1: Link already exists: prompt (ID:{prompt.id}) → keyword '{keyword.keyword}'")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in immediate linking: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _link_prompts_from_chatgpt_json(self, domain: Domain, chatgpt_prompts: List[Dict[str, Any]]) -> dict:
        """
        Phase 2: Safety net - Loop through ChatGPT JSON and link any prompts that weren't linked.
        This catches any prompts that failed during the primary linking phase.
        
        Args:
            domain: Domain instance
            chatgpt_prompts: Original ChatGPT response with keyword info
            
        Returns:
            Statistics dict with counts
        """
        from shared_models.models import Prompt, Keyword, PromptKeyword
        from decimal import Decimal
        
        stats = {'created': 0, 'exists': 0, 'failed': 0, 'not_found': 0}
        
        print(f"\n🔗 Phase 2 (Safety Net): Linking prompts from ChatGPT JSON for {domain.name}")
        
        # Get all keywords sorted desc
        keywords_qs = Keyword.objects.filter(domain=domain).order_by('-priority', '-created_at')
        keyword_cache = {}  # Cache for faster lookup
        
        # Get all prompts for this domain (create lookup dict)
        domain_prompts = {}
        for p in Prompt.objects.filter(group__domain=domain):
            # Use multiple keys for lookup (original, sanitized, lowercase)
            key1 = p.prompt.lower().strip()
            key2 = self._sanitize_prompt_text(p.prompt).lower().strip()
            domain_prompts[key1] = p
            if key2 != key1:
                domain_prompts[key2] = p
        
        print(f"   Found {len(domain_prompts)} prompts in database")
        print(f"   Processing {len(chatgpt_prompts)} prompts from ChatGPT JSON")
        
        for prompt_data in chatgpt_prompts:
            prompt_text = (prompt_data.get('prompt_text') or prompt_data.get('prompt') or '').strip()
            keyword_text = (prompt_data.get('keyword') or '').strip()
            
            if not prompt_text or not keyword_text:
                stats['failed'] += 1
                continue
            
            # Find prompt (case-insensitive, try multiple variations)
            prompt = None
            lookup_keys = [
                prompt_text.lower().strip(),
                self._sanitize_prompt_text(prompt_text).lower().strip(),
                prompt_text.strip()
            ]
            
            for key in lookup_keys:
                if key in domain_prompts:
                    prompt = domain_prompts[key]
                    break
            
            if not prompt:
                stats['not_found'] += 1
                print(f"   ⚠️ Prompt not found: '{prompt_text[:50]}...'")
                continue
            
            # Check if already linked
            if PromptKeyword.objects.filter(prompt=prompt).exists():
                stats['exists'] += 1
                continue
            
            # Find keyword (use cache for performance)
            keyword_lower = keyword_text.lower().strip()
            if keyword_lower not in keyword_cache:
                keyword = keywords_qs.filter(keyword__iexact=keyword_text).first()
                if not keyword:
                    keyword = keywords_qs.filter(keyword__icontains=keyword_text).first()
                keyword_cache[keyword_lower] = keyword
            else:
                keyword = keyword_cache[keyword_lower]
            
            if not keyword:
                stats['failed'] += 1
                print(f"   ❌ Keyword not found: '{keyword_text}'")
                continue
            
            # Create link
            try:
                PromptKeyword.objects.create(
                    prompt=prompt,
                    keyword=keyword,
                    relevance_score=Decimal('100.00')
                )
                stats['created'] += 1
                print(f"   ✅ Phase 2: Linked prompt (ID:{prompt.id}) → keyword '{keyword.keyword}'")
            except Exception as e:
                stats['failed'] += 1
                print(f"   ❌ Error creating link: {str(e)}")
        
        print(f"\n📊 Phase 2 Summary:")
        print(f"   ✅ Created: {stats['created']} links")
        print(f"   ⚠️  Already exists: {stats['exists']} links")
        print(f"   ❌ Failed: {stats['failed']} links")
        print(f"   ⚠️  Not found: {stats['not_found']} prompts")
        
        return stats
    
    def _link_prompt_to_keyword_direct(self, prompt: Prompt, prompt_text: str, 
                                        prompt_to_keyword_map: Dict[str, str], domain: Domain,
                                        direct_keyword: str = None) -> str:
        """
        Link prompt to keyword using the pre-built mapping or direct keyword.
        This is called immediately when a prompt is created from a keyword.
        
        Args:
            prompt: Prompt instance to link
            prompt_text: The prompt text
            prompt_to_keyword_map: Mapping dictionary from prompt text to keyword
            domain: Domain instance
            direct_keyword: Optional direct keyword (takes precedence over mapping)
            
        Returns:
            'created' if link was created, 'exists' if already exists, 'failed' if failed
        """
        from shared_models.models import PromptKeyword
        
        try:
            # Use direct keyword if provided, otherwise try mapping
            keyword_text = None
            
            if direct_keyword:
                keyword_text = direct_keyword.strip()
            else:
                # Get keyword from mapping - try exact match first, then case-insensitive
                keyword_text = prompt_to_keyword_map.get(prompt_text, '').strip()
                
                # If not found with exact match, try case-insensitive search
                if not keyword_text:
                    for map_prompt, map_keyword in prompt_to_keyword_map.items():
                        if map_prompt.strip().lower() == prompt_text.strip().lower():
                            keyword_text = map_keyword.strip()
                            break
            
            if not keyword_text:
                print(f"⚠️ No keyword found in mapping for prompt: {prompt_text[:50]}...")
                print(f"   Mapping has {len(prompt_to_keyword_map)} entries")
                if len(prompt_to_keyword_map) <= 10:
                    print(f"   Available mappings: {list(prompt_to_keyword_map.keys())}")
                return 'failed'
            
            # Find the keyword in database (case-insensitive)
            try:
                keyword = Keyword.objects.get(keyword__iexact=keyword_text.strip(), domain=domain)
                
                # Create PromptKeyword link if it doesn't exist
                prompt_keyword, created = PromptKeyword.objects.get_or_create(
                    prompt=prompt,
                    keyword=keyword,
                    defaults={'relevance_score': Decimal('100.00')}
                )
                
                if created:
                    print(f"✅ Linked prompt (ID:{prompt.id}) to keyword: '{keyword_text}'")
                    return 'created'
                else:
                    print(f"⚠️ Link already exists for prompt (ID:{prompt.id}) and keyword: '{keyword_text}'")
                    return 'exists'
                    
            except Keyword.DoesNotExist:
                print(f"⚠️ Keyword '{keyword_text}' not found in database for domain {domain.name}")
                print(f"   Looking for: '{keyword_text.lower()}'")
                # Show available keywords
                available_keywords = list(Keyword.objects.filter(domain=domain).values_list('keyword', flat=True)[:10])
                print(f"   Available keywords: {available_keywords}")
                
                # Create the keyword if it doesn't exist (it should exist, but create it as fallback)
                try:
                    keyword = Keyword.objects.create(
                        keyword=keyword_text.lower().strip(),
                        domain=domain,
                        auto_generate_prompts=True,
                        priority=0
                    )
                    print(f"✅ Created missing keyword '{keyword_text}' for domain {domain.name}")
                    
                    # Now create the PromptKeyword link
                    prompt_keyword, created = PromptKeyword.objects.get_or_create(
                        prompt=prompt,
                        keyword=keyword,
                        defaults={'relevance_score': Decimal('100.00')}
                    )
                    
                    if created:
                        print(f"✅ Linked prompt (ID:{prompt.id}) to newly created keyword: '{keyword_text}'")
                        return 'created'
                    else:
                        print(f"⚠️ Link already exists for prompt (ID:{prompt.id}) and keyword: '{keyword_text}'")
                        return 'exists'
                except Exception as e:
                    print(f"❌ Error creating keyword '{keyword_text}': {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return 'failed'
                
        except Exception as e:
            print(f"❌ Error linking prompt to keyword: {str(e)}")
            import traceback
            traceback.print_exc()
            return 'failed'
    
    def _store_prompt_groups(self, domain: Domain, grouped_prompts: List[Dict[str, Any]], 
                             prompt_to_keyword_map: Dict[str, str]):
        """
        Store prompt groups and prompts in the database
        
        Args:
            domain: Domain instance
            grouped_prompts: List of grouped prompt dictionaries
            prompt_to_keyword_map: Mapping of prompt_text to keyword (built after sanitization)
        """
        from shared_models.models import PromptKeyword
        
        # Track linking statistics
        links_created = 0
        links_failed = 0
        
        with transaction.atomic():
            # Track used titles in this batch to ensure uniqueness
            used_titles_in_batch = set()
            
            for group_data in grouped_prompts:
                # Create prompt group with interpretable group_id (title)
                # First, extract theme from primary prompt (ensures 2+ words and closer to prompt)
                extracted_theme = self._extract_theme_from_group(group_data)
                
                # Use the extracted theme as the base title (already normalized to 2+ words)
                desired_group_id = extracted_theme if extracted_theme and extracted_theme != "General Topic" else group_data.get('title', 'Untitled').strip() or 'Untitled'
                
                # If still using the original title, normalize it to ensure 2+ words
                if desired_group_id == group_data.get('title', '').strip():
                    desired_group_id = self._normalize_to_term(desired_group_id, min_words=2, max_words=4)
                
                # Remove numbers from desired group_id before processing
                desired_group_id = self._remove_numbers_from_text(desired_group_id)
                
                # Ensure we have at least 2 words (fallback if normalization failed)
                words = desired_group_id.split()
                if len(words) < 2:
                    desired_group_id = f"{desired_group_id} Topic"
                
                # Ensure uniqueness within this batch first
                base_title = desired_group_id
                candidate_title = base_title
                suffix_index = 0
                descriptive_suffixes = ['Advanced', 'Essential', 'Core', 'Premium', 'Standard', 
                                       'Basic', 'Professional', 'Expert', 'Complete', 'Ultimate']
                
                while candidate_title in used_titles_in_batch:
                    if suffix_index < len(descriptive_suffixes):
                        candidate_title = f"{base_title} {descriptive_suffixes[suffix_index]}"
                        suffix_index += 1
                    else:
                        suffix_char = chr(ord('A') + (suffix_index - len(descriptive_suffixes)))
                        candidate_title = f"{base_title} {suffix_char}"
                        suffix_index += 1
                
                used_titles_in_batch.add(candidate_title)
                
                # Now ensure uniqueness in database
                group_id = self._unique_group_id_for_domain(domain, candidate_title)
                
                # Use the theme we already extracted earlier
                theme = extracted_theme
                # Remove numbers from theme
                theme = self._remove_numbers_from_text(theme)
                
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
                
                for prompt_item in primary_prompts:
                    # Handle both dict and string formats
                    if isinstance(prompt_item, dict):
                        prompt_text = (prompt_item.get('prompt_text') or prompt_item.get('prompt') or '').strip()
                        keyword_text = (prompt_item.get('keyword') or '').strip()
                    else:
                        # Backward compatibility: treat as string
                        prompt_text = str(prompt_item).strip()
                        keyword_text = None
                    
                    if prompt_text:
                        prompt = Prompt.objects.create(
                            prompt=prompt_text,
                            group=prompt_group,
                            type='primary',
                            track_status='INIT'
                        )
                        print(f"Created primary prompt: {prompt_text[:50]}...")
                        self._create_default_analytics_for_prompt(prompt, domain)
                        
                        # Phase 1: Immediate linking - use keyword from dict directly
                        if keyword_text:
                            linked = self._link_prompt_to_keyword_immediate(prompt, keyword_text, domain)
                            if linked:
                                links_created += 1
                            else:
                                links_failed += 1
                        else:
                            # Fallback: try to get keyword from mapping
                            keyword_from_map = prompt_to_keyword_map.get(prompt_text, '').strip()
                            if keyword_from_map:
                                linked = self._link_prompt_to_keyword_immediate(prompt, keyword_from_map, domain)
                                if linked:
                                    links_created += 1
                                else:
                                    links_failed += 1
                            else:
                                print(f"⚠️ No keyword available for prompt: '{prompt_text[:50]}...'")
                                links_failed += 1
                
                # Create secondary prompts
                secondary_prompts = group_data.get('secondary_prompts', [])
                for prompt_item in secondary_prompts:
                    # Handle both dict and string formats
                    if isinstance(prompt_item, dict):
                        prompt_text = (prompt_item.get('prompt_text') or prompt_item.get('prompt') or '').strip()
                        keyword_text = (prompt_item.get('keyword') or '').strip()
                    else:
                        # Backward compatibility: treat as string
                        prompt_text = str(prompt_item).strip()
                        keyword_text = None
                    
                    if prompt_text:
                        prompt = Prompt.objects.create(
                            prompt=prompt_text,
                            group=prompt_group,
                            type='secondary',
                            track_status='INIT'
                        )
                        print(f"Created secondary prompt: {prompt_text[:50]}...")
                        self._create_default_analytics_for_prompt(prompt, domain)
                        
                        # Phase 1: Immediate linking - use keyword from dict directly
                        if keyword_text:
                            linked = self._link_prompt_to_keyword_immediate(prompt, keyword_text, domain)
                            if linked:
                                links_created += 1
                            else:
                                links_failed += 1
                        else:
                            # Fallback: try to get keyword from mapping
                            keyword_from_map = prompt_to_keyword_map.get(prompt_text, '').strip()
                            if keyword_from_map:
                                linked = self._link_prompt_to_keyword_immediate(prompt, keyword_from_map, domain)
                                if linked:
                                    links_created += 1
                                else:
                                    links_failed += 1
                            else:
                                print(f"⚠️ No keyword available for prompt: '{prompt_text[:50]}...'")
                                links_failed += 1
                
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
            
            # Print summary of Phase 1 keyword linking
            print(f"\n📊 Phase 1 (Immediate) Linking Summary:")
            print(f"   ✅ Created: {links_created} links")
            print(f"   ❌ Failed: {links_failed} links")
            if links_failed > 0:
                print(f"   ⚠️  WARNING: {links_failed} prompts could not be linked in Phase 1. Phase 2 safety net will attempt to link them.")

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

    def _link_prompt_to_keywords(self, prompt: Prompt, group_data: Dict[str, Any]) -> None:
        """
        Link a prompt to keywords by creating PromptKeyword records
        Extracts keywords from the prompt's original data or from the group's prompts
        
        Args:
            prompt: Prompt instance to link
            group_data: Dictionary containing prompt group data with prompts and keywords
        """
        try:
            from decimal import Decimal
            
            # Try to find the keyword from the original prompt data
            # The prompt text should match one of the prompts in the group data
            prompt_text = prompt.prompt.strip()
            
            # Look for the keyword in the original prompts list
            # Prompts are generated with a 'keyword' field
            keyword_text = None
            
            # Check primary prompts
            for p in group_data.get('primary_prompts', []):
                if isinstance(p, dict) and p.get('prompt_text', '').strip() == prompt_text:
                    keyword_text = p.get('keyword', '').strip()
                    break
                elif isinstance(p, str) and p.strip() == prompt_text:
                    # If it's just a string, we need to find the keyword from the original prompts
                    # This happens when prompts are grouped
                    pass
            
            # Check secondary prompts
            if not keyword_text:
                for p in group_data.get('secondary_prompts', []):
                    if isinstance(p, dict) and p.get('prompt_text', '').strip() == prompt_text:
                        keyword_text = p.get('keyword', '').strip()
                        break
            
            # If we found a keyword, link it
            if keyword_text:
                try:
                    keyword = Keyword.objects.get(keyword=keyword_text.lower(), domain=prompt.group.domain)
                    if not PromptKeyword.objects.filter(prompt=prompt, keyword=keyword).exists():
                        PromptKeyword.objects.create(
                            prompt=prompt,
                            keyword=keyword,
                            relevance_score=Decimal('100.00')
                        )
                        print(f"Linked prompt to keyword: {keyword_text}")
                except Keyword.DoesNotExist:
                    # Keyword not found, skip
                    pass
                except Exception as e:
                    print(f"Error linking prompt to keyword {keyword_text}: {str(e)}")
            
        except Exception as e:
            print(f"Error in _link_prompt_to_keywords: {str(e)}")

    def _normalize_to_term(self, text: str, min_words: int = 2, max_words: int = 4) -> str:
        """
        Normalize text to a term format with better semantic extraction:
        - Prioritizes nouns and noun phrases
        - Looks for meaningful word pairs that appear together
        - Considers semantic relationships
        - Minimum min_words (default 2) - ensures title is not one word
        - Maximum max_words (default 4)
        - Join multiple words with spaces
        """
        if not text or not text.strip():
            return "General"
        
        text_clean = text.strip()
        
        # Remove question marks
        if text_clean.endswith('?'):
            text_clean = text_clean[:-1].strip()
        
        # Remove common question starters and patterns
        question_starters = [
            'what is', 'what are', 'what do', 'what does', 'what did',
            'how to', 'how does', 'how do', 'how can', 'how will',
            'why is', 'why are', 'why do', 'why does',
            'when to', 'when is', 'when are', 'when do', 'when does',
            'where to', 'where is', 'where are', 'where do', 'where does',
            'who is', 'who are', 'who do', 'who does',
            'tell me', 'explain', 'describe', 'show me', 'give me',
            'is there', 'are there', 'can i', 'should i', 'will i'
        ]
        
        text_lower = text_clean.lower()
        for starter in question_starters:
            if text_lower.startswith(starter):
                # Extract the main term after the question starter
                remaining = text_clean[len(starter):].strip()
                text_clean = remaining.strip('?').strip(' :-\'".,')
                # Also remove common qualifiers that come after question starters
                qualifiers = ['a ', 'an ', 'the ', 'any ', 'some ', 'good ', 'best ', 'better ']
                for qual in qualifiers:
                    if text_clean.lower().startswith(qual):
                        text_clean = text_clean[len(qual):].strip()
                break
        
        # Enhanced stop words including temporal, location, and descriptive words that shouldn't be in titles
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
            'when', 'where', 'how', 'why', 'what', 'who', 'which',  # Question words
            'there', 'here', 'good', 'bad', 'best', 'better', 'worse', 'worst',  # Descriptive/qualitative words
            'online', 'offline', 'free', 'paid', 'new', 'old', 'latest',  # Common but not descriptive
            'time', 'date', 'day', 'month', 'year', 'now', 'today', 'before', 'after',  # Temporal words
            'location', 'place', 'area', 'region', 'city', 'country',  # Location words
            'buy', 'purchase', 'get', 'find', 'save', 'use', 'make', 'take',  # Common verbs
        }
        
        # Split into words
        words = text_clean.split()
        
        # Extract meaningful words with their positions
        # Prioritize words that appear later in the sentence (usually the object/topic)
        meaningful_words = []
        for i, word in enumerate(words):
            word_clean = word.strip('.,!?;:\'"()[]{}').lower()
            # Filter out numbers and words containing numbers
            if word_clean and word_clean not in stop_words and len(word_clean) > 2:
                # Skip words that contain numbers
                if not any(char.isdigit() for char in word_clean):
                    # Boost words that appear later in the sentence (usually the main topic)
                    # But still include all meaningful words
                    meaningful_words.append((word_clean, i))
        
        if not meaningful_words:
            return "General Topic"
        
        # Strategy 1: Look for common noun phrases (adjacent meaningful words)
        # These are more likely to be meaningful concepts
        noun_phrases = []
        for i in range(len(meaningful_words) - 1):
            word1, pos1 = meaningful_words[i]
            word2, pos2 = meaningful_words[i + 1]
            # Check if words are adjacent or close (within 2 positions)
            if pos2 - pos1 <= 2:
                noun_phrases.append((word1, word2, pos1))
        
        # Strategy 2: Prioritize words that are likely nouns (longer, more specific)
        # Score words by length, position, and semantic importance
        # Common domain-specific nouns get higher scores
        domain_nouns = {
            'medicine', 'medicines', 'medication', 'medications', 'prescription', 'prescriptions',
            'app', 'apps', 'application', 'applications', 'software', 'platform', 'platforms',
            'service', 'services', 'product', 'products', 'brand', 'brands',
            'purchase', 'buying', 'buy', 'shopping', 'order', 'ordering',
            'price', 'pricing', 'cost', 'costs', 'payment', 'payments',
            'delivery', 'shipping', 'location', 'locations', 'store', 'stores',
            'review', 'reviews', 'rating', 'ratings', 'quality', 'features',
            'guide', 'guides', 'tutorial', 'tutorials', 'help', 'support',
            'information', 'details', 'specifications', 'benefits', 'advantages'
        }
        
        word_scores = {}
        total_words = len(words) if words else 1
        for word, pos in meaningful_words:
            # Score based on length (longer = more specific)
            length_score = len(word) * 3
            # Boost words that appear later in sentence (usually the main topic/object)
            # But not too late (avoid trailing words)
            position_score = (total_words - pos) * 0.5 if pos < total_words * 0.8 else 0
            base_score = length_score + position_score
            
            # Major boost for domain-specific nouns
            if word in domain_nouns:
                base_score += 30
            
            # Penalize very short words (less than 4 chars) unless they're domain nouns
            if len(word) < 4 and word not in domain_nouns:
                base_score -= 15
            
            word_scores[word] = base_score
        
        # Strategy 3: If we have noun phrases, prefer them
        if noun_phrases:
            # Score noun phrases by word scores
            phrase_scores = []
            for word1, word2, pos in noun_phrases:
                score = word_scores.get(word1, 0) + word_scores.get(word2, 0) - pos
                phrase_scores.append((score, word1, word2))
            
            # Sort by score and take the best
            phrase_scores.sort(reverse=True, key=lambda x: x[0])
            if phrase_scores:
                _, word1, word2 = phrase_scores[0]
                # Always use both words (minimum 2 words requirement)
                capitalized = [word1.capitalize(), word2.capitalize()]
                # Use space to join words
                return f"{capitalized[0]} {capitalized[1]}"
        
        # Strategy 4: If no good phrases, take top words by score (minimum min_words)
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        top_words = [word for word, _ in sorted_words[:max_words]]
        
        if len(top_words) >= min_words:
            # Always use at least min_words (default 2) words
            words_to_use = top_words[:min_words] if len(top_words) >= min_words else top_words
            capitalized = [word.capitalize() for word in words_to_use]
            
            # Use space to join all words
            return " ".join(capitalized)
        elif len(top_words) == 1:
            # If only one word found, add a generic second word to meet minimum requirement
            return f"{top_words[0].capitalize()} Topic"
        
        return "General Topic"
    
    def _should_combine_words(self, word1: str, word2: str) -> bool:
        """
        Determine if two words should be combined with "&" symbol.
        Returns True only if both words are meaningful and form a natural pair.
        
        Rules:
        - Don't combine if one is a verb and the other is a noun (prefer noun)
        - Don't combine if one word is much shorter (likely less important)
        - Don't combine descriptive/qualitative words with nouns
        - Don't combine temporal/location words with nouns
        - Only combine if both are nouns/adjectives of similar importance
        - Prefer single-word titles unless there's a strong semantic relationship
        """
        # Common verbs that shouldn't be combined with nouns
        action_verbs = {
            'buy', 'purchase', 'get', 'find', 'save', 'use', 'make', 'take',
            'give', 'show', 'tell', 'help', 'need', 'want', 'know', 'see',
            'go', 'come', 'look', 'check', 'search', 'order', 'book', 'choose',
            'sell', 'provide', 'offer', 'deliver', 'ship', 'pay', 'cost'
        }
        
        # Descriptive/qualitative words that shouldn't be combined with nouns
        descriptive_words = {
            'good', 'bad', 'best', 'better', 'worse', 'worst', 'great', 'nice',
            'there', 'here', 'free', 'paid', 'new', 'old', 'latest', 'cheap',
            'expensive', 'easy', 'hard', 'simple', 'complex', 'fast', 'slow',
            'top', 'popular', 'famous', 'known', 'available', 'possible'
        }
        
        # Temporal and location words that shouldn't be combined
        temporal_location_words = {
            'when', 'where', 'time', 'date', 'day', 'month', 'year', 'now',
            'today', 'tomorrow', 'yesterday', 'before', 'after', 'during',
            'location', 'place', 'area', 'region', 'city', 'country', 'state',
            'online', 'offline', 'near', 'far', 'local', 'remote'
        }
        
        word1_lower = word1.lower()
        word2_lower = word2.lower()
        
        # If one word is a verb and the other is likely a noun, don't combine
        if word1_lower in action_verbs and word2_lower not in action_verbs:
            return False
        if word2_lower in action_verbs and word1_lower not in action_verbs:
            return False
        
        # If one word is descriptive and the other is a noun, don't combine
        if word1_lower in descriptive_words and word2_lower not in descriptive_words:
            return False
        if word2_lower in descriptive_words and word1_lower not in descriptive_words:
            return False
        
        # If one word is temporal/location and the other is not, don't combine
        if word1_lower in temporal_location_words and word2_lower not in temporal_location_words:
            return False
        if word2_lower in temporal_location_words and word1_lower not in temporal_location_words:
            return False
        
        # If one word is much shorter (less than 4 chars), it's likely less important
        # Only combine if both are substantial words
        if len(word1) < 4 or len(word2) < 4:
            # Don't combine short words - prefer single-word titles
            return False
        
        # If both words are very short (less than 3 chars), don't combine
        if len(word1) < 3 or len(word2) < 3:
            return False
        
        # Additional check: if one word is significantly longer, prefer the longer one
        # (longer words are usually more specific and meaningful)
        length_diff = abs(len(word1) - len(word2))
        if length_diff > 5:  # If one word is much longer, don't combine
            return False
        
        # Only combine if both words are substantial, similar length, and neither is a verb/descriptive/temporal word
        # This means they're likely both nouns or both adjectives
        return True

    def _unique_group_id_for_domain(self, domain: Domain, base_id: str) -> str:
        # Normalize base_id to term format (minimum 2 words, max 4 words)
        normalized_base = self._normalize_to_term(base_id, min_words=2, max_words=4)
        
        # Remove any numbers from the base title
        normalized_base = self._remove_numbers_from_text(normalized_base)
        
        # Ensure we still have at least 2 words after number removal
        words = normalized_base.split()
        if len(words) < 2:
            # If we lost words during number removal, add a generic word
            if len(words) == 1:
                normalized_base = f"{normalized_base} Topic"
            else:
                normalized_base = "General Topic"
        
        # truncate base to 90 chars to allow suffixes within 100-char field limit
        base = normalized_base[:90].rstrip()
        candidate = base
        
        # Use descriptive suffixes instead of numbers for uniqueness
        descriptive_suffixes = ['Advanced', 'Essential', 'Core', 'Premium', 'Standard', 
                               'Basic', 'Professional', 'Expert', 'Complete', 'Ultimate']
        suffix_index = 0
        
        while PromptGroup.objects.filter(domain=domain, group_id=candidate).exists():
            if suffix_index < len(descriptive_suffixes):
                # Try adding a descriptive suffix
                suffix = descriptive_suffixes[suffix_index]
                candidate = f"{base} {suffix}"
                suffix_index += 1
            else:
                # If we run out of descriptive suffixes, use alphabetical suffixes
                suffix_char = chr(ord('A') + (suffix_index - len(descriptive_suffixes)))
                candidate = f"{base} {suffix_char}"
                suffix_index += 1
            
            if len(candidate) > 100:
                candidate = candidate[:100]
        
        return candidate
    
    def _remove_numbers_from_text(self, text: str) -> str:
        """
        Remove all numbers and numeric patterns from text.
        Returns the cleaned text, or "General" if text becomes empty.
        """
        if not text:
            return "General"
        
        import re
        # Remove standalone numbers
        text = re.sub(r'\b\d+\b', '', text)
        # Remove numbers in parentheses like "(1)", "(2)"
        text = re.sub(r'\s*\(\d+\)\s*', '', text)
        # Remove numbers with dashes like "-1", "-2"
        text = re.sub(r'\s*-\d+\s*', '', text)
        # Remove any remaining numeric characters
        text = re.sub(r'\d+', '', text)
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # If text becomes empty after removing numbers, return default
        if not text:
            return "General"
        
        return text

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

            # Get ALL prompts in this cluster (both primary and secondary) for title generation
            # Note: Primary/secondary split happens AFTER title generation, so this includes all prompts
            cluster_prompts = [texts[i] for i in inds]

            normalized_title = None

            # Prefer ChatGPT-generated titles when available (uses ALL prompts in the cluster)
            chatgpt_title = self._generate_title_with_chatgpt(cluster_prompts)
            if chatgpt_title:
                normalized_title = self._normalize_to_term(chatgpt_title, min_words=2, max_words=4)
                normalized_title = self._remove_numbers_from_text(normalized_title)

            if not normalized_title:
                # Use smart NLP-based title extraction as fallback
                smart_title = self._extract_smart_title_from_prompts(cluster_prompts)
                if smart_title:
                    normalized_title = self._normalize_to_term(smart_title, min_words=2, max_words=4)
                    normalized_title = self._remove_numbers_from_text(normalized_title)

            if not normalized_title:
                # Final fallback titles
                fallback_titles = ['General Topics', 'Core Concepts', 'Key Themes',
                                   'Main Topics', 'Primary Themes', 'Essential Topics',
                                   'Important Concepts', 'Central Themes', 'Key Topics',
                                   'Main Concepts']
                fallback_index = label % len(fallback_titles)
                normalized_title = fallback_titles[fallback_index]
            info['title'] = normalized_title

            # Primary = top 1-3 closest; Secondary = rest
            sorted_within = [inds[i] for i in np.argsort(dists)]
            primary_count = min(3, len(sorted_within))
            primary_indices = sorted_within[:primary_count]
            secondary_indices = sorted_within[primary_count:]
            
            # Preserve original prompt dictionaries (with keyword info) instead of just text
            info['primary_prompts'] = [prompts[i] for i in primary_indices]
            info['secondary_prompts'] = [prompts[i] for i in secondary_indices]

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

    def _generate_title_with_chatgpt(self, prompts_texts: List[str]) -> str:
        """
        Try to generate a prompt-group title using ChatGPT with ALL prompts in the group.
        Returns empty string if not available.
        """
        if not prompts_texts:
            return ''
        try:
            print(f"Generating ChatGPT title using {len(prompts_texts)} prompts (all prompts in group)")
            title = self.chatgpt_client.generate_group_title(prompts_texts)
            if title:
                print(f"ChatGPT group title generated: {title} (from {len(prompts_texts)} prompts)")
                return title
        except Exception as exc:
            print(f"ChatGPT title generation failed: {exc}")
        return ''

    def _extract_smart_title_from_prompts(self, prompts_texts: List[str]) -> str:
        """
        Extract a smart, concise title from a list of prompts using improved NLP techniques.
        Analyzes all prompts together to find common themes and meaningful phrases.
        Prioritizes words/phrases that appear across multiple prompts.

        Args:
            prompts_texts: List of prompt text strings from a cluster

        Returns:
            A clean, professional term (max 2 words joined with space)
        """
        from collections import Counter
        import re

        # Comprehensive stop words including temporal, location, and descriptive words
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
            'get', 'make', 'find', 'use', 'help', 'know', 'need', 'want', 'tell', 'show',
            'there', 'here', 'good', 'bad', 'best', 'better', 'worse', 'worst',  # Descriptive/qualitative
            'online', 'offline', 'free', 'paid', 'new', 'old', 'latest',  # Common but not descriptive
        }
        
        # Domain-specific nouns that should be prioritized
        domain_nouns = {
            'medicine', 'medicines', 'medication', 'medications', 'prescription', 'prescriptions',
            'app', 'apps', 'application', 'applications', 'software', 'platform', 'platforms',
            'service', 'services', 'product', 'products', 'brand', 'brands',
            'purchase', 'buying', 'buy', 'shopping', 'order', 'ordering',
            'price', 'pricing', 'cost', 'costs', 'payment', 'payments',
            'delivery', 'shipping', 'location', 'locations', 'store', 'stores',
            'review', 'reviews', 'rating', 'ratings', 'quality', 'features',
            'guide', 'guides', 'tutorial', 'tutorials', 'help', 'support',
            'information', 'details', 'specifications', 'benefits', 'advantages'
        }

        # Collect all meaningful words and bigrams from ALL prompts
        all_words = []
        all_bigrams = []

        for prompt in prompts_texts:
            # Clean and normalize text
            cleaned = re.sub(r'[^\w\s]', ' ', prompt.lower())
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            words = cleaned.split()

            # Extract meaningful words
            meaningful = []
            for word in words:
                word_clean = word.strip('.,!?;:\'"()[]{}').lower()
                # Filter out numbers and words containing numbers
                if (word_clean and 
                    word_clean not in stop_words and 
                    len(word_clean) > 2 and 
                    word_clean.isalpha() and
                    not any(char.isdigit() for char in word_clean)):  # No numbers
                    meaningful.append(word_clean)
                    all_words.append(word_clean)

            # Extract bigrams (adjacent meaningful words) - these are likely noun phrases
            for i in range(len(meaningful) - 1):
                word1 = meaningful[i]
                word2 = meaningful[i + 1]
                # Only create bigram if both words are meaningful (not stop words)
                if word1 not in stop_words and word2 not in stop_words:
                    bigram = f"{word1} {word2}"
                    all_bigrams.append(bigram)

        # Count frequencies - words/phrases that appear in multiple prompts are more important
        word_freq = Counter(all_words)
        bigram_freq = Counter(all_bigrams)
        
        # Boost scores for domain-specific nouns
        for word in word_freq:
            if word in domain_nouns:
                word_freq[word] = word_freq[word] * 2  # Double the frequency for domain nouns

        # Strategy 1: Prioritize bigrams that appear in multiple prompts
        # These represent common themes across prompts
        if bigram_freq:
            # For small clusters (<=2 prompts), accept bigrams that appear once
            # For larger clusters, prefer bigrams that appear in multiple prompts
            min_count = 1 if len(prompts_texts) <= 2 else max(1, len(prompts_texts) // 2)
            
            # Get common bigrams sorted by frequency
            # Prioritize bigrams that contain domain nouns
            all_common_bigrams = [(bg, count) for bg, count in bigram_freq.most_common(10) if count >= min_count]
            
            # Score bigrams: prioritize those with domain nouns
            scored_bigrams = []
            for bg, count in all_common_bigrams:
                words = bg.split()
                score = count
                # Boost score if bigram contains domain nouns
                if len(words) == 2:
                    if words[0] in domain_nouns:
                        score += 10
                    if words[1] in domain_nouns:
                        score += 10
                    # Boost if both are domain nouns
                    if words[0] in domain_nouns and words[1] in domain_nouns:
                        score += 20
                scored_bigrams.append((score, bg, count))

            # Sort by score (highest first)
            scored_bigrams.sort(reverse=True, key=lambda x: x[0])
            
            if scored_bigrams:
                # Take the best scored bigram
                _, best_bigram, count = scored_bigrams[0]
                words = best_bigram.split()
                
                # Ensure we have exactly 2 words (always return at least 2 words)
                if len(words) == 2:
                    # Additional validation: both words should be meaningful
                    if len(words[0]) > 2 and len(words[1]) > 2:
                        # Always use both words (minimum 2 words requirement)
                        return f"{words[0].capitalize()} {words[1].capitalize()}"
                elif len(words) == 1:
                    # If only one word, add a generic second word
                    return f"{words[0].capitalize()} Topic"

        # Strategy 2: Use most common individual words that appear across prompts
        # Prioritize domain-specific nouns
        if word_freq:
            # Prefer words that appear in multiple prompts
            min_word_count = 1 if len(prompts_texts) <= 2 else max(1, len(prompts_texts) // 2)
            
            # Sort by frequency, but prioritize domain nouns
            sorted_words = sorted(word_freq.items(), key=lambda x: (x[0] in domain_nouns, x[1]), reverse=True)
            common_words = [(w, count) for w, count in sorted_words[:10] if count >= min_word_count]
            
            if len(common_words) >= 2:
                # Take top 2 most common words (prioritizing domain nouns)
                word1, count1 = common_words[0]
                word2, count2 = common_words[1]
                # Ensure both words are different and meaningful
                if word1 != word2 and len(word1) > 2 and len(word2) > 2:
                    # Always use both words (minimum 2 words requirement)
                    return f"{word1.capitalize()} {word2.capitalize()}"
            elif len(common_words) == 1:
                word, count = common_words[0]
                if len(word) > 2:
                    # If only one word, add a generic second word
                    return f"{word.capitalize()} Topic"

        # Strategy 3: Fallback - use most frequent words, prioritizing domain nouns
        if word_freq:
            # Sort by domain noun priority first, then frequency
            sorted_words = sorted(word_freq.items(), key=lambda x: (x[0] in domain_nouns, x[1]), reverse=True)
            top_words = [word for word, _ in sorted_words[:2] if len(word) > 2]
            if len(top_words) >= 2:
                word1, word2 = top_words[0], top_words[1]
                # Always use both words (minimum 2 words requirement)
                return f"{word1.capitalize()} {word2.capitalize()}"
            elif len(top_words) == 1:
                # If only one word, add a generic second word
                return f"{top_words[0].capitalize()} Topic"

        # Last resort: use first meaningful words from first prompt
        if prompts_texts:
            first_prompt = prompts_texts[0]
            cleaned = re.sub(r'[^\w\s]', ' ', first_prompt.lower())
            words = cleaned.split()
            meaningful = [w for w in words if w not in stop_words and len(w) > 2 and w.isalpha() and not any(char.isdigit() for char in w)][:2]
            if len(meaningful) >= 2:
                word1, word2 = meaningful[0], meaningful[1]
                # Always use both words (minimum 2 words requirement)
                return f"{word1.capitalize()} {word2.capitalize()}"
            elif len(meaningful) == 1:
                # If only one word, add a generic second word
                return f"{meaningful[0].capitalize()} Topic"

        return "General Topic"

    def _extract_theme_from_group(self, group_data: Dict[str, Any]) -> str:
        """
        Extract a concise theme from the primary prompt.
        Simple extraction: remove question words and keep key nouns/verbs.
        Example: "What helps with relieving vaginal dryness?" -> "vaginal dryness relief"
        """
        # Priority 1: Use primary prompt text
        primary_prompts = group_data.get('primary_prompts', [])
        if primary_prompts:
            # Get the first primary prompt
            prompt_item = primary_prompts[0]
            if isinstance(prompt_item, dict):
                prompt_text = (prompt_item.get('prompt_text') or prompt_item.get('prompt') or '').strip()
            else:
                prompt_text = str(prompt_item).strip()

            if prompt_text:
                # Simple extraction from prompt
                theme = self._extract_key_terms_from_prompt(prompt_text)
                if theme and theme != "General":
                    return theme

        # Priority 2: Fallback to title if no primary prompt available
        title = group_data.get('title', '').strip()
        if title and title != 'Untitled':
            theme = self._extract_key_terms_from_prompt(title)
            if theme and theme != "General":
                return theme

        # Fallback: if no meaningful theme, use "General Topic"
        return "General Topic"

    def _extract_key_terms_from_prompt(self, prompt: str) -> str:
        """
        Extract key terms from a prompt question using GPT-4o-mini.
        Example: "What helps with relieving vaginal dryness?" -> "Vaginal Dryness Relief"
        """
        if not prompt or not prompt.strip():
            return "General Topic"

        # Use GPT-4o-mini to extract key terms intelligently
        try:
            title = self.chatgpt_client._extract_title_from_prompt(prompt)
            if title and title != "General":
                return title
        except Exception as e:
            logger.warning(f"Failed to extract title using GPT-4o-mini: {e}, using fallback")

        # Fallback: Simple extraction (if GPT fails)
        return self._simple_title_extraction(prompt)

    def _simple_title_extraction(self, prompt: str) -> str:
        """
        Fallback: Simple rule-based title extraction.
        Used only if GPT-4o-mini API fails.
        """
        text = prompt.strip().lower()
        text = text.rstrip('?').strip()

        # Remove common question starters
        question_starters = ['what is', 'what are', 'what', 'how to', 'how', 'why', 'when', 'where', 'who']
        for starter in question_starters:
            if text.startswith(starter + ' '):
                text = text[len(starter):].strip()
                break

        # Remove filler words
        filler_words = {'the', 'a', 'an', 'is', 'are', 'some', 'best', 'good'}
        words = [w for w in text.split() if w not in filler_words and len(w) > 2]

        # Take first 4 words
        result = ' '.join(words[:4])
        result = ' '.join(word.capitalize() for word in result.split())

        return result if len(result.split()) >= 2 else "General Topic"
    
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
