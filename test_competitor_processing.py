#!/usr/bin/env python
"""
Test script to verify competitor processing creates prompts and analytics
"""
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8001/api"

def test_competitor_processing():
    """Test that competitor processing creates prompts and analytics"""
    
    print("=" * 60)
    print("Testing Competitor Processing - Full Flow")
    print("=" * 60)
    
    competitor_id = 1
    
    # Step 1: Check competitor status before
    print(f"\n1. Checking competitor {competitor_id} status BEFORE processing...")
    try:
        response = requests.get(f"{BASE_URL}/competitors/{competitor_id}/", timeout=5)
        if response.status_code == 200:
            competitor = response.json()
            print(f"   Status: {competitor.get('track_status')}")
            print(f"   Total Mentions: {competitor.get('total_mentions', 0)}")
        else:
            print(f"   ❌ Failed to get competitor: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Step 2: Check competitor-prompt analytics before
    print(f"\n2. Checking competitor-prompt analytics BEFORE processing...")
    try:
        response = requests.get(
            f"{BASE_URL}/competitor-prompt-analytics/",
            params={"competitor_id": competitor_id},
            timeout=5
        )
        if response.status_code == 200:
            analytics_before = response.json()
            print(f"   Found {len(analytics_before)} competitor-prompt analytics")
        else:
            print(f"   ⚠️  Failed to get analytics: {response.status_code}")
            analytics_before = []
    except Exception as e:
        print(f"   ⚠️  Error: {str(e)}")
        analytics_before = []
    
    # Step 3: Trigger processing
    print(f"\n3. Triggering competitor processing...")
    try:
        response = requests.post(
            f"{BASE_URL}/competitors/process-single/",
            json={"competitor_id": competitor_id},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Processing started!")
            print(f"   Task ID: {data.get('task_id')}")
            print(f"   Message: {data.get('message')}")
            
            # Wait a bit for processing
            print(f"\n4. Waiting 10 seconds for processing to complete...")
            time.sleep(10)
            
        else:
            print(f"   ❌ Failed to start processing: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Step 5: Check competitor status after
    print(f"\n5. Checking competitor {competitor_id} status AFTER processing...")
    try:
        response = requests.get(f"{BASE_URL}/competitors/{competitor_id}/", timeout=5)
        if response.status_code == 200:
            competitor = response.json()
            print(f"   Status: {competitor.get('track_status')}")
            print(f"   Total Mentions: {competitor.get('total_mentions', 0)}")
            print(f"   Visibility Score: {competitor.get('visibility_score', 0)}")
            print(f"   Average Position: {competitor.get('average_position', 0)}")
            
            if competitor.get('track_status') == 'COMP':
                print(f"   ✅ Competitor processing completed!")
            elif competitor.get('track_status') == 'FAIL':
                print(f"   ❌ Competitor processing failed!")
                print(f"   Error: {competitor.get('track_message')}")
                return False
            else:
                print(f"   ⚠️  Competitor still processing (status: {competitor.get('track_status')})")
        else:
            print(f"   ❌ Failed to get competitor: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Step 6: Check competitor-prompt analytics after
    print(f"\n6. Checking competitor-prompt analytics AFTER processing...")
    try:
        response = requests.get(
            f"{BASE_URL}/competitor-prompt-analytics/",
            params={"competitor_id": competitor_id},
            timeout=5
        )
        if response.status_code == 200:
            analytics_after = response.json()
            print(f"   Found {len(analytics_after)} competitor-prompt analytics")
            
            if len(analytics_after) > len(analytics_before):
                print(f"   ✅ Created {len(analytics_after) - len(analytics_before)} new analytics!")
                
                # Show first few
                print(f"\n   First 3 analytics:")
                for i, analytics in enumerate(analytics_after[:3], 1):
                    print(f"   {i}. Prompt: {analytics.get('prompt_text', 'N/A')[:50]}...")
                    print(f"      Status: {analytics.get('track_status')}")
                    print(f"      Mentioned: {analytics.get('is_mentioned')}")
                    print(f"      Position: {analytics.get('position')}")
                    print(f"      Mentions: {analytics.get('mention_count')}")
            elif len(analytics_after) == 0:
                print(f"   ⚠️  No analytics found - prompts may not have been linked")
            else:
                print(f"   ⚠️  Same number of analytics ({len(analytics_after)})")
        else:
            print(f"   ❌ Failed to get analytics: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Step 7: Get detailed analytics
    print(f"\n7. Getting detailed competitor analytics...")
    try:
        response = requests.get(f"{BASE_URL}/competitors/{competitor_id}/analytics/", timeout=5)
        if response.status_code == 200:
            analytics = response.json()
            stats = analytics.get('statistics', {})
            print(f"   Total Prompts Tested: {stats.get('total_prompts_tested', 0)}")
            print(f"   Times Mentioned: {stats.get('times_mentioned', 0)}")
            print(f"   Mention Rate: {stats.get('mention_rate', 0)}%")
            print(f"   Average Position: {stats.get('average_position', 0)}")
            print(f"   Total Mention Count: {stats.get('total_mention_count', 0)}")
        else:
            print(f"   ⚠️  Failed to get detailed analytics: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_competitor_processing()
    sys.exit(0 if success else 1)

