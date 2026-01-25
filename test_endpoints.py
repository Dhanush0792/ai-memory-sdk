"""Endpoint verification test - prove all endpoints work"""

import requests
import json

BASE_URL = "http://localhost:8001"
HEADERS = {
    "Authorization": "Bearer dev-key-12345",
    "X-User-ID": "test-user",
    "Content-Type": "application/json"
}

def test_health():
    """Test health endpoint"""
    print("Testing GET /health...")
    r = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 200
    print("  ✅ PASS\n")

def test_add_memory():
    """Test adding memory"""
    print("Testing POST /api/v1/memory...")
    data = {"content": "Test fact", "type": "fact"}
    r = requests.post(f"{BASE_URL}/api/v1/memory", headers=HEADERS, json=data)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 200
    memory_id = r.json().get("id")
    print(f"  ✅ PASS - Created memory {memory_id}\n")
    return memory_id

def test_get_memories():
    """Test retrieving memories"""
    print("Testing GET /api/v1/memory...")
    r = requests.get(f"{BASE_URL}/api/v1/memory", headers=HEADERS)
    print(f"  Status: {r.status_code}")
    memories = r.json()
    print(f"  Response: {len(memories)} memories")
    assert r.status_code == 200
    print("  ✅ PASS\n")
    return memories

def test_stats():
    """Test memory stats"""
    print("Testing GET /api/v1/memory/stats...")
    r = requests.get(f"{BASE_URL}/api/v1/memory/stats", headers=HEADERS)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 200
    print("  ✅ PASS\n")

def test_no_auth():
    """Test that endpoints reject requests without auth"""
    print("Testing auth enforcement (no Authorization header)...")
    r = requests.post(f"{BASE_URL}/api/v1/memory", json={"content": "Test", "type": "fact"})
    print(f"  Status: {r.status_code}")
    assert r.status_code in (401, 403, 422), "Should reject unauthenticated requests"
    print("  ✅ PASS - Auth required\n")

def test_no_user_id():
    """Test that endpoints reject requests without X-User-ID"""
    print("Testing X-User-ID enforcement...")
    headers = {"Authorization": "Bearer test-key", "Content-Type": "application/json"}
    r = requests.post(f"{BASE_URL}/api/v1/memory", headers=headers, json={"content": "Test", "type": "fact"})
    print(f"  Status: {r.status_code}")
    assert r.status_code in (401, 403, 422), "Should reject requests without X-User-ID"
    print("  ✅ PASS - X-User-ID required\n")

def test_delete_memory(memory_id):
    """Test deleting memory"""
    print(f"Testing DELETE /api/v1/memory/{memory_id}...")
    r = requests.delete(f"{BASE_URL}/api/v1/memory/{memory_id}", headers=HEADERS)
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    assert r.status_code == 200
    print("  ✅ PASS\n")

if __name__ == "__main__":
    print("="*60)
    print("ENDPOINT REALITY VERIFICATION")
    print("="*60 + "\n")
    
    try:
        test_health()
        test_no_auth()
        test_no_user_id()
        memory_id = test_add_memory()
        test_get_memories()
        test_stats()
        test_delete_memory(memory_id)
        
        print("="*60)
        print("ALL TESTS PASSED ✅")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
