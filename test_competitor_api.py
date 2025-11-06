#!/usr/bin/env python
"""
Test the competitor process-single API endpoint
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001/api"
COMPETITOR_ID = 1

print("=" * 70)
print("Testing Competitor Process-Single API")
print("=" * 70)

# Step 1: Check competitor status before
print(f"\n1. Checking competitor {COMPETITOR_ID} BEFORE processing...")
try:
    response = requests.get(f"{BASE_URL}/competitors/{COMPETITOR_ID}/", timeout=5)
    if response.status_code == 200:
        competitor = response.json()
        print(f"   ✅ Competitor found: {competitor.get('name')}")
        print(f"   Status: {competitor.get('track_status')}")
        print(f"   Total Mentions: {competitor.get('total_mentions', 0)}")
        print(f"   Track Message: {competitor.get('track_message', 'N/A')}")
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"   ❌ Error: {str(e)}")
    exit(1)

# Step 2: Check existing competitor-prompt analytics
print(f"\n2. Checking existing competitor-prompt analytics...")
try:
    response = requests.get(
        f"{BASE_URL}/competitor-prompt-analytics/",
        params={"competitor_id": COMPETITOR_ID},
        timeout=5
    )
    if response.status_code == 200:
        analytics_before = response.json()
        print(f"   Found {len(analytics_before)} existing analytics")
        if analytics_before:
            print(f"   Sample: Status={analytics_before[0].get('track_status')}, "
                  f"Mentioned={analytics_before[0].get('is_mentioned')}")
    else:
        print(f"   ⚠️  Could not fetch analytics: {response.status_code}")
        analytics_before = []
except Exception as e:
    print(f"   ⚠️  Error: {str(e)}")
    analytics_before = []

# Step 3: Call the process-single API
print(f"\n3. Calling POST /api/competitors/process-single/ with competitor_id={COMPETITOR_ID}...")
try:
    response = requests.post(
        f"{BASE_URL}/competitors/process-single/",
        json={"competitor_id": COMPETITOR_ID},
        timeout=30
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ SUCCESS!")
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        task_id = data.get('task_id')
        print(f"\n   Task ID: {task_id}")
        print(f"   Message: {data.get('message')}")
        
        # Wait for processing
        print(f"\n4. Waiting 15 seconds for Celery task to complete...")
        time.sleep(15)
        
    elif response.status_code == 400:
        print(f"   ⚠️  Bad Request: {response.text}")
        exit(1)
    elif response.status_code == 404:
        print(f"   ❌ Not Found: {response.text}")
        exit(1)
    else:
        print(f"   ❌ Unexpected status: {response.status_code}")
        print(f"   Response: {response.text}")
        exit(1)
        
except requests.exceptions.Timeout:
    print(f"   ⚠️  Request timeout (this might be OK if processing takes long)")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 5: Check competitor status after
print(f"\n5. Checking competitor {COMPETITOR_ID} AFTER processing...")
try:
    response = requests.get(f"{BASE_URL}/competitors/{COMPETITOR_ID}/", timeout=5)
    if response.status_code == 200:
        competitor = response.json()
        print(f"   Status: {competitor.get('track_status')}")
        print(f"   Track Message: {competitor.get('track_message', 'N/A')}")
        print(f"   Total Mentions: {competitor.get('total_mentions', 0)}")
        print(f"   Visibility Score: {competitor.get('visibility_score', 0)}")
        print(f"   Average Position: {competitor.get('average_position', 0)}")
        print(f"   Sentiment Score: {competitor.get('sentiment_score', 0)}")
        print(f"   Share of Voice: {competitor.get('share_of_voice_percentage', 0)}%")
        
        if competitor.get('track_status') == 'COMP':
            print(f"   ✅ Competitor processing COMPLETED!")
        elif competitor.get('track_status') == 'FAIL':
            print(f"   ❌ Competitor processing FAILED!")
            print(f"   Error: {competitor.get('track_message')}")
        elif competitor.get('track_status') == 'PROC':
            print(f"   ⏳ Competitor still PROCESSING...")
        else:
            print(f"   ⚠️  Status: {competitor.get('track_status')}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Step 6: Check competitor-prompt analytics after
print(f"\n6. Checking competitor-prompt analytics AFTER processing...")
try:
    response = requests.get(
        f"{BASE_URL}/competitor-prompt-analytics/",
        params={"competitor_id": COMPETITOR_ID},
        timeout=5
    )
    if response.status_code == 200:
        analytics_after = response.json()
        print(f"   Found {len(analytics_after)} competitor-prompt analytics")
        
        if len(analytics_after) > len(analytics_before):
            print(f"   ✅ Created {len(analytics_after) - len(analytics_before)} NEW analytics!")
        elif len(analytics_after) == len(analytics_before) and len(analytics_after) > 0:
            print(f"   ℹ️  Same number of analytics (may have been updated)")
        elif len(analytics_after) == 0:
            print(f"   ⚠️  No analytics found - prompts may not have been linked")
        else:
            print(f"   ℹ️  Analytics count: {len(analytics_after)}")
        
        # Show details of first few
        if analytics_after:
            print(f"\n   First 3 analytics details:")
            for i, analytics in enumerate(analytics_after[:3], 1):
                print(f"   {i}. Prompt ID: {analytics.get('prompt')}")
                print(f"      Status: {analytics.get('track_status')}")
                print(f"      Mentioned: {analytics.get('is_mentioned')}")
                print(f"      Position: {analytics.get('position')}")
                print(f"      Mention Count: {analytics.get('mention_count')}")
                print(f"      Sentiment: {analytics.get('sentiment_category')} ({analytics.get('sentiment_score')})")
                print()
    else:
        print(f"   ❌ Failed: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Step 7: Get detailed analytics
print(f"\n7. Getting detailed competitor analytics...")
try:
    response = requests.get(f"{BASE_URL}/competitors/{COMPETITOR_ID}/analytics/", timeout=5)
    if response.status_code == 200:
        analytics = response.json()
        stats = analytics.get('statistics', {})
        print(f"   ✅ Detailed Analytics:")
        print(f"   Total Prompts Tested: {stats.get('total_prompts_tested', 0)}")
        print(f"   Times Mentioned: {stats.get('times_mentioned', 0)}")
        print(f"   Mention Rate: {stats.get('mention_rate', 0)}%")
        print(f"   Average Position: {stats.get('average_position', 0)}")
        print(f"   Average Sentiment: {stats.get('average_sentiment', 0)}")
        print(f"   Total Mention Count: {stats.get('total_mention_count', 0)}")
        
        recent_prompts = analytics.get('recent_prompts', [])
        if recent_prompts:
            print(f"\n   Recent Prompts ({len(recent_prompts)}):")
            for i, prompt in enumerate(recent_prompts[:3], 1):
                print(f"   {i}. {prompt.get('prompt_text', 'N/A')[:60]}...")
                print(f"      Mentioned: {prompt.get('is_mentioned')}, Position: {prompt.get('position')}")
    else:
        print(f"   ⚠️  Failed: {response.status_code}")
except Exception as e:
    print(f"   ⚠️  Error: {str(e)}")

print("\n" + "=" * 70)
print("Test Complete!")
print("=" * 70)

