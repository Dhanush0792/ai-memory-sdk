"""LLM Feature Verification - Option A: Experimental Status"""

import requests

BASE_URL = "http://localhost:8001"
API_KEY = "dev-key-12345"
USER_ID = "test-user-llm"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "X-User-ID": USER_ID,
    "Content-Type": "application/json"
}

def test_llm_without_keys():
    """Verify LLM endpoints fail honestly when no API keys configured"""
    
    print("="*60)
    print("LLM FEATURE VERIFICATION - OPTION A (EXPERIMENTAL)")
    print("="*60 + "\n")
    
    print("Testing LLM endpoints WITHOUT API keys configured...")
    print("Expected: Clear error messages, no silent failures\n")
    
    # TEST 1: Chat endpoint
    print("TEST 1: POST /api/v1/chat")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            headers=HEADERS,
            json={"message": "Hello, test message", "auto_save": True}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 500:
            error_detail = response.json().get('detail', '')
            if 'LLM' in error_detail or 'API' in error_detail or 'key' in error_detail.lower():
                print("✅ PASS: Clear error about missing LLM configuration")
            else:
                print(f"⚠️ WARNING: Error message unclear: {error_detail}")
        else:
            print(f"❌ FAIL: Expected 500 error, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    print()
    
    # TEST 2: Extract endpoint
    print("TEST 2: POST /api/v1/memory/extract")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/memory/extract",
            headers=HEADERS,
            json={"message": "My name is Alice"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 500:
            error_detail = response.json().get('detail', '')
            if 'LLM' in error_detail or 'API' in error_detail or 'key' in error_detail.lower():
                print("✅ PASS: Clear error about missing LLM configuration")
            else:
                print(f"⚠️ WARNING: Error message unclear: {error_detail}")
        else:
            print(f"❌ FAIL: Expected 500 error, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    print()
    
    # TEST 3: Context endpoint (should work - no LLM required)
    print("TEST 3: POST /api/v1/memory/context")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/memory/context",
            headers=HEADERS,
            json={"query": "test", "max_tokens": 1000}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ PASS: Context endpoint works without LLM")
        else:
            print(f"❌ FAIL: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    print()
    print("="*60)
    print("LLM VERIFICATION COMPLETE")
    print("="*60)
    print("\nDECISION: Mark Chat and Extract as EXPERIMENTAL")
    print("REASON: No LLM API keys configured")
    print("STATUS: Endpoints exist and fail honestly")
    
    return True

if __name__ == "__main__":
    try:
        success = test_llm_without_keys()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
