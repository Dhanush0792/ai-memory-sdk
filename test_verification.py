"""
Test script for verifying Memory Infrastructure V1.
Runs all test scenarios from the implementation plan.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-12345678"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Test data
TENANT_ID = "test-tenant"
USER_ID = "user-123"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"  {details}")


def test_health_check() -> bool:
    """Test 1: Health check endpoint."""
    print_section("Test 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        
        passed = (
            response.status_code == 200 and
            data.get("status") == "healthy" and
            data.get("database_connected") is True
        )
        
        print_test("Health endpoint accessible", passed, json.dumps(data, indent=2))
        return passed
    except Exception as e:
        print_test("Health endpoint accessible", False, str(e))
        return False


def test_authentication() -> bool:
    """Test 2: Authentication required."""
    print_section("Test 2: Authentication")
    
    try:
        # Request without API key
        response = requests.get(
            f"{BASE_URL}/memory/retrieve",
            params={"tenant_id": TENANT_ID, "user_id": USER_ID, "query": "test"}
        )
        
        passed = response.status_code == 401
        print_test("Unauthorized without API key", passed, f"Status: {response.status_code}")
        return passed
    except Exception as e:
        print_test("Unauthorized without API key", False, str(e))
        return False


def test_ingest_initial() -> Dict[str, Any]:
    """Test 3: Ingest initial conversation."""
    print_section("Test 3: Ingest Initial Conversation")
    
    try:
        payload = {
            "tenant_id": TENANT_ID,
            "user_id": USER_ID,
            "conversation_text": "I prefer short explanations and my manager is Ravi."
        }
        
        response = requests.post(
            f"{BASE_URL}/memory/ingest",
            headers=HEADERS,
            json=payload
        )
        
        data = response.json()
        
        passed = (
            response.status_code == 200 and
            data.get("status") == "success" and
            len(data.get("memories", [])) >= 2
        )
        
        print_test("Ingest conversation", passed, f"Extracted {len(data.get('memories', []))} memories")
        
        if passed:
            for memory in data["memories"]:
                print(f"  - {memory['subject']} {memory['predicate']} {memory['object']} (v{memory['version']})")
        
        return data
    except Exception as e:
        print_test("Ingest conversation", False, str(e))
        return {}


def test_retrieve(query: str) -> Dict[str, Any]:
    """Test 4: Retrieve memories."""
    print_section(f"Test 4: Retrieve - '{query}'")
    
    try:
        response = requests.get(
            f"{BASE_URL}/memory/retrieve",
            headers=HEADERS,
            params={
                "tenant_id": TENANT_ID,
                "user_id": USER_ID,
                "query": query,
                "limit": 10
            }
        )
        
        data = response.json()
        
        passed = (
            response.status_code == 200 and
            "memories" in data
        )
        
        print_test("Retrieve memories", passed, f"Found {data.get('total', 0)} results")
        
        if passed and data.get("memories"):
            for memory in data["memories"][:3]:  # Show top 3
                print(f"  - {memory['subject']} {memory['predicate']} {memory['object']}")
                print(f"    Score: {memory['relevance_score']:.2f}, Confidence: {memory['confidence']}")
        
        return data
    except Exception as e:
        print_test("Retrieve memories", False, str(e))
        return {}


def test_update_manager() -> Dict[str, Any]:
    """Test 5: Update manager (versioning test)."""
    print_section("Test 5: Update Manager (Versioning)")
    
    try:
        payload = {
            "tenant_id": TENANT_ID,
            "user_id": USER_ID,
            "conversation_text": "My manager changed to Arjun."
        }
        
        response = requests.post(
            f"{BASE_URL}/memory/ingest",
            headers=HEADERS,
            json=payload
        )
        
        data = response.json()
        
        passed = (
            response.status_code == 200 and
            data.get("status") == "success"
        )
        
        print_test("Update manager", passed)
        
        if passed:
            for memory in data.get("memories", []):
                print(f"  - {memory['subject']} {memory['predicate']} {memory['object']} (v{memory['version']})")
        
        return data
    except Exception as e:
        print_test("Update manager", False, str(e))
        return {}


def test_versioning_check():
    """Test 6: Verify versioning worked correctly."""
    print_section("Test 6: Verify Versioning")
    
    # Retrieve manager info
    result = test_retrieve("manager")
    
    if result.get("memories"):
        # Check that only active version is returned
        manager_memories = [m for m in result["memories"] if "manager" in m["predicate"].lower() or "manager" in m["subject"].lower()]
        
        if manager_memories:
            latest = manager_memories[0]
            print_test(
                "Latest manager version active",
                latest["object"] == "Arjun" and latest["is_active"],
                f"Manager: {latest['object']}, Version: {latest['version']}"
            )


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "=" * 60)
    print("  MEMORY INFRASTRUCTURE V1 - VERIFICATION SUITE")
    print("=" * 60)
    print(f"  Base URL: {BASE_URL}")
    print(f"  Tenant: {TENANT_ID}")
    print(f"  User: {USER_ID}")
    print("=" * 60)
    
    # Wait for services to be ready
    print("\nWaiting for services to start...")
    time.sleep(5)
    
    # Run tests
    test_health_check()
    test_authentication()
    test_ingest_initial()
    test_retrieve("Who is my manager?")
    test_update_manager()
    test_versioning_check()
    
    print("\n" + "=" * 60)
    print("  VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
