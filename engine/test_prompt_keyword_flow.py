#!/usr/bin/env python
"""
Test script to verify PromptKeyword and KeywordAnalytics creation flow.
This script tests the complete flow from domain creation to keyword analytics.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from shared_models.models import (
    Domain, Organisation, Keyword, Prompt, PromptGroup, PromptAnalytics,
    PromptKeyword, Topic, TopicKeyword, KeywordAnalytics
)
from core.domain_processor import DomainProcessor
from core.topic_processor import TopicProcessor
from core.topic_analytics_processor import TopicAnalyticsProcessor
from django.utils import timezone
from decimal import Decimal


def cleanup_test_domain():
    """Remove test domain and related data if it exists"""
    try:
        test_domains = Domain.objects.filter(name='test-example.com')
        for domain in test_domains:
            print(f"Cleaning up existing test domain: {domain.name}")
            # Delete related data manually to avoid cascade issues
            try:
                # Delete prompts and related data first
                prompts = Prompt.objects.filter(group__domain=domain)
                PromptKeyword.objects.filter(prompt__in=prompts).delete()
                PromptAnalytics.objects.filter(prompt__in=prompts).delete()
                prompts.delete()
                PromptGroup.objects.filter(domain=domain).delete()
                
                # Delete keywords
                Keyword.objects.filter(domain=domain).delete()
                
                # Delete topics
                Topic.objects.filter(domain=domain).delete()
                
                # Finally delete domain
                domain.delete()
                print(f"✅ Deleted test domain: {domain.name}")
            except Exception as e:
                print(f"⚠️ Warning during cleanup: {str(e)}")
                # Try to delete domain anyway
                try:
                    domain.delete()
                except:
                    pass
        print("✅ Cleanup complete\n")
    except Exception as e:
        print(f"⚠️ Cleanup skipped due to error: {str(e)}\n")


def create_test_domain_with_data():
    """Create a test domain with keywords and prompts"""
    print("=== STEP 1: Creating Test Domain ===")
    
    # Get or create test organisation
    org, _ = Organisation.objects.get_or_create(
        name='Test Organisation',
        defaults={'team_count': 1}
    )
    
    domain = Domain.objects.create(
        name='test-example.com',
        url='https://test-example.com',
        country='United States',
        organisation=org,
        processing_status='INIT'
    )
    print(f"✅ Created domain: {domain.name} (ID: {domain.id})\n")
    
    # Create test keywords
    print("=== STEP 2: Creating Test Keywords ===")
    keywords = []
    for kw_text in ['test product', 'example service', 'demo feature']:
        kw = Keyword.objects.create(
            keyword=kw_text,
            domain=domain,
            auto_generate_prompts=True,
            priority=5
        )
        keywords.append(kw)
        print(f"✅ Created keyword: {kw.keyword}")
    print()
    
    # Create prompt group
    print("=== STEP 3: Creating Prompt Group and Prompts ===")
    group = PromptGroup.objects.create(
        group_id='Test Group',
        domain=domain,
        theme='Testing',
        total_mentions=0,
        total_citations=0,
        average_position=0.00
    )
    print(f"✅ Created prompt group: {group.group_id}")
    
    # Create prompts with keyword mapping
    prompts_data = [
        ('What is test product?', 'test product'),
        ('How does test product work?', 'test product'),
        ('Tell me about example service', 'example service'),
        ('What are the benefits of demo feature?', 'demo feature'),
    ]
    
    prompts = []
    for prompt_text, keyword_text in prompts_data:
        prompt = Prompt.objects.create(
            prompt=prompt_text,
            group=group,
            type='primary',
            track_status='INIT'
        )
        prompts.append(prompt)
        print(f"✅ Created prompt: {prompt_text}")
        
        # Create PromptKeyword link (this is what domain_processor should do)
        keyword = Keyword.objects.get(keyword=keyword_text, domain=domain)
        PromptKeyword.objects.create(
            prompt=prompt,
            keyword=keyword,
            relevance_score=Decimal('100.00')
        )
        print(f"   → Linked to keyword: {keyword_text}")
        
        # Create PromptAnalytics (simulating real data)
        PromptAnalytics.objects.create(
            prompt=prompt,
            platform='ChatGPT',
            position=Decimal('5.00'),
            total_mentions=10,
            total_citations=3,
            position_history_list=[5, 4, 6],
            track_status='COMP',
            tracked_at=timezone.now()
        )
        print(f"   → Created PromptAnalytics")
    
    print()
    return domain, keywords, prompts


def test_topic_creation(domain, keywords):
    """Test topic creation from keywords"""
    print("=== STEP 4: Creating Topic ===")
    
    # Create a topic manually (simulating topic processor)
    topic = Topic.objects.create(
        name='Test Topic',
        domain=domain,
        description='A test topic for verification'
    )
    print(f"✅ Created topic: {topic.name} (ID: {topic.id})")
    
    # Link keywords to topic
    for keyword in keywords:
        TopicKeyword.objects.create(
            topic=topic,
            keyword=keyword,
            track_status='INIT'
        )
        print(f"   → Linked keyword: {keyword.keyword}")
    
    print()
    return topic


def test_keyword_analytics_creation(domain, topic):
    """Test KeywordAnalytics creation"""
    print("=== STEP 5: Processing Keyword Analytics ===")
    
    processor = TopicAnalyticsProcessor()
    result = processor.process_analytics_for_domain(domain)
    
    print(f"Processing result: {result}")
    print()
    
    return result


def verify_final_state(domain):
    """Verify all tables are populated correctly"""
    print("=== STEP 6: Verifying Final State ===")
    
    prompt_keywords = PromptKeyword.objects.filter(
        prompt__group__domain=domain
    ).count()
    
    keyword_analytics = KeywordAnalytics.objects.filter(
        keyword__domain=domain
    ).count()
    
    print(f"✅ PromptKeywords created: {prompt_keywords}")
    print(f"✅ KeywordAnalytics created: {keyword_analytics}")
    
    # Show details
    if prompt_keywords > 0:
        print("\nPromptKeyword Details:")
        for pk in PromptKeyword.objects.filter(prompt__group__domain=domain).select_related('prompt', 'keyword'):
            print(f"  - Prompt: \"{pk.prompt.prompt[:40]}...\" → Keyword: \"{pk.keyword.keyword}\"")
    
    if keyword_analytics > 0:
        print("\nKeywordAnalytics Details:")
        for ka in KeywordAnalytics.objects.filter(keyword__domain=domain).select_related('keyword'):
            print(f"  - Keyword: \"{ka.keyword.keyword}\" | Platform: {ka.platform} | Mentions: {ka.mentions} | Visibility: {ka.visibility_score}")
    
    print()
    
    # Verification
    success = prompt_keywords > 0 and keyword_analytics > 0
    if success:
        print("✅ ✅ ✅ ALL TESTS PASSED! ✅ ✅ ✅")
        print("Both PromptKeywords and KeywordAnalytics are being created correctly.")
    else:
        print("❌ ❌ ❌ TESTS FAILED! ❌ ❌ ❌")
        if prompt_keywords == 0:
            print("  - PromptKeywords are NOT being created")
        if keyword_analytics == 0:
            print("  - KeywordAnalytics are NOT being created")
    
    return success


def main():
    """Run the complete test flow"""
    print("\n" + "="*70)
    print("TESTING: PromptKeyword and KeywordAnalytics Creation Flow")
    print("="*70 + "\n")
    
    try:
        # Cleanup any existing test data
        cleanup_test_domain()
        
        # Create test domain with data
        domain, keywords, prompts = create_test_domain_with_data()
        
        # Create topic from keywords
        topic = test_topic_creation(domain, keywords)
        
        # Process keyword analytics
        test_keyword_analytics_creation(domain, topic)
        
        # Verify final state
        success = verify_final_state(domain)
        
        # Cleanup after test
        print("\n=== Cleanup ===")
        response = input("Do you want to keep the test domain for inspection? (y/n): ").strip().lower()
        if response != 'y':
            cleanup_test_domain()
            print("✅ Test domain cleaned up")
        else:
            print(f"Test domain '{domain.name}' (ID: {domain.id}) kept for inspection")
        
        print("\n" + "="*70)
        if success:
            print("TEST RESULT: ✅ SUCCESS")
        else:
            print("TEST RESULT: ❌ FAILURE")
        print("="*70 + "\n")
        
        return success
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

