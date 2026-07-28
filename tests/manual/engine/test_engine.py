#!/usr/bin/env python
"""
Test script for the LLM Monitor Engine
"""
import os
import sys
import django
import requests
import time
from pathlib import Path

# Add the engine source directory to Python path
ENGINE_ROOT = Path(__file__).resolve().parents[3] / 'engine'
sys.path.insert(0, str(ENGINE_ROOT))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from shared_models.models import Domain, Organisation


def test_engine():
    """
    Test the engine functionality
    """
    print("Testing LLM Monitor Engine...")
    
    # Test 1: Check if we can connect to the database
    print("\n1. Testing database connection...")
    try:
        org_count = Organisation.objects.count()
        domain_count = Domain.objects.count()
        print(f"   ✓ Database connected successfully")
        print(f"   ✓ Found {org_count} organisations and {domain_count} domains")
    except Exception as e:
        print(f"   ✗ Database connection failed: {str(e)}")
        return False
    
    # Test 2: Test API endpoints (if server is running)
    print("\n2. Testing API endpoints...")
    try:
        response = requests.get('http://localhost:8001/api/status/', timeout=5)
        if response.status_code == 200:
            print("   ✓ API endpoints are accessible")
            data = response.json()
            print(f"   ✓ Processing status: {data}")
        else:
            print(f"   ⚠ API returned status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ⚠ API server is not running (this is expected if you haven't started it)")
    except Exception as e:
        print(f"   ⚠ API test failed: {str(e)}")
    
    # Test 3: Test domain processor initialization
    print("\n3. Testing domain processor initialization...")
    try:
        from core.domain_processor import DomainProcessor
        processor = DomainProcessor()
        status = processor.get_processing_status()
        print(f"   ✓ Domain processor initialized successfully")
        print(f"   ✓ Status: {status}")
    except Exception as e:
        print(f"   ✗ Domain processor initialization failed: {str(e)}")
        return False
    
    # Test 4: Test ChatGPT client
    print("\n4. Testing ChatGPT client...")
    try:
        from core.chatgpt_client import ChatGPTClient
        client = ChatGPTClient()
        print("   ✓ ChatGPT client initialized successfully")
    except Exception as e:
        print(f"   ✗ ChatGPT client initialization failed: {str(e)}")
        return False
    
    print("\n✅ All tests passed! The engine is ready to use.")
    return True


def create_test_data():
    """
    Create test data for the engine
    """
    print("\nCreating test data...")
    
    try:
        # Create test organisation
        org, created = Organisation.objects.get_or_create(
            name="Test Organisation",
            defaults={
                'name': 'Test Organisation',
                'industry': 'Technology',
                'team_count': 1
            }
        )
        if created:
            print(f"   ✓ Created organisation: {org.name}")
        else:
            print(f"   ✓ Found existing organisation: {org.name}")
        
        # Create test domain
        domain, created = Domain.objects.get_or_create(
            name="test.com",
            defaults={
                'name': 'test.com',
                'url': 'https://test.com',
                'organisation': org
            }
        )
        if created:
            print(f"   ✓ Created domain: {domain.name}")
        else:
            print(f"   ✓ Found existing domain: {domain.name}")
        
        return domain
        
    except Exception as e:
        print(f"   ✗ Failed to create test data: {str(e)}")
        return None


if __name__ == '__main__':
    print("LLM Monitor Engine Test Suite")
    print("=" * 40)
    
    # Run tests
    success = test_engine()
    
    if success:
        # Create test data
        test_domain = create_test_data()
        
        if test_domain:
            print(f"\n🎉 Engine is ready! You can now:")
            print(f"   1. Start the engine: python start_engine.py")
            print(f"   2. Start the API server: python manage.py runserver 8001")
            print(f"   3. Test with domain ID: {test_domain.id}")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
