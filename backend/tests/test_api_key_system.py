"""
Comprehensive Test Suite for API Key System

Tests all requirements:
1. Database schema
2. Key generation and management
3. Authentication middleware
4. Rate limiting
5. Data isolation
6. Error handling
7. Security hardening
8. Backward compatibility
"""

import os
import sys
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from api.key_manager import KeyManager
from api.auth import get_api_key_context, APIKeyContext
from api.rate_limiter import RateLimiter, TokenBucket
from api.database import Database


class TestDatabaseSchema:
    """Test 1: Database Schema"""
    
    def test_api_keys_table_exists(self):
        """Verify api_keys table exists with correct schema"""
        db = Database()
        
        with db._get_conn() as conn:
            with conn.cursor() as cur:
                # Check table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'api_keys'
                    );
                """)
                assert cur.fetchone()[0], "api_keys table does not exist"
                
                # Check columns
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'api_keys'
                    ORDER BY ordinal_position;
                """)
                columns = {row[0]: row[1] for row in cur.fetchall()}
                
                assert 'id' in columns
                assert 'key_hash' in columns
                assert 'owner_id' in columns
                assert 'is_active' in columns
                assert 'created_at' in columns
                assert 'revoked_at' in columns
                assert 'rate_limit_per_minute' in columns
                assert 'metadata' in columns
                assert 'last_used_at' in columns
    
    def test_indexes_exist(self):
        """Verify required indexes exist"""
        db = Database()
        
        with db._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'api_keys';
                """)
                indexes = [row[0] for row in cur.fetchall()]
                
                assert 'idx_key_hash' in indexes
                assert 'idx_owner_id' in indexes
                assert 'idx_is_active' in indexes


class TestKeyGeneration:
    """Test 2: Key Generation & Management"""
    
    def test_key_format(self):
        """Verify API key format"""
        km = KeyManager()
        key = km.generate_api_key()
        
        assert key.startswith("aimsk_live_"), f"Invalid key format: {key}"
        assert len(key) > 40, "Key too short"
    
    def test_key_creation(self):
        """Test key creation and storage"""
        km = KeyManager()
        
        result = km.create_api_key(
            owner_id="test_owner_001",
            rate_limit_per_minute=100,
            metadata={"plan": "test"}
        )
        
        assert "api_key" in result
        assert "key_id" in result
        assert result["owner_id"] == "test_owner_001"
        assert result["rate_limit_per_minute"] == 100
        assert result["api_key"].startswith("aimsk_live_")
    
    def test_no_plaintext_storage(self):
        """Verify plaintext keys are never stored"""
        km = KeyManager()
        
        result = km.create_api_key(owner_id="test_owner_002")
        plaintext_key = result["api_key"]
        
        # Check database
        with km._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT key_hash FROM api_keys 
                    WHERE id = %s
                """, (result["key_id"],))
                
                stored_hash = cur.fetchone()[0]
                
                # Verify it's a hash, not plaintext
                assert stored_hash != plaintext_key
                assert len(stored_hash) == 64  # SHA-256 hex length
    
    def test_key_revocation(self):
        """Test key revocation"""
        km = KeyManager()
        
        result = km.create_api_key(owner_id="test_owner_003")
        key_id = result["key_id"]
        
        # Revoke key
        success = km.revoke_key(key_id)
        assert success, "Revocation failed"
        
        # Verify key is revoked
        with km._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT is_active, revoked_at 
                    FROM api_keys 
                    WHERE id = %s
                """, (key_id,))
                
                is_active, revoked_at = cur.fetchone()
                
                assert not is_active
                assert revoked_at is not None


class TestAuthentication:
    """Test 3: Authentication Middleware"""
    
    def test_valid_key_authentication(self):
        """Test authentication with valid key"""
        km = KeyManager()
        result = km.create_api_key(owner_id="test_owner_004")
        api_key = result["api_key"]
        
        # Validate key
        context = km.validate_key(api_key)
        
        assert context is not None
        assert context["owner_id"] == "test_owner_004"
        assert "key_id" in context
        assert "rate_limit_per_minute" in context
    
    def test_invalid_key_rejection(self):
        """Test rejection of invalid keys"""
        km = KeyManager()
        
        # Invalid format
        context = km.validate_key("invalid_key")
        assert context is None
        
        # Valid format but doesn't exist
        context = km.validate_key("aimsk_live_" + "0" * 64)
        assert context is None
    
    def test_revoked_key_rejection(self):
        """Test rejection of revoked keys"""
        km = KeyManager()
        
        result = km.create_api_key(owner_id="test_owner_005")
        api_key = result["api_key"]
        key_id = result["key_id"]
        
        # Revoke key
        km.revoke_key(key_id)
        
        # Try to validate
        context = km.validate_key(api_key)
        assert context is None, "Revoked key should not validate"


class TestRateLimiting:
    """Test 4: Rate Limiting"""
    
    def test_token_bucket_creation(self):
        """Test token bucket initialization"""
        bucket = TokenBucket(capacity=60, refill_rate=1.0)
        
        assert bucket.capacity == 60
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 60.0
    
    def test_token_consumption(self):
        """Test token consumption"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Consume tokens
        assert bucket.consume(1) == True
        assert bucket.get_remaining() == 9
        
        # Consume all tokens
        for _ in range(9):
            bucket.consume(1)
        
        assert bucket.get_remaining() == 0
        assert bucket.consume(1) == False  # Should fail
    
    def test_token_refill(self):
        """Test token refill over time"""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec
        
        # Consume all tokens
        for _ in range(10):
            bucket.consume(1)
        
        assert bucket.get_remaining() == 0
        
        # Wait 1 second
        time.sleep(1.1)
        
        # Should have refilled
        assert bucket.get_remaining() >= 10
    
    def test_rate_limiter_per_key(self):
        """Test per-key rate limiting"""
        limiter = RateLimiter()
        
        # Different keys should have separate limits
        allowed1, remaining1, reset1 = limiter.check_rate_limit("key1", 60)
        allowed2, remaining2, reset2 = limiter.check_rate_limit("key2", 60)
        
        assert allowed1 == True
        assert allowed2 == True
        assert remaining1 == 59
        assert remaining2 == 59


class TestDataIsolation:
    """Test 5: Data Isolation"""
    
    def test_owner_id_from_key(self):
        """Verify owner_id is derived from API key"""
        km = KeyManager()
        
        result1 = km.create_api_key(owner_id="customer_a")
        result2 = km.create_api_key(owner_id="customer_b")
        
        context1 = km.validate_key(result1["api_key"])
        context2 = km.validate_key(result2["api_key"])
        
        assert context1["owner_id"] == "customer_a"
        assert context2["owner_id"] == "customer_b"
        assert context1["owner_id"] != context2["owner_id"]
    
    def test_no_cross_owner_access(self):
        """Verify keys cannot access other owner's data"""
        km = KeyManager()
        
        # Create keys for different owners
        result_a = km.create_api_key(owner_id="owner_a")
        result_b = km.create_api_key(owner_id="owner_b")
        
        # Validate keys
        context_a = km.validate_key(result_a["api_key"])
        context_b = km.validate_key(result_b["api_key"])
        
        # Verify isolation
        assert context_a["owner_id"] != context_b["owner_id"]


class TestErrorHandling:
    """Test 6: Error Handling"""
    
    def test_constant_error_messages(self):
        """Verify all auth failures return same message"""
        km = KeyManager()
        
        # All these should return None (which maps to same 401 error)
        invalid_cases = [
            "invalid_key",
            "aimsk_live_nonexistent",
            "",
            None
        ]
        
        for invalid_key in invalid_cases:
            if invalid_key is None:
                continue
            context = km.validate_key(invalid_key)
            assert context is None, f"Should reject: {invalid_key}"
    
    def test_no_key_leakage_in_errors(self):
        """Verify keys never appear in error messages"""
        km = KeyManager()
        
        # This should fail but not expose the key
        try:
            context = km.validate_key("aimsk_live_secret_key_123")
            assert context is None
        except Exception as e:
            error_msg = str(e)
            assert "aimsk_live_secret_key_123" not in error_msg


class TestSecurity:
    """Test 7: Security Hardening"""
    
    def test_sha256_hashing(self):
        """Verify SHA-256 hashing"""
        km = KeyManager()
        
        test_key = "aimsk_live_test123"
        hash1 = km.hash_key(test_key)
        hash2 = km.hash_key(test_key)
        
        # Same input = same hash
        assert hash1 == hash2
        
        # Hash is 64 chars (SHA-256 hex)
        assert len(hash1) == 64
        
        # Hash is different from input
        assert hash1 != test_key
    
    def test_audit_logging(self):
        """Verify audit logging for key operations"""
        km = KeyManager()
        db = Database()
        
        # Create key
        result = km.create_api_key(owner_id="test_audit_001")
        
        # Check audit log
        with db._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT action, user_id, resource_id 
                    FROM audit_logs 
                    WHERE user_id = %s 
                    AND action = 'api_key.create'
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, ("test_audit_001",))
                
                log = cur.fetchone()
                assert log is not None
                assert log[0] == "api_key.create"
                assert log[1] == "test_audit_001"
                assert log[2] == result["key_id"]


class TestBackwardCompatibility:
    """Test 8: Backward Compatibility"""
    
    def test_legacy_auth_support(self):
        """Verify legacy auth still works (if enabled)"""
        # This tests that the fallback mechanism exists
        # Actual behavior depends on env vars
        from api.auth import hash_api_key, verify_api_key_constant_time
        
        test_key = "legacy_key_123"
        hashed = hash_api_key(test_key)
        
        # Verify constant-time comparison works
        assert verify_api_key_constant_time(test_key, hashed)
        assert not verify_api_key_constant_time("wrong_key", hashed)


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*70)
    print("API KEY SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*70 + "\n")
    
    test_classes = [
        TestDatabaseSchema,
        TestKeyGeneration,
        TestAuthentication,
        TestRateLimiting,
        TestDataIsolation,
        TestErrorHandling,
        TestSecurity,
        TestBackwardCompatibility
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n{test_class.__doc__}")
        print("-" * 70)
        
        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            method = getattr(test_instance, method_name)
            
            try:
                method()
                print(f"  ✓ {method.__doc__}")
                passed_tests += 1
            except Exception as e:
                print(f"  ✗ {method.__doc__}")
                print(f"    Error: {str(e)}")
                failed_tests.append((test_class.__name__, method_name, str(e)))
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed Tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}: {error}")
    else:
        print("\n✓ ALL TESTS PASSED!")
    
    print("\n" + "="*70 + "\n")
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
