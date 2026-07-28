"""
Test competitor extraction for appkodes.com with sample LLM response
This simulates what would happen when LLM responses are processed
"""
import os
import django
import sys
from pathlib import Path

# Setup Django
BACKEND_ROOT = Path(__file__).resolve().parents[3] / 'backend'
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from prompts.models import PromptAnalytics, Prompt, PromptGroup
from domains.models import Domain
from competitors.services import CompetitorExtractionService
from django.utils import timezone


def create_sample_analytics_for_appkodes():
    """
    Create sample prompt analytics with competitor mentions for appkodes.com
    This simulates what the LLM processing would create
    """
    try:
        domain = Domain.objects.get(name='appkodes.com')
    except Domain.DoesNotExist:
        print("Domain appkodes.com not found. Please add it first.")
        return None

    print(f"\n{'='*60}")
    print(f"Creating Sample Analytics for {domain.name}")
    print(f"{'='*60}\n")

    # Sample LLM responses that mention competitors
    sample_responses = [
        {
            "prompt_text": "What are the best clone script providers?",
            "response": """When looking for clone script providers, here are some top options:

1. **Miracuves** - Offers ready-made clone scripts for various platforms
   Website: https://miracuves.com
   They provide solutions for marketplace, delivery, and social media platforms.

2. **CodeCanyon** - Marketplace for scripts
   Website: https://codecanyon.net
   Large collection of ready-made scripts and templates.

3. **CloneScripts.co** - Specialized in clone solutions
   Website: https://clonescripts.co
   Focuses on popular app clones for startups.

4. **ScriptGiant** - Custom clone script development
   Website: https://scriptgiant.com
   Provides customizable solutions for various industries.

5. **Trioangle** - Mobile app clone scripts
   Website: https://trioangle.com
   Specializes in on-demand service app clones.

Each platform offers different features, pricing, and customization options. Miracuves and Trioangle are particularly popular for their comprehensive solutions.""",
            "competitors": ["Miracuves", "Codecanyon", "Clonescripts", "Scriptgiant", "Trioangle"]
        },
        {
            "prompt_text": "Best platforms for ready-made app solutions?",
            "response": """For ready-made app solutions and clone scripts, consider these platforms:

**Miracuves** is a leading provider offering various ready-to-launch solutions. They have scripts for food delivery, ride-sharing, and marketplace apps.

**Trioangle Technologies** specializes in on-demand app clones with features like real-time tracking and payment integration. Visit trioangle.com for more details.

**NCrypted** (ncrypted.net) provides business software and clone scripts with extensive customization options.

**Kreativeminds** offers SaaS-based clone solutions for startups looking to launch quickly.

These platforms typically offer:
- Source code access
- Free installation support
- Regular updates
- Technical documentation
""",
            "competitors": ["Miracuves", "Trioangle", "Ncrypted", "Kreativeminds"]
        },
        {
            "prompt_text": "Mobile app development clone script companies",
            "response": """Several companies specialize in clone script development:

1. Miracuves - Known for comprehensive clone solutions
2. Cubix - Custom mobile app development
3. Trioangle - On-demand service app clones
4. Mind Inventory - Full-stack development services
5. Space-O Technologies - Mobile app clones and custom development

Miracuves.com stands out for their rapid delivery and cost-effective solutions. They offer clones of popular platforms like Uber, Airbnb, and Amazon.

Trioangle.com focuses on feature-rich clones with modern UI/UX designs.

These companies provide end-to-end solutions including design, development, deployment, and maintenance.""",
            "competitors": ["Miracuves", "Cubix", "Trioangle", "Mind Inventory", "Space-O Technologies"]
        },
        {
            "prompt_text": "Where to buy app clone scripts?",
            "response": """You can purchase app clone scripts from several reputable sources:

**Codecanyon** (codecanyon.net) - Part of Envato Market, offers thousands of scripts
**Miracuves Solutions** - Specialized clone script provider at miracuves.com
**Clonify** - Budget-friendly clone scripts at clonify.net
**ScriptStore** - Wide variety of ready-made solutions

For marketplace clones specifically:
- Miracuves offers comprehensive marketplace solutions
- Yo!Kart provides multi-vendor marketplace scripts
- CS-Cart is popular for ecommerce marketplaces

Pricing varies from $99 to $5000+ depending on complexity and features.""",
            "competitors": ["Codecanyon", "Miracuves", "Clonify", "Scriptstore", "Yo!Kart", "Cs-Cart"]
        },
        {
            "prompt_text": "Top-rated clone script services in 2024",
            "response": """Based on 2024 reviews and ratings, here are the top clone script services:

🥇 **Miracuves** (miracuves.com)
   - Rating: 4.8/5
   - Known for: Fast delivery, comprehensive solutions
   - Popular products: Multi-service app clones

🥈 **Trioangle Technologies**
   - Rating: 4.6/5
   - Specialization: On-demand service platforms
   - Website: trioangle.com

🥉 **ScriptGiant**
   - Rating: 4.5/5
   - Focus: Custom clone development
   - URL: scriptgiant.com

Other notable mentions:
- **MintTM** - Social networking clones
- **Clone Daddy** - Quick deployment solutions
- **App Cloner Pro** - DIY clone builder

Miracuves leads in customer satisfaction with 500+ successful deployments across 40+ countries.""",
            "competitors": ["Miracuves", "Trioangle", "Scriptgiant", "Minttm", "Clone Daddy", "App Cloner Pro"]
        }
    ]

    # Get or create a prompt group for testing
    prompt_group, _ = PromptGroup.objects.get_or_create(
        domain=domain,
        group_id="test_clone_scripts",
        defaults={
            'theme': 'Clone Scripts',
            'track_status': 'COMP',
            'is_published': True
        }
    )

    created_count = 0
    for idx, sample in enumerate(sample_responses, 1):
        # Create prompt
        prompt, _ = Prompt.objects.get_or_create(
            group=prompt_group,
            prompt=sample['prompt_text'],
            defaults={
                'type': 'primary',
                'track_status': 'COMP'
            }
        )

        # Create or update analytics with competitor mentions
        analytics, created = PromptAnalytics.objects.get_or_create(
            prompt=prompt,
            platform='ChatGPT',
            defaults={
                'is_mention': False,  # appkodes not mentioned in these responses
                'total_mentions': 0,
                'total_citations': 0,
                'context_summary': sample['response'],
                'competitor_mention_list': sample['competitors'],  # THIS IS THE KEY FIELD
                'sentiment_category': 'neutral',
                'sentiment_score': 0.0,
                'track_status': 'COMP',
                'is_published': True
            }
        )

        if created:
            created_count += 1
            print(f"✓ Created analytics {idx}: {sample['prompt_text'][:50]}...")
            print(f"  Competitors found: {', '.join(sample['competitors'])}")
        else:
            # Update existing with new competitor list
            analytics.competitor_mention_list = sample['competitors']
            analytics.context_summary = sample['response']
            analytics.save()
            print(f"✓ Updated analytics {idx}: {sample['prompt_text'][:50]}...")
            print(f"  Competitors found: {', '.join(sample['competitors'])}")

    print(f"\n{'='*60}")
    print(f"Created/Updated {len(sample_responses)} analytics records")
    print(f"{'='*60}\n")

    return domain


def test_extraction(domain):
    """
    Run competitor extraction and show results
    """
    print(f"\n{'='*60}")
    print(f"Running Competitor Extraction")
    print(f"{'='*60}\n")

    service = CompetitorExtractionService(domain)
    created_count, competitor_names = service.extract_and_create_competitors()

    print(f"\n{'='*60}")
    print(f"Extraction Results")
    print(f"{'='*60}")
    print(f"Created: {created_count} new competitors")
    if competitor_names:
        print(f"New Competitors: {', '.join(competitor_names)}")
    print(f"{'='*60}\n")

    # Show all competitors
    from competitors.models import Competitor
    all_competitors = Competitor.objects.filter(domain=domain).order_by('-total_mentions')

    print(f"All Competitors for {domain.name}:")
    print(f"{'-'*60}")
    for idx, comp in enumerate(all_competitors, 1):
        print(f"{idx}. {comp.name}")
        print(f"   Mentions: {comp.total_mentions}")
        print(f"   URL: {comp.url}")
        print(f"   Status: {comp.track_status}")
        print(f"   Message: {comp.track_message}")
        print()
    print(f"{'-'*60}\n")


if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print(f"# Competitor Extraction Test for appkodes.com")
    print(f"{'#'*60}\n")

    # Step 1: Create sample analytics data
    domain = create_sample_analytics_for_appkodes()

    if not domain:
        sys.exit(1)

    # Step 2: Run extraction
    test_extraction(domain)

    print(f"\n{'#'*60}")
    print(f"# Test Complete!")
    print(f"# Visit http://localhost:8080/competitors to see results")
    print(f"{'#'*60}\n")
