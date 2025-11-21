#!/usr/bin/env python3
"""
Script to generate AI insights from existing competitor snapshots.
Usage: python3 generate_insights.py <domain_id>
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from competitors.models import Competitor, CompetitiveInsight, CompetitorMetricSnapshot
from domains.models import Domain
from analytics.models import ShareOfVoiceAnalytics
from prompts.models import PromptAnalytics
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
import hashlib
import json

# Add engine path for OpenAI client
engine_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'engine')
if engine_path not in sys.path:
    sys.path.insert(0, engine_path)

# Read OpenAI API key from engine/.env
from decouple import config as decouple_config
engine_env_path = os.path.join(engine_path, '.env')
if os.path.exists(engine_env_path):
    # Temporarily change directory to engine to read .env
    original_cwd = os.getcwd()
    os.chdir(engine_path)
    openai_api_key = decouple_config('OPENAI_API_KEY', default=None)
    os.chdir(original_cwd)
else:
    openai_api_key = None

# Import OpenAI client function
try:
    from core.analytics_helpers import get_openai_client
except:
    # Fallback: create OpenAI client directly if import fails
    def get_openai_client():
        if not openai_api_key:
            raise Exception("OpenAI API key not found in engine/.env file")
        from openai import OpenAI
        return OpenAI(api_key=openai_api_key, timeout=60)

def generate_snapshot_version(domain_id):
    """Generate a unique snapshot version based on latest snapshots"""
    latest_snapshot = CompetitorMetricSnapshot.objects.filter(
        domain_id=domain_id
    ).order_by('-timestamp').first()
    
    if latest_snapshot:
        # Use timestamp as version identifier
        timestamp_str = latest_snapshot.timestamp.isoformat()
        return hashlib.md5(timestamp_str.encode()).hexdigest()[:16]
    return None

def generate_insights_for_domain(domain_id):
    """Generate AI insights for a domain from existing data"""
    try:
        domain = Domain.objects.get(id=domain_id)
        print(f"Generating insights for domain: {domain.name} (ID: {domain_id})")
        
        # Check if insights already exist for current snapshot version
        snapshot_version = generate_snapshot_version(domain_id)
        if not snapshot_version:
            print("❌ No snapshots found. Please run competitor processor first.")
            return
        
        existing_insights = CompetitiveInsight.objects.filter(
            domain_id=domain_id,
            snapshot_version=snapshot_version
        )
        
        if existing_insights.exists():
            print(f"✅ Insights already exist for snapshot version: {snapshot_version}")
            print(f"   Found {existing_insights.count()} insights")
            return
        
        print(f"📊 Snapshot version: {snapshot_version}")
        print("📝 Gathering competitor data...")
        
        # Get competitors
        competitors = Competitor.objects.filter(domain_id=domain_id).order_by('-share_of_voice_percentage')
        
        # Get your brand's metrics
        your_prompts = PromptAnalytics.objects.filter(
            prompt__group__domain_id=domain_id,
            is_mention=True,
            track_status='COMP'
        )
        your_mentions = your_prompts.count()
        your_sov = ShareOfVoiceAnalytics.objects.filter(
            domain_id=domain_id,
            competitor__isnull=True
        ).order_by('-timestamp').first()
        your_sov_pct = float(your_sov.share_percentage) if your_sov else 0
        your_sentiment = float(your_prompts.aggregate(avg=Avg('sentiment_score'))['avg'] or 0) * 100
        
        # Build summary data
        competitor_summary = []
        for comp in competitors[:5]:  # Top 5
            competitor_summary.append({
                'name': comp.name,
                'share_of_voice': float(comp.share_of_voice_percentage or 0),
                'mentions': comp.total_mentions or 0,
                'visibility': float(comp.visibility_score or 0),
                'sentiment': float(comp.sentiment_score or 0) * 100,
                'position': float(comp.average_position or 0),
            })
        
        # Build prompt for ChatGPT
        prompt_text = f"""You are a competitive intelligence analyst providing ACTIONABLE strategic insights to help {domain.name} increase brand visibility in AI search results.

CURRENT PERFORMANCE:
Your Brand ({domain.name}):
- Share of Voice: {your_sov_pct:.1f}%
- Total Mentions: {your_mentions}
- Sentiment Score: {your_sentiment:.1f}%

Top Competitors:
"""
        for comp_data in competitor_summary:
            prompt_text += f"- {comp_data['name']}: SoV {comp_data['share_of_voice']:.1f}%, Mentions {comp_data['mentions']}, Visibility {comp_data['visibility']:.1f}, Sentiment {comp_data['sentiment']:.1f}%\n"

        prompt_text += """
Generate exactly 2 ACTIONABLE insights that help the brand take specific actions to improve visibility. Each insight MUST:
- Be specific and actionable (not generic advice)
- Include concrete numbers/percentages from the data
- Suggest a clear next step or strategy
- Focus on competitive gaps, opportunities, or threats

Required JSON format for each insight:
- title: Specific, action-oriented title (e.g., "Target 10 High-Traffic Queries Where Competitors Dominate", NOT "Improve Visibility")
- description: 2-3 sentences with: (1) Specific data point, (2) Why it matters, (3) Recommended action
- type: "success" (wins to leverage), "warning" (losing ground), "opportunity" (gaps to exploit), "risk" (competitive threats)
- impact: "high" (urgent, >20% gap), "medium" (important, 10-20% gap), "low" (<10% gap)
- category: "market_position", "sentiment", "visibility", "growth", "opportunity"

EXAMPLES OF GOOD INSIGHTS:
✅ "Capitalize on 15% Higher Sentiment vs Top Competitor" - "Your sentiment (75%) beats Competitor X (60%) by 15 points. Create comparison content highlighting superior customer satisfaction to win users comparing options. Focus on review aggregation and feature comparison pages."
✅ "Competitor Y Gaining 25% Momentum in Category Z" - "Competitor Y grew mentions 25% month-over-month in 'product category' queries. They're targeting long-tail keywords. Counter by optimizing for related queries and publishing category guides to reclaim share."

EXAMPLES OF BAD INSIGHTS:
❌ "Low Share of Voice" - Too generic, no action
❌ "Increase Engagement" - Vague, not specific
❌ "Competitive Threat Exists" - States obvious, no strategy

Return ONLY valid JSON array with 2 insights, no other text:
[
  {
    "title": "Specific Action-Oriented Title with Numbers",
    "description": "Specific data point. Why it matters for visibility. Clear recommended action to take.",
    "type": "opportunity",
    "impact": "high",
    "category": "visibility"
  },
  ...
]
"""
        
        print("🤖 Calling ChatGPT to generate insights...")
        
        try:
            openai_client = get_openai_client()
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a competitive intelligence analyst. Generate strategic insights in JSON format only."},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON (handle markdown code blocks if present)
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            insights_data = json.loads(response_text)

            if not isinstance(insights_data, list) or len(insights_data) != 2:
                print(f"⚠️  Warning: Expected 2 insights, got {len(insights_data) if isinstance(insights_data, list) else 'non-list'}")
            
            print(f"✅ Generated {len(insights_data)} insights")
            
            # Save insights
            saved_count = 0
            for insight_data in insights_data:
                insight = CompetitiveInsight.objects.create(
                    domain=domain,
                    title=insight_data.get('title', 'Untitled Insight'),
                    description=insight_data.get('description', ''),
                    insight_type=insight_data.get('type', 'opportunity'),
                    category=insight_data.get('category', 'market_position'),
                    impact=insight_data.get('impact', 'medium'),
                    snapshot_version=snapshot_version,
                    insight_data=insight_data,
                    model_name='gpt-4o-mini'
                )
                saved_count += 1
                print(f"   💾 Saved: {insight.title}")
            
            print(f"\n✅ Successfully generated and saved {saved_count} insights!")
            print(f"   Snapshot version: {snapshot_version}")
            
        except Exception as e:
            print(f"❌ Error generating insights: {str(e)}")
            import traceback
            traceback.print_exc()
            return
        
    except Domain.DoesNotExist:
        print(f"Error: Domain with ID {domain_id} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 generate_insights.py <domain_id>")
        print("Example: python3 generate_insights.py 4")
        sys.exit(1)
    
    domain_id = int(sys.argv[1])
    generate_insights_for_domain(domain_id)

