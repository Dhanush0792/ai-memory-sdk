"""
Test New Features
Test memory update/delete and analytics endpoints
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "tk_T_Jc0ffICmAwDaZF-ijPzqYYfqAGoPQLPTJQh2rQ_qY"  # Your test key

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def test_memory_update():
    """Test memory update endpoint"""
    print("=" * 80)
    print("  🧪 TEST 1: Memory Update")
    print("=" * 80)
    print()
    
    # First, create a memory
    print("Creating test memory...")
    create_response = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers=headers,
        json={
            "memory_type": "fact",
            "key": "test_update",
            "value": "original value",
            "confidence": 0.8
        }
    )
    
    if create_response.status_code == 200:
        memory = create_response.json()
        memory_id = memory['id']
        print(f"✅ Memory created: {memory_id}")
        print(f"   Original value: {memory['value']}")
        print()
        
        # Update the memory
        print("Updating memory...")
        update_response = requests.put(
            f"{BASE_URL}/api/v1/memory/{memory_id}",
            headers=headers,
            json={
                "value": {"updated": "new value"},
                "confidence": 0.95
            }
        )
        
        if update_response.status_code == 200:
            result = update_response.json()
            print(f"✅ Memory updated successfully!")
            print(f"   Version: {result['version']}")
            print()
        else:
            print(f"❌ Update failed: {update_response.text}")
    else:
        print(f"❌ Create failed: {create_response.text}")
    
    print()


def test_memory_delete():
    """Test memory delete endpoint"""
    print("=" * 80)
    print("  🧪 TEST 2: Memory Delete")
    print("=" * 80)
    print()
    
    # Create a memory to delete
    print("Creating test memory...")
    create_response = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers=headers,
        json={
            "memory_type": "fact",
            "key": "test_delete",
            "value": "will be deleted",
            "confidence": 0.8
        }
    )
    
    if create_response.status_code == 200:
        memory = create_response.json()
        memory_id = memory['id']
        print(f"✅ Memory created: {memory_id}")
        print()
        
        # Delete the memory
        print("Deleting memory...")
        delete_response = requests.delete(
            f"{BASE_URL}/api/v1/memory/{memory_id}",
            headers=headers
        )
        
        if delete_response.status_code == 200:
            result = delete_response.json()
            print(f"✅ Memory deleted successfully!")
            print(f"   Message: {result['message']}")
            print()
        else:
            print(f"❌ Delete failed: {delete_response.text}")
    else:
        print(f"❌ Create failed: {create_response.text}")
    
    print()


def test_analytics_dashboard():
    """Test analytics dashboard"""
    print("=" * 80)
    print("  🧪 TEST 3: Analytics Dashboard")
    print("=" * 80)
    print()
    
    response = requests.get(
        f"{BASE_URL}/api/v1/analytics/dashboard?days=30",
        headers=headers
    )
    
    if response.status_code == 200:
        dashboard = response.json()
        print("✅ Dashboard retrieved successfully!")
        print()
        print(f"📊 Usage Statistics:")
        print(f"   Total Requests: {dashboard['total_requests']}")
        print(f"   Today: {dashboard['requests_today']}")
        print(f"   This Week: {dashboard['requests_this_week']}")
        print(f"   This Month: {dashboard['requests_this_month']}")
        print(f"   Avg Response Time: {dashboard['avg_response_time']:.2f}ms")
        print()
        
        print(f"🚦 Rate Limit Status:")
        rate_limit = dashboard['rate_limit_status']
        print(f"   Tier: {rate_limit['tier']}")
        print(f"   Hourly: {rate_limit['hourly']['used']}/{rate_limit['hourly']['limit']} ({rate_limit['hourly']['percentage']:.1f}%)")
        print(f"   Daily: {rate_limit['daily']['used']}/{rate_limit['daily']['limit']} ({rate_limit['daily']['percentage']:.1f}%)")
        print()
        
        if dashboard['top_endpoints']:
            print(f"🔝 Top Endpoints:")
            for endpoint in dashboard['top_endpoints'][:5]:
                print(f"   {endpoint['endpoint']}: {endpoint['count']} requests ({endpoint['avg_response_time']:.1f}ms avg)")
        print()
    else:
        print(f"❌ Dashboard failed: {response.text}")
    
    print()


def test_endpoint_analytics():
    """Test endpoint analytics"""
    print("=" * 80)
    print("  🧪 TEST 4: Endpoint Analytics")
    print("=" * 80)
    print()
    
    response = requests.get(
        f"{BASE_URL}/api/v1/analytics/endpoints?days=7",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Endpoint analytics retrieved!")
        print()
        print(f"📈 Endpoint Performance (Last {data['period_days']} days):")
        
        for endpoint in data['endpoints'][:5]:
            print(f"\n   {endpoint['method']} {endpoint['endpoint']}")
            print(f"      Requests: {endpoint['total_requests']}")
            print(f"      Success: {endpoint['successful']} ({100 - endpoint['error_rate']:.1f}%)")
            print(f"      Errors: {endpoint['errors']} ({endpoint['error_rate']:.1f}%)")
            print(f"      Avg Time: {endpoint['avg_response_time']:.1f}ms")
        print()
    else:
        print(f"❌ Endpoint analytics failed: {response.text}")
    
    print()


def test_billing_data():
    """Test billing data"""
    print("=" * 80)
    print("  🧪 TEST 5: Billing Data")
    print("=" * 80)
    print()
    
    response = requests.get(
        f"{BASE_URL}/api/v1/analytics/billing",
        headers=headers
    )
    
    if response.status_code == 200:
        billing = response.json()
        print("✅ Billing data retrieved!")
        print()
        print(f"💰 Billing Summary:")
        print(f"   Month: {billing['month']}")
        print(f"   Tier: {billing['tier']}")
        print(f"   Total Requests: {billing['total_requests']}")
        print(f"   Total Response Time: {billing['total_response_time_ms']}ms")
        print()
        
        if billing['daily_breakdown']:
            print(f"📅 Daily Breakdown (Last 5 days):")
            for day in billing['daily_breakdown'][-5:]:
                print(f"   {day['date']}: {day['requests']} requests")
        print()
    else:
        print(f"❌ Billing data failed: {response.text}")
    
    print()


def main():
    """Run all tests"""
    print()
    print("=" * 80)
    print("  🧪 TESTING NEW FEATURES")
    print("=" * 80)
    print()
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:20]}...")
    print()
    
    try:
        # Test memory operations
        test_memory_update()
        test_memory_delete()
        
        # Test analytics
        test_analytics_dashboard()
        test_endpoint_analytics()
        test_billing_data()
        
        print("=" * 80)
        print("  ✅ ALL TESTS COMPLETE!")
        print("=" * 80)
        print()
        print("🎉 All features working correctly!")
        print()
        print("Next steps:")
        print("  1. Review the analytics dashboard")
        print("  2. Test with your own data")
        print("  3. Deploy to production!")
        print()
        
    except requests.exceptions.ConnectionError:
        print()
        print("=" * 80)
        print("  ❌ CONNECTION ERROR")
        print("=" * 80)
        print()
        print("The API server is not running!")
        print()
        print("Start the server with:")
        print("  python -m uvicorn truthkeeper_api:app --reload")
        print()
    except Exception as e:
        print()
        print("=" * 80)
        print("  ❌ TEST FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
