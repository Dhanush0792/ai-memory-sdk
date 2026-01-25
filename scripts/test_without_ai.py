"""
Test the Memory SDK without using AI APIs (no charges).
This script tests the core memory storage and retrieval functionality.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("\n1️⃣ Testing Health Endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    print("   ✅ PASS")

def test_manual_memory_storage():
    """Test manual memory storage (no AI needed)."""
    print("\n2️⃣ Testing Manual Memory Storage...")
    
    # Note: The API doesn't have a direct endpoint to add memories without extraction
    # But we can test the database directly using the SDK
    print("   ℹ️  Manual memory addition requires direct SDK usage")
    print("   ℹ️  See example below for programmatic usage")
    print("   ✅ SKIP (requires code modification)")

def test_retrieve_memories():
    """Test retrieving memories."""
    print("\n3️⃣ Testing Memory Retrieval...")
    user_id = "test_user_no_ai"
    response = requests.get(f"{BASE_URL}/api/v1/memory/{user_id}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    print("   ✅ PASS")

def test_memory_stats():
    """Test memory statistics."""
    print("\n4️⃣ Testing Memory Statistics...")
    user_id = "test_user_no_ai"
    response = requests.get(f"{BASE_URL}/api/v1/memory/{user_id}/stats")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    print("   ✅ PASS")

def main():
    print("=" * 60)
    print("🧪 AI Memory SDK - No-AI Test Suite")
    print("=" * 60)
    print("\nℹ️  These tests don't require API keys and won't incur charges")
    
    try:
        test_health()
        test_retrieve_memories()
        test_memory_stats()
        
        print("\n" + "=" * 60)
        print("✅ All no-AI tests passed!")
        print("=" * 60)
        
        print("\n📝 To add memories without AI:")
        print("   Use the SDK directly in Python:")
        print("""
   from app.memory import MemorySDK
   
   sdk = MemorySDK()
   sdk.add_memory(
       user_id="alice",
       memory_type="fact",
       key="name",
       value="Alice"
   )
        """)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
