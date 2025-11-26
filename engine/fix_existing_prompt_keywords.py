#!/usr/bin/env python
"""
Script to retroactively link existing prompts to keywords.
This fixes prompts that were created before the keyword linking was fixed.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from shared_models.models import Prompt, Keyword, PromptKeyword, Domain
from decimal import Decimal
from django.db import transaction

def fix_prompt_keywords_for_domain(domain):
    """Fix prompt-keyword links for a specific domain"""
    print(f"\n{'='*60}")
    print(f"Processing domain: {domain.name} (ID: {domain.id})")
    print(f"{'='*60}")
    
    # Get all prompts for this domain
    prompts = Prompt.objects.filter(group__domain=domain)
    keywords = Keyword.objects.filter(domain=domain)
    
    print(f"Found {prompts.count()} prompts and {keywords.count()} keywords")
    
    if prompts.count() == 0:
        print("No prompts found. Skipping.")
        return
    
    if keywords.count() == 0:
        print("No keywords found. Skipping.")
        return
    
    # Create a mapping of keyword text to Keyword objects
    keyword_map = {kw.keyword.lower(): kw for kw in keywords}
    
    links_created = 0
    links_existing = 0
    links_failed = 0
    
    with transaction.atomic():
        for prompt in prompts:
            prompt_text_lower = prompt.prompt.lower()
            
            # Try to find matching keyword
            matched_keyword = None
            
            # Strategy 1: Check if any keyword appears in the prompt text
            for kw_text, keyword in keyword_map.items():
                if kw_text in prompt_text_lower:
                    matched_keyword = keyword
                    break
            
            # Strategy 2: If no match, use the first keyword as fallback
            if not matched_keyword and keywords.exists():
                matched_keyword = keywords.first()
                print(f"⚠️ Using fallback keyword '{matched_keyword.keyword}' for prompt: '{prompt.prompt[:50]}...'")
            
            if matched_keyword:
                # Check if link already exists
                existing_link = PromptKeyword.objects.filter(
                    prompt=prompt,
                    keyword=matched_keyword
                ).first()
                
                if existing_link:
                    links_existing += 1
                    print(f"✓ Link already exists: Prompt {prompt.id} → Keyword '{matched_keyword.keyword}'")
                else:
                    # Create the link
                    try:
                        PromptKeyword.objects.create(
                            prompt=prompt,
                            keyword=matched_keyword,
                            relevance_score=Decimal('100.00')
                        )
                        links_created += 1
                        print(f"✅ Created link: Prompt {prompt.id} → Keyword '{matched_keyword.keyword}'")
                    except Exception as e:
                        links_failed += 1
                        print(f"❌ Failed to create link for Prompt {prompt.id}: {str(e)}")
            else:
                links_failed += 1
                print(f"❌ No keyword found for prompt: '{prompt.prompt[:50]}...'")
    
    print(f"\n📊 Summary for {domain.name}:")
    print(f"   ✅ Created: {links_created} links")
    print(f"   ⚠️  Already exists: {links_existing} links")
    print(f"   ❌ Failed: {links_failed} links")

def main():
    """Main function"""
    print("="*60)
    print("Fixing existing Prompt-Keyword links")
    print("="*60)
    
    # Get all domains
    domains = Domain.objects.all()
    
    if not domains.exists():
        print("No domains found.")
        return
    
    print(f"Found {domains.count()} domain(s)")
    
    for domain in domains:
        fix_prompt_keywords_for_domain(domain)
    
    print(f"\n{'='*60}")
    print("Done!")
    print(f"{'='*60}")
    
    # Show final statistics
    total_prompts = Prompt.objects.count()
    total_keywords = Keyword.objects.count()
    total_links = PromptKeyword.objects.count()
    
    print(f"\nFinal Statistics:")
    print(f"   Total Prompts: {total_prompts}")
    print(f"   Total Keywords: {total_keywords}")
    print(f"   Total PromptKeywords: {total_links}")
    
    if total_prompts > 0:
        coverage = (total_links / total_prompts) * 100
        print(f"   Coverage: {coverage:.1f}% ({total_links}/{total_prompts} prompts linked)")

if __name__ == '__main__':
    main()

