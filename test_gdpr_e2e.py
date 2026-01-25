"""GDPR End-to-End Verification Test"""

import requests
import json

BASE_URL = "http://localhost:8001"
API_KEY = "dev-key-12345"

def test_gdpr_flow():
    """Test complete GDPR flow with two users"""
    
    print("="*60)
    print("GDPR END-TO-END VERIFICATION")
    print("="*60 + "\n")
    
    # Setup: Two users
    user_a_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "X-User-ID": "user-a-gdpr-test",
        "Content-Type": "application/json"
    }
    
    user_b_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "X-User-ID": "user-b-gdpr-test",
        "Content-Type": "application/json"
    }
    
    # Setup: Create memories for both users
    print("SETUP: Creating test data...")
    
    # User A: 2 memories
    r1 = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers=user_a_headers,
        json={"content": "User A fact 1", "type": "fact"}
    )
    print(f"  User A Memory 1: {r1.status_code}")
    
    r2 = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers=user_a_headers,
        json={"content": "User A fact 2", "type": "fact"}
    )
    print(f"  User A Memory 2: {r2.status_code}")
    
    # User B: 2 memories
    r3 = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers=user_b_headers,
        json={"content": "User B fact 1", "type": "fact"}
    )
    print(f"  User B Memory 1: {r3.status_code}")
    
    r4 = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers=user_b_headers,
        json={"content": "User B fact 2", "type": "fact"}
    )
    print(f"  User B Memory 2: {r4.status_code}\n")
    
    # TEST 1: EXPORT (User A)
    print("TEST 1: GDPR EXPORT (User A)")
    print("-" * 60)
    
    export_response = requests.get(
        f"{BASE_URL}/api/v1/gdpr/export",
        headers=user_a_headers
    )
    
    print(f"Status: {export_response.status_code}")
    export_data = export_response.json()
    
    print(f"User ID: {export_data['user_id']}")
    print(f"Total memories: {export_data['metadata']['total_count']}")
    
    # Verify only User A data
    memories = export_data['memories']
    user_ids = set(m['user_id'] for m in memories)
    
    if len(user_ids) == 1 and 'user-a-gdpr-test' in user_ids:
        print("✅ PASS: Only User A data returned")
    else:
        print(f"❌ FAIL: Data leakage detected - user_ids: {user_ids}")
        return False
    
    if export_data['metadata']['total_count'] == 2:
        print("✅ PASS: Correct count (2 memories)")
    else:
        print(f"❌ FAIL: Expected 2 memories, got {export_data['metadata']['total_count']}")
        return False
    
    print()
    
    # TEST 2: DELETE (User A)
    print("TEST 2: GDPR DELETE (User A)")
    print("-" * 60)
    
    delete_response = requests.delete(
        f"{BASE_URL}/api/v1/gdpr/delete",
        headers=user_a_headers
    )
    
    print(f"Status: {delete_response.status_code}")
    delete_data = delete_response.json()
    
    print(f"Deleted: {delete_data['deleted']}")
    print(f"User ID: {delete_data['user_id']}")
    print(f"Deleted count: {delete_data['deleted_count']}")
    print(f"Irreversible: {delete_data['irreversible']}")
    
    if delete_data['deleted'] and delete_data['deleted_count'] == 2:
        print("✅ PASS: User A data deleted")
    else:
        print(f"❌ FAIL: Expected 2 deletions, got {delete_data['deleted_count']}")
        return False
    
    print()
    
    # TEST 3: STATS AFTER DELETE (User A)
    print("TEST 3: STATS AFTER DELETE (User A)")
    print("-" * 60)
    
    stats_response = requests.get(
        f"{BASE_URL}/api/v1/memory/stats",
        headers=user_a_headers
    )
    
    print(f"Status: {stats_response.status_code}")
    stats_data = stats_response.json()
    
    print(f"Total: {stats_data['total']}")
    print(f"By type: {stats_data['by_type']}")
    
    if stats_data['total'] == 0:
        print("✅ PASS: User A has 0 memories after delete")
    else:
        print(f"❌ FAIL: Expected 0 memories, got {stats_data['total']}")
        return False
    
    print()
    
    # VERIFY: User B data untouched
    print("VERIFY: User B data untouched")
    print("-" * 60)
    
    user_b_stats = requests.get(
        f"{BASE_URL}/api/v1/memory/stats",
        headers=user_b_headers
    )
    
    user_b_data = user_b_stats.json()
    print(f"User B total: {user_b_data['total']}")
    
    if user_b_data['total'] == 2:
        print("✅ PASS: User B data untouched (2 memories remain)")
    else:
        print(f"❌ FAIL: User B should have 2 memories, got {user_b_data['total']}")
        return False
    
    print()
    
    # Cleanup User B
    print("CLEANUP: Deleting User B data...")
    requests.delete(f"{BASE_URL}/api/v1/gdpr/delete", headers=user_b_headers)
    print("Done\n")
    
    print("="*60)
    print("ALL GDPR TESTS PASSED ✅")
    print("="*60)
    return True

if __name__ == "__main__":
    try:
        success = test_gdpr_flow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
