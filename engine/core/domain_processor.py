import threading
import time
import uuid
from typing import List, Dict, Any, Tuple
import re
from django.conf import settings
from django.db import transaction
from shared_models.models import Domain, Keyword, PromptGroup, Prompt, PromptAnalytics, Organisation
from .rest_client import DataForSEOClient
from .chatgpt_client import ChatGPTClient
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans


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
            domain.track_status = 'Processing'
            domain.track_message = 'Starting domain processing...'
            domain.save()
            
            # Step 1: Scrape keywords from DataForSEO
            print(f"Scraping keywords for {domain.name}")
            kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
            keywords = self.dataforseo_client.scrape_target_domain(domain.name, limit=kw_limit)
            
            if not keywords:
                domain.processing_status = 'FAIL'
                domain.track_status = 'Failed'
                domain.track_message = 'No keywords found from DataForSEO API'
                domain.save()
                return
            
            # Step 2: Store keywords in database
            print(f"Storing {len(keywords)} keywords for {domain.name}")
            self._store_keywords(domain, keywords)
            
            # Step 3: Generate prompts using ChatGPT
            print(f"Generating prompts for {domain.name}")
            prompts = self.chatgpt_client.generate_prompts_from_keywords(keywords, domain.name)

            # Ensure distinct prompts and a minimum of 10 prompts
            prompts = self._deduplicate_prompts(prompts)
            min_prompts = getattr(settings, 'PROMPT_MIN_COUNT', 10)
            if len(prompts) < min_prompts:
                prompts = self._supplement_prompts_to_minimum(prompts, keywords, min_count=min_prompts)

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
                domain.track_status = 'Failed'
                domain.track_message = 'Failed to generate prompts with ChatGPT'
                domain.save()
                return
            
            # Step 4: Group prompts using SentenceTransformer-based NLP
            print(f"Grouping prompts for {domain.name}")
            grouped_prompts = self._group_prompts_with_sentence_transformers(prompts)
            
            if not grouped_prompts:
                domain.processing_status = 'FAIL'
                domain.track_status = 'Failed'
                domain.track_message = 'Failed to group prompts'
                domain.save()
                return
            
            # Step 5: Store prompts and groups in database
            print(f"Storing {len(grouped_prompts)} prompt groups for {domain.name}")
            self._store_prompt_groups(domain, grouped_prompts)
            
            # Step 6: Update domain status to completed
            domain.processing_status = 'COMP'
            domain.track_status = 'Completed'
            domain.track_message = f'Successfully processed {len(keywords)} keywords and {len(grouped_prompts)} prompt groups'
            domain.save()
            
            print(f"Successfully processed domain: {domain.name}")
            
        except Exception as e:
            print(f"Error processing domain {domain_id}: {str(e)}")
            try:
                domain = Domain.objects.get(id=domain_id)
                domain.processing_status = 'FAIL'
                domain.track_status = 'Failed'
                domain.track_message = f'Processing failed: {str(e)}'
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
        Store keywords in the database
        """
        with transaction.atomic():
            for keyword_text in keywords:
                keyword, created = Keyword.objects.get_or_create(
                    keyword=keyword_text,
                    domain=domain,
                    organisation=domain.organisation,
                    defaults={
                        'keyword': keyword_text,
                        'domain': domain,
                        'organisation': domain.organisation
                    }
                )
                if created:
                    print(f"Created keyword: {keyword_text}")
    
    def _store_prompt_groups(self, domain: Domain, grouped_prompts: List[Dict[str, Any]]):
        """
        Store prompt groups and prompts in the database
        """
        with transaction.atomic():
            for group_data in grouped_prompts:
                # Create prompt group with interpretable group_id (title)
                desired_group_id = group_data.get('title', 'Untitled').strip() or 'Untitled'
                group_id = self._unique_group_id_for_domain(domain, desired_group_id)
                prompt_group = PromptGroup.objects.create(
                    group_id=group_id,
                    domain=domain,
                    organisation=domain.organisation,
                    total_mentions=0,
                    total_citations=0,
                    average_position=0.00
                )
                
                # Create primary prompts
                primary_prompts = group_data.get('primary_prompts', [])
                for prompt_text in primary_prompts:
                    if prompt_text.strip():
                        prompt = Prompt.objects.create(
                            prompt=prompt_text.strip(),
                            group=prompt_group,
                            domain=domain,
                            organisation=domain.organisation,
                            type='primary',
                            track_status='active'
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
                            domain=domain,
                            organisation=domain.organisation,
                            type='secondary',
                            track_status='active'
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
        for platform in [
            'ChatGPT',
            'Google Gemini',
            'Perplexity'
        ]:
            PromptAnalytics.objects.get_or_create(
                prompt=prompt,
                platform=platform,
                defaults={
                    'prompt': prompt,
                    'domain': domain,
                    'organisation': domain.organisation,
                    'platform': platform,
                    'is_mention': False,
                    'total_mentions': 0,
                    'total_citations': 0,
                    'position': 0.00,
                    'sentiment': 'neutral',
                    'sentiment_score': 0.00,
                    'context_summary': '',
                    'citations': [],
                    'views': 0,
                    'shares': 0,
                    'engagement_score': 0.00,
                    'competitor_mentions': [],
                    'key_topics': [],
                    'position_history': []
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

        model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        texts = [p.get('prompt_text') or p.get('prompt') for p in prompts]
        embeddings = model.encode(texts, convert_to_numpy=True)

        n = len(texts)
        # heuristic for clusters: ~1 cluster per 5 prompts; ensure 1 <= k <= n
        if n >= 10:
            k = max(1, min(10, n // 5))
        else:
            k = max(1, min(2, n))
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

        # compute titles per cluster using centroid closest prompt text
        for label, info in groups.items():
            inds = info['indices']
            centroid = kmeans.cluster_centers_[label]
            cluster_vecs = embeddings[inds]
            dists = np.linalg.norm(cluster_vecs - centroid, axis=1)
            rep_idx_within = int(np.argmin(dists))
            rep_idx = inds[rep_idx_within]
            representative_text = texts[rep_idx]
            # Title as a concise theme: first 6-10 words of representative prompt
            cleaned = self._sanitize_prompt_text(representative_text)
            title = " ".join(cleaned.split()[:8]).strip()
            info['title'] = title or f"Cluster {label+1}"

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
            domain.track_status = 'Scheduled'
            domain.track_message = 'Scheduled for processing by API request'
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
