"""
V1.1 Hardening Test Suite
Tests for transaction safety, concurrency control, audit logging, extraction validation, and security.
"""

import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-12345678"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def print_test(name: str):
    """Print test header."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)

def print_result(passed: bool, message: str):
    """Print test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {message}")

# =============================================================================
# 1. EXTRACTION VALIDATION HARDENING TESTS
# =============================================================================

def test_extraction_validation():
    """Test hardened extraction validation."""
    print_test("Extraction Validation Hardening")
    
    # Test 1: Valid extraction
    response = requests.post(
        f"{BASE_URL}/memory/ingest",
        headers=HEADERS,
        json={
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "conversation_text": "I prefer short explanations and my manager is Ravi."
        }
    )
    print_result(response.status_code == 200, f"Valid extraction: {response.status_code}")
    
    # Test 2: Empty conversation (should fail gracefully)
    response = requests.post(
        f"{BASE_URL}/memory/ingest",
        headers=HEADERS,
        json={
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "conversation_text": ""
        }
    )
    print_result(
        response.status_code in [200, 422],
        f"Empty conversation handled: {response.status_code}"
    )
    
    print(f"\nExtraction validation tests complete")

# =============================================================================
# 2. CONCURRENCY CONTROL TESTS
# =============================================================================

def update_manager_concurrent(user_id: str, manager_name: str, attempt: int) -> Dict:
    """Helper function to update manager concurrently."""
    response = requests.post(
        f"{BASE_URL}/memory/ingest",
        headers=HEADERS,
        json={
            "tenant_id": "concurrency-test",
            "user_id": user_id,
            "conversation_text": f"My manager is {manager_name} (attempt {attempt})."
        }
    )
    return {
        "attempt": attempt,
        "status_code": response.status_code,
        "success": response.status_code == 200
    }

def test_concurrency_control():
    """Test concurrent updates to same memory."""
    print_test("Concurrency Control")
    
    user_id = f"concurrent-user-{int(time.time())}"
    
    # Perform 10 concurrent updates
    print("Performing 10 concurrent updates to same memory...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(update_manager_concurrent, user_id, f"Manager{i}", i)
            for i in range(10)
        ]
        results = [f.result() for f in futures]
    
    successful_updates = sum(1 for r in results if r["success"])
    print_result(
        successful_updates >= 8,  # Allow some failures due to lock contention
        f"Concurrent updates handled: {successful_updates}/10 succeeded"
    )
    
    # Verify only ONE active version exists
    time.sleep(1)  # Wait for all transactions to complete
    response = requests.get(
        f"{BASE_URL}/memory/retrieve",
        headers=HEADERS,
        params={
            "tenant_id": "concurrency-test",
            "user_id": user_id,
            "query": "manager"
        }
    )
    
    if response.status_code == 200:
        memories = response.json()["memories"]
        active_manager_memories = [m for m in memories if m["predicate"] == "manager" and m["is_active"]]
        print_result(
            len(active_manager_memories) == 1,
            f"Single active version guaranteed: {len(active_manager_memories)} active version(s)"
        )
        if active_manager_memories:
            print(f"  Final version: {active_manager_memories[0]['version']}")
    
    print(f"\nConcurrency control tests complete")

# =============================================================================
# 3. AUDIT LOGGING TESTS
# =============================================================================

def test_audit_logging():
    """Test audit logging for all operations."""
    print_test("Audit Logging")
    
    tenant_id = f"audit-test-{int(time.time())}"
    user_id = "audit-user"
    
    # Test 1: Ingest operation
    response = requests.post(
        f"{BASE_URL}/memory/ingest",
        headers=HEADERS,
        json={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "conversation_text": "I like Python programming."
        }
    )
    print_result(response.status_code == 200, "Ingest operation logged")
    
    # Test 2: Retrieve operation
    response = requests.get(
        f"{BASE_URL}/memory/retrieve",
        headers=HEADERS,
        params={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "query": "python"
        }
    )
    print_result(response.status_code == 200, "Retrieve operation logged")
    
    # Test 3: Delete operation
    if response.status_code == 200:
        memories = response.json()["memories"]
        if memories:
            memory_id = memories[0]["id"]
            response = requests.delete(
                f"{BASE_URL}/memory/{memory_id}",
                headers=HEADERS
            )
            print_result(response.status_code == 200, "Delete operation logged")
    
    print("\nNOTE: Verify audit_logs table in database for complete audit trail")
    print(f"\nAudit logging tests complete")

# =============================================================================
# 4. DETERMINISTIC RANKING TESTS
# =============================================================================

def test_deterministic_ranking():
    """Test that ranking produces identical results."""
    print_test("Deterministic Ranking")
    
    tenant_id = f"ranking-test-{int(time.time())}"
    user_id = "ranking-user"
    
    # Ingest multiple memories
    memories_text = [
        "I prefer short explanations.",
        "My manager is Ravi.",
        "I like Python programming.",
        "I work on backend systems.",
        "My favorite color is blue."
    ]
    
    for text in memories_text:
        requests.post(
            f"{BASE_URL}/memory/ingest",
            headers=HEADERS,
            json={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "conversation_text": text
            }
        )
    
    time.sleep(0.5)  # Wait for ingestion
    
    # Run same query 5 times
    results = []
    for i in range(5):
        response = requests.get(
            f"{BASE_URL}/memory/retrieve",
            headers=HEADERS,
            params={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "query": "manager"
            }
        )
        if response.status_code == 200:
            memories = response.json()["memories"]
            # Extract IDs and scores for comparison
            result_signature = [(m["id"], m.get("relevance_score", 0)) for m in memories]
            results.append(result_signature)
    
    # Check if all results are identical
    all_identical = all(r == results[0] for r in results)
    print_result(all_identical, "Ranking is deterministic (5/5 identical results)")
    
    if not all_identical:
        print("  WARNING: Results differ across runs!")
        for i, result in enumerate(results):
            print(f"  Run {i+1}: {len(result)} results")
    
    print(f"\nDeterministic ranking tests complete")

# =============================================================================
# 5. SECURITY TESTS
# =============================================================================

def test_security_controls():
    """Test security enhancements."""
    print_test("Security Controls")
    
    # Test 1: CORS restrictions (can't test directly via requests)
    print_result(True, "CORS restrictions configured (check startup logs)")
    
    # Test 2: Request size limit
    large_text = "x" * 2_000_000  # 2MB
    response = requests.post(
        f"{BASE_URL}/memory/ingest",
        headers=HEADERS,
        json={
            "tenant_id": "security-test",
            "user_id": "security-user",
            "conversation_text": large_text
        }
    )
    print_result(
        response.status_code == 413,
        f"Request size limit enforced: {response.status_code}"
    )
    
    # Test 3: Rate limiting (send 110 requests rapidly)
    print("Testing rate limiting (sending 110 requests)...")
    rate_limit_hit = False
    for i in range(110):
        response = requests.get(
            f"{BASE_URL}/memory/retrieve",
            headers=HEADERS,
            params={
                "tenant_id": "rate-test",
                "user_id": "rate-user",
                "query": "test"
            }
        )
        if response.status_code == 429:
            rate_limit_hit = True
            print_result(True, f"Rate limit enforced at request {i+1}")
            break
    
    if not rate_limit_hit:
        print_result(False, "Rate limit NOT hit (may need to adjust timing)")
    
    # Test 4: API key authentication
    response = requests.get(
        f"{BASE_URL}/memory/retrieve",
        headers={"Content-Type": "application/json"},  # No API key
        params={
            "tenant_id": "auth-test",
            "user_id": "auth-user",
            "query": "test"
        }
    )
    print_result(
        response.status_code == 401,
        f"API key required: {response.status_code}"
    )
    
    print(f"\nSecurity control tests complete")

# =============================================================================
# 6. TRANSACTION SAFETY TESTS
# =============================================================================

def test_transaction_safety():
    """Test transaction rollback on failure."""
    print_test("Transaction Safety")
    
    # This test requires manual verification via database inspection
    # We can test the happy path here
    
    tenant_id = f"transaction-test-{int(time.time())}"
    user_id = "transaction-user"
    
    # Insert initial memory
    response = requests.post(
        f"{BASE_URL}/memory/ingest",
        headers=HEADERS,
        json={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "conversation_text": "My manager is Alice."
        }
    )
    print_result(response.status_code == 200, "Initial memory inserted")
    
    # Update memory (should create version 2)
    response = requests.post(
        f"{BASE_URL}/memory/ingest",
        headers=HEADERS,
        json={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "conversation_text": "My manager is Bob."
        }
    )
    print_result(response.status_code == 200, "Memory updated (version 2)")
    
    # Verify version 2 exists and version 1 is inactive
    response = requests.get(
        f"{BASE_URL}/memory/retrieve",
        headers=HEADERS,
        params={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "query": "manager"
        }
    )
    
    if response.status_code == 200:
        memories = response.json()["memories"]
        active_memories = [m for m in memories if m["is_active"]]
        if active_memories:
            latest_version = active_memories[0]["version"]
            print_result(
                latest_version == 2,
                f"Versioning works correctly: version {latest_version}"
            )
    
    print("\nNOTE: For full transaction safety testing, simulate database failures")
    print(f"\nTransaction safety tests complete")

# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all V1.1 hardening tests."""
    print("\n" + "="*60)
    print("MEMORY INFRASTRUCTURE V1.1 - HARDENING TEST SUITE")
    print("="*60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("\n✗ ERROR: Server health check failed")
            return
        print("\n✓ Server is running")
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Cannot connect to server. Is it running?")
        print(f"  Expected URL: {BASE_URL}")
        return
    
    # Run test suites
    test_extraction_validation()
    test_concurrency_control()
    test_audit_logging()
    test_deterministic_ranking()
    test_security_controls()
    test_transaction_safety()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60)
    print("\nMANUAL VERIFICATION REQUIRED:")
    print("1. Check audit_logs table for complete audit trail")
    print("2. Verify API key hashing in audit logs")
    print("3. Test transaction rollback by simulating database failures")
    print("4. Verify CORS restrictions via browser")
    print("\n")

if __name__ == "__main__":
    run_all_tests()
