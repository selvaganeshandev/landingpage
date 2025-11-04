#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta
import random

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from authentication.models import Organisation, Account
from domains.models import Domain
from prompts.models import PromptGroup, Prompt, PromptAnalytics

def create_test_data():
    print("Creating test data...")
    
    # Get or create organization
    org, created = Organisation.objects.get_or_create(
        name="Test Organization",
        defaults={
            'industry': 'Technology',
            'created_at': datetime.now(),
            'modified_at': datetime.now()
        }
    )
    print(f"Organization: {'Created' if created else 'Found'} - {org.name}")
    
    # Get or create domain
    domain, created = Domain.objects.get_or_create(
        name="Test Domain",
        defaults={
            'url': 'https://testdomain.com',
            'organisation': org,
            'total_mentions': 0,
            'total_citations': 0,
            'visibility_score': 0.00,
            'average_position': 0.00,
            'active_alerts': 0,
            'sentiment': 'neutral',
            'sentiment_score': 0.00
        }
    )
    print(f"Domain: {'Created' if created else 'Found'} - {domain.name}")
    
    # Create PromptGroup
    group, created = PromptGroup.objects.get_or_create(
        group_id="test-group-1",
        defaults={
            'domain': domain,
            'organisation': org,
            'total_mentions': 0,
            'total_citations': 0,
            'average_position': 0.00,
            'created_at': datetime.now(),
            'modified_at': datetime.now()
        }
    )
    print(f"PromptGroup: {'Created' if created else 'Found'} - {group.group_id}")
    
    # Create Prompt
    prompt, created = Prompt.objects.get_or_create(
        prompt="best vegan protein powder for athletes",
        defaults={
            'group': group,
            'domain': domain,
            'organisation': org,
            'track_status': 'active',
            'type': 'primary',
            'last_tracked_at': datetime.now(),
            'track_message': 'Successfully tracked',
            'created_at': datetime.now(),
            'modified_at': datetime.now()
        }
    )
    print(f"Prompt: {'Created' if created else 'Found'} - {prompt.prompt[:50]}...")
    
    # Create multiple PromptAnalytics entries (mentions)
    platforms = ['ChatGPT', 'Claude', 'Perplexity', 'Gemini', 'Grok']
    sentiments = ['positive', 'neutral', 'negative']
    
    for i in range(10):
        platform = random.choice(platforms)
        sentiment = random.choice(sentiments)
        sentiment_score = random.uniform(-1.0, 1.0)
        
        analytics, created = PromptAnalytics.objects.get_or_create(
            prompt=prompt,
            platform=platform,
            defaults={
                'domain': domain,
                'organisation': org,
                'is_mention': True,
                'total_mentions': random.randint(1, 100),
                'total_citations': random.randint(1, 50),
                'position': random.uniform(1.0, 10.0),
                'sentiment': sentiment,
                'sentiment_score': sentiment_score,
                'context_summary': f"This is a test mention for {platform} about vegan protein powder. The sentiment is {sentiment}.",
                'citations': [
                    {
                        'text': f'VegFit Pro stands out as a top choice for athletes seeking plant-based protein',
                        'source': 'vegfitpro.com',
                        'url': 'https://vegfitpro.com/products/protein-powder',
                        'description': 'Product page citing key benefits and features'
                    },
                    {
                        'text': f'superior amino acid blend makes it ideal for post-workout recovery',
                        'source': 'healthline.com',
                        'url': 'https://healthline.com/nutrition/vegan-protein-powder',
                        'description': 'Third-party nutritional analysis'
                    }
                ],
                'views': random.randint(100, 1000),
                'shares': random.randint(10, 100),
                'engagement_score': random.uniform(0.0, 10.0),
                'competitor_mentions': ['Competitor A', 'Competitor B'],
                'key_topics': ['protein', 'vegan', 'athletes', 'nutrition'],
                'position_history': [
                    {'date': '2025-10-20', 'position': 2.5},
                    {'date': '2025-10-21', 'position': 1.8},
                    {'date': '2025-10-22', 'position': 1.2}
                ],
                'created_at': datetime.now() - timedelta(hours=random.randint(1, 48)),
                'modified_at': datetime.now()
            }
        )
        
        if created:
            print(f"Created analytics entry {i+1}: {platform} - {sentiment}")
    
    # Update group totals
    group.total_mentions = PromptAnalytics.objects.filter(prompt__group=group, is_mention=True).count()
    group.total_citations = sum(analytics.total_citations for analytics in PromptAnalytics.objects.filter(prompt__group=group, is_mention=True))
    group.average_position = sum(analytics.position for analytics in PromptAnalytics.objects.filter(prompt__group=group, is_mention=True)) / group.total_mentions if group.total_mentions > 0 else 0
    group.save()
    
    print(f"\nTest data created successfully!")
    print(f"Organization: {org.name}")
    print(f"Domain: {domain.name}")
    print(f"PromptGroup: {group.group_id}")
    print(f"Prompt: {prompt.prompt[:50]}...")
    print(f"Analytics entries: {PromptAnalytics.objects.filter(prompt__group=group, is_mention=True).count()}")

if __name__ == "__main__":
    create_test_data()
