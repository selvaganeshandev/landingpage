#!/usr/bin/env python
"""
Test script for competitor API endpoint
"""
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8001/api"

def test_competitor_endpoint():
    """Test the start_single_competitor_processing endpoint"""
    
    print("=" * 60)
    print("Testing Competitor API Endpoint")
    print("=" * 60)
    
    # Step 1: List existing competitors
    print("\n1. Listing existing competitors...")
    try:
        response = requests.get(f"{BASE_URL}/competitors/", timeout=5)
        if response.status_code == 200:
            competitors = response.json()
            print(f"   Found {len(competitors)} competitors")
            if competitors:
                for comp in competitors[:3]:
                    print(f"   - ID: {comp['id']}, Name: {comp['name']}, Status: {comp.get('track_status', 'N/A')}")
                test_id = competitors[0]['id']
            else:
                print("   ⚠️  No competitors found. Please create one first.")
                return False
        else:
            print(f"   ❌ Failed to list competitors: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection Error: Is the engine server running on port 8001?")
        print("   Run: python manage.py runserver 0.0.0.0:8001")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Step 2: Test the process-single endpoint
    print(f"\n2. Testing POST /api/competitors/process-single/ with competitor_id={test_id}...")
    try:
        response = requests.post(
            f"{BASE_URL}/competitors/process-single/",
            json={"competitor_id": test_id},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ SUCCESS!")
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Validate response structure
            required_fields = ['success', 'message', 'task_id', 'competitor_id']
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
                return False
            
            if data.get('success') == True:
                print(f"   ✅ Task ID: {data.get('task_id')}")
                print(f"   ✅ Competitor ID: {data.get('competitor_id')}")
                print(f"   ✅ Competitor Name: {data.get('competitor_name', 'N/A')}")
                return True
            else:
                print(f"   ❌ Success field is False: {data}")
                return False
                
        elif response.status_code == 400:
            data = response.json()
            print(f"   ⚠️  Bad Request: {data}")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return False
        elif response.status_code == 404:
            print(f"   ❌ Competitor not found (404)")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timeout")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_with_invalid_id():
    """Test with invalid competitor_id"""
    print(f"\n3. Testing with invalid competitor_id (should return 404)...")
    try:
        response = requests.post(
            f"{BASE_URL}/competitors/process-single/",
            json={"competitor_id": 99999},
            timeout=5
        )
        
        if response.status_code == 404:
            print("   ✅ Correctly returned 404 for invalid ID")
            return True
        else:
            print(f"   ⚠️  Expected 404, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_without_competitor_id():
    """Test without competitor_id (should return 400)"""
    print(f"\n4. Testing without competitor_id (should return 400)...")
    try:
        response = requests.post(
            f"{BASE_URL}/competitors/process-single/",
            json={},
            timeout=5
        )
        
        if response.status_code == 400:
            data = response.json()
            if 'competitor_id is required' in str(data.get('error', '')):
                print("   ✅ Correctly returned 400 with error message")
                return True
            else:
                print(f"   ⚠️  Got 400 but wrong error message: {data}")
                return False
        else:
            print(f"   ⚠️  Expected 400, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nTesting Competitor API Endpoint: start_single_competitor_processing")
    print("=" * 60)
    
    # Test 1: Valid request
    test1 = test_competitor_endpoint()
    
    # Test 2: Invalid ID
    test2 = test_with_invalid_id()
    
    # Test 3: Missing competitor_id
    test3 = test_without_competitor_id()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print(f"Valid Request Test: {'✅ PASSED' if test1 else '❌ FAILED'}")
    print(f"Invalid ID Test: {'✅ PASSED' if test2 else '❌ FAILED'}")
    print(f"Missing ID Test: {'✅ PASSED' if test3 else '❌ FAILED'}")
    
    if test1 and test2 and test3:
        print("\n🎉 All tests PASSED!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests FAILED")
        sys.exit(1)

