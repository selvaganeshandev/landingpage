"""
Test script to verify prompt-keyword linking in domain processing
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
ENGINE_ROOT = Path(__file__).resolve().parents[3] / 'engine'
sys.path.insert(0, str(ENGINE_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from shared_models.models import Domain, Keyword, Prompt, PromptKeyword
from django.db.models import Count
from django.utils import timezone


def test_prompt_keyword_linking(domain_id: int = None):
    """
    Test that prompts are properly linked to keywords after domain processing
    
    Args:
        domain_id: Optional domain ID to test. If None, tests the most recently processed domain.
    """
    print("=" * 80)
    print("Testing Prompt-Keyword Linking")
    print("=" * 80)
    
    # Get domain to test
    if domain_id:
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            print(f"❌ Domain {domain_id} not found")
            return False
    else:
        # Get most recently processed domain
        domain = Domain.objects.filter(
            processing_status__in=['PROC', 'COMP']
        ).order_by('-modified_at').first()
        
        if not domain:
            print("❌ No processed domains found. Please process a domain first.")
            return False
    
    print(f"\n📋 Testing Domain: {domain.name} (ID: {domain.id})")
    print(f"   Status: {domain.processing_status}")
    print(f"   Modified: {domain.modified_at}")
    
    # Get all prompts for this domain
    prompts = Prompt.objects.filter(group__domain=domain)
    total_prompts = prompts.count()
    
    print(f"\n📊 Prompt Statistics:")
    print(f"   Total prompts: {total_prompts}")
    
    if total_prompts == 0:
        print("⚠️  No prompts found for this domain. Domain may not have been processed yet.")
        return False
    
    # Get all prompt-keyword links
    prompt_keywords = PromptKeyword.objects.filter(prompt__group__domain=domain)
    total_links = prompt_keywords.count()
    
    print(f"   Total prompt-keyword links: {total_links}")
    
    # Get prompts with links
    prompts_with_links = prompts.filter(prompt_keywords__isnull=False).distinct()
    prompts_without_links = prompts.exclude(id__in=prompts_with_links.values_list('id', flat=True))
    
    print(f"   Prompts with keyword links: {prompts_with_links.count()}")
    print(f"   Prompts without keyword links: {prompts_without_links.count()}")
    
    # Calculate percentage
    if total_prompts > 0:
        link_percentage = (prompts_with_links.count() / total_prompts) * 100
        print(f"   Link coverage: {link_percentage:.1f}%")
    
    # Show sample of prompts without links
    if prompts_without_links.exists():
        print(f"\n⚠️  Sample prompts WITHOUT keyword links:")
        for prompt in prompts_without_links[:5]:
            print(f"   - Prompt ID {prompt.id}: '{prompt.prompt[:60]}...'")
    
    # Show sample of prompts with links
    if prompts_with_links.exists():
        print(f"\n✅ Sample prompts WITH keyword links:")
        for prompt in prompts_with_links[:5]:
            keywords = [pk.keyword.keyword for pk in prompt.prompt_keywords.all()]
            print(f"   - Prompt ID {prompt.id}: '{prompt.prompt[:60]}...'")
            print(f"     Keywords: {', '.join(keywords)}")
    
    # Get keywords and their link counts
    keywords = Keyword.objects.filter(domain=domain)
    print(f"\n📊 Keyword Statistics:")
    print(f"   Total keywords: {keywords.count()}")
    
    # Keywords with links
    keywords_with_links = keywords.filter(prompt_keywords__isnull=False).distinct()
    keywords_without_links = keywords.exclude(id__in=keywords_with_links.values_list('id', flat=True))
    
    print(f"   Keywords with prompt links: {keywords_with_links.count()}")
    print(f"   Keywords without prompt links: {keywords_without_links.count()}")
    
    if keywords_without_links.exists():
        print(f"\n⚠️  Sample keywords WITHOUT prompt links:")
        for keyword in keywords_without_links[:5]:
            print(f"   - Keyword: '{keyword.keyword}'")
    
    # Summary
    print(f"\n" + "=" * 80)
    if prompts_without_links.count() == 0:
        print("✅ SUCCESS: All prompts are linked to keywords!")
        return True
    else:
        print(f"❌ ISSUE: {prompts_without_links.count()} prompts are not linked to keywords")
        print(f"   Link coverage: {link_percentage:.1f}%")
        return False


def test_keyword_prompt_distribution(domain_id: int = None):
    """
    Test the distribution of prompts across keywords
    """
    print("\n" + "=" * 80)
    print("Testing Keyword-Prompt Distribution")
    print("=" * 80)
    
    # Get domain
    if domain_id:
        domain = Domain.objects.get(id=domain_id)
    else:
        domain = Domain.objects.filter(
            processing_status__in=['PROC', 'COMP']
        ).order_by('-modified_at').first()
    
    if not domain:
        print("❌ No domain found")
        return
    
    # Get keywords with their prompt counts
    keywords = Keyword.objects.filter(domain=domain).annotate(
        prompt_count=Count('prompt_keywords')
    ).order_by('-prompt_count')
    
    print(f"\n📊 Keywords and their prompt counts:")
    for keyword in keywords[:10]:
        print(f"   '{keyword.keyword}': {keyword.prompt_count} prompts")
    
    # Check for keywords with no prompts
    keywords_without_prompts = [kw for kw in keywords if kw.prompt_count == 0]
    if keywords_without_prompts:
        print(f"\n⚠️  {len(keywords_without_prompts)} keywords have no prompts linked:")
        for kw in keywords_without_prompts[:5]:
            print(f"   - '{kw.keyword}'")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test prompt-keyword linking')
    parser.add_argument('--domain-id', type=int, help='Domain ID to test (optional)')
    parser.add_argument('--distribution', action='store_true', help='Show keyword-prompt distribution')
    
    args = parser.parse_args()
    
    # Run tests
    success = test_prompt_keyword_linking(args.domain_id)
    
    if args.distribution:
        test_keyword_prompt_distribution(args.domain_id)
    
    sys.exit(0 if success else 1)

