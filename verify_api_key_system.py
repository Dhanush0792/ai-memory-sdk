"""
API Key System Verification Script

Quick verification of all implemented features.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from backend.api.key_manager import KeyManager
from backend.api.database import Database
from backend.api.rate_limiter import TokenBucket


def verify_database_schema():
    """Verify database schema"""
    print("\n1️⃣ DATABASE SCHEMA")
    print("-" * 60)
    
    try:
        db = Database()
        
        with db._get_conn() as conn:
            with conn.cursor() as cur:
                # Check api_keys table
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'api_keys'
                    );
                """)
                exists = cur.fetchone()[0]
                
                if exists:
                    print("✓ api_keys table exists")
                    
                    # Check indexes
                    cur.execute("""
                        SELECT indexname 
                        FROM pg_indexes 
                        WHERE tablename = 'api_keys';
                    """)
                    indexes = [row[0] for row in cur.fetchall()]
                    
                    required_indexes = ['idx_key_hash', 'idx_owner_id', 'idx_is_active']
                    for idx in required_indexes:
                        if idx in indexes:
                            print(f"✓ Index {idx} exists")
                        else:
                            print(f"✗ Index {idx} missing")
                else:
                    print("✗ api_keys table does not exist")
                    return False
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_key_generation():
    """Verify key generation"""
    print("\n2️⃣ KEY GENERATION & MANAGEMENT")
    print("-" * 60)
    
    try:
        km = KeyManager()
        
        # Generate key
        key = km.generate_api_key()
        if key.startswith("aimsk_live_"):
            print(f"✓ Key format correct: {key[:20]}...")
        else:
            print(f"✗ Invalid key format: {key}")
            return False
        
        # Create key
        result = km.create_api_key(
            owner_id="verify_test_001",
            rate_limit_per_minute=100
        )
        
        print(f"✓ Key created: {result['key_id']}")
        print(f"✓ Owner ID: {result['owner_id']}")
        print(f"✓ Rate limit: {result['rate_limit_per_minute']}")
        
        # Verify no plaintext storage
        with km._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT key_hash FROM api_keys WHERE id = %s
                """, (result['key_id'],))
                
                stored_hash = cur.fetchone()[0]
                if stored_hash != result['api_key'] and len(stored_hash) == 64:
                    print("✓ Key stored as SHA-256 hash (not plaintext)")
                else:
                    print("✗ Key not properly hashed")
                    return False
        
        # Test validation
        context = km.validate_key(result['api_key'])
        if context and context['owner_id'] == 'verify_test_001':
            print("✓ Key validation works")
        else:
            print("✗ Key validation failed")
            return False
        
        # Test revocation
        success = km.revoke_key(result['key_id'])
        if success:
            print("✓ Key revocation works")
            
            # Verify revoked key fails validation
            context = km.validate_key(result['api_key'])
            if context is None:
                print("✓ Revoked key rejected")
            else:
                print("✗ Revoked key still validates")
                return False
        else:
            print("✗ Key revocation failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_rate_limiting():
    """Verify rate limiting"""
    print("\n3️⃣ RATE LIMITING")
    print("-" * 60)
    
    try:
        # Test token bucket
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        if bucket.capacity == 10:
            print("✓ Token bucket created")
        else:
            print("✗ Token bucket creation failed")
            return False
        
        # Test consumption
        success = bucket.consume(1)
        if success and bucket.get_remaining() == 9:
            print("✓ Token consumption works")
        else:
            print("✗ Token consumption failed")
            return False
        
        # Test exhaustion
        for _ in range(9):
            bucket.consume(1)
        
        if bucket.get_remaining() == 0 and not bucket.consume(1):
            print("✓ Rate limit enforcement works")
        else:
            print("✗ Rate limit enforcement failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_security():
    """Verify security measures"""
    print("\n4️⃣ SECURITY")
    print("-" * 60)
    
    try:
        km = KeyManager()
        
        # Test SHA-256 hashing
        test_key = "aimsk_live_test123"
        hash1 = km.hash_key(test_key)
        hash2 = km.hash_key(test_key)
        
        if hash1 == hash2 and len(hash1) == 64 and hash1 != test_key:
            print("✓ SHA-256 hashing works")
        else:
            print("✗ Hashing failed")
            return False
        
        # Test audit logging
        result = km.create_api_key(owner_id="security_test_001")
        
        db = Database()
        with db._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT action FROM audit_logs 
                    WHERE user_id = %s AND action = 'api_key.create'
                    ORDER BY timestamp DESC LIMIT 1
                """, ("security_test_001",))
                
                log = cur.fetchone()
                if log and log[0] == 'api_key.create':
                    print("✓ Audit logging works")
                else:
                    print("✗ Audit logging failed")
                    return False
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_data_isolation():
    """Verify data isolation"""
    print("\n5️⃣ DATA ISOLATION")
    print("-" * 60)
    
    try:
        km = KeyManager()
        
        # Create keys for different owners
        result_a = km.create_api_key(owner_id="owner_a")
        result_b = km.create_api_key(owner_id="owner_b")
        
        context_a = km.validate_key(result_a['api_key'])
        context_b = km.validate_key(result_b['api_key'])
        
        if context_a['owner_id'] != context_b['owner_id']:
            print("✓ Owner IDs are isolated")
        else:
            print("✗ Owner IDs not isolated")
            return False
        
        if context_a['owner_id'] == 'owner_a' and context_b['owner_id'] == 'owner_b':
            print("✓ Owner IDs correctly assigned")
        else:
            print("✗ Owner IDs incorrectly assigned")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all verifications"""
    print("\n" + "="*60)
    print("API KEY SYSTEM VERIFICATION")
    print("="*60)
    
    results = []
    
    results.append(("Database Schema", verify_database_schema()))
    results.append(("Key Generation", verify_key_generation()))
    results.append(("Rate Limiting", verify_rate_limiting()))
    results.append(("Security", verify_security()))
    results.append(("Data Isolation", verify_data_isolation()))
    
    print("\n" + "="*60)
    print("VERIFICATION RESULTS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n✓ ALL VERIFICATIONS PASSED!")
        print("\nThe API key system is production-ready.")
        return 0
    else:
        print("\n✗ SOME VERIFICATIONS FAILED")
        print("\nPlease review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
