"""Verification Test - Security Fixes"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sdk import MemorySDK, MemoryAuthError
import requests
import psycopg
import time

print("=" * 60)
print("VERIFICATION TEST: Security Fixes")
print("=" * 60)

BASE_URL = "http://localhost:8000"

# Test 1: Encryption verification
print("\n[1/4] Verifying Field-Level Encryption")

sdk = MemorySDK(
    api_key="dev-key-12345",
    user_id=f"encrypt-test-{int(time.time())}",
    base_url=BASE_URL
)

# Add memory
mem = sdk.add_memory("Sensitive user data", "fact")
print(f"✓ Memory created: {mem['id']}")

# Check database directly
try:
    conn_string = "postgresql://postgres:postgres@localhost:5432/memory_db"
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT content FROM memories WHERE id = %s", (mem['id'],))
            db_content = cur.fetchone()[0]
            
            if db_content == "Sensitive user data":
                print("✗ CRITICAL: Content stored as plaintext in database")
            else:
                print(f"✓ Content encrypted in database")
                print(f"  DB value: {db_content[:50]}...")
except Exception as e:
    print(f"✗ Cannot verify database: {e}")

# Verify decryption works
memories = sdk.get_memories()
if memories and memories[0]['content'] == "Sensitive user data":
    print("✓ Decryption works transparently")
else:
    print("✗ CRITICAL: Decryption failed")

# Test 2: Auth status codes
print("\n[2/4] Verifying Auth Status Codes")

# Missing auth header -> 401
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/memory",
        json={"user_id": "test", "content": "test", "type": "fact"}
    )
    if response.status_code == 401:
        print("✓ Missing auth header returns 401")
    else:
        print(f"✗ FAIL: Missing auth returned {response.status_code} (expected 401)")
except Exception as e:
    print(f"✗ Request failed: {e}")

# Invalid auth token -> 403
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers={"Authorization": "Bearer invalid-key"},
        json={"user_id": "test", "content": "test", "type": "fact"}
    )
    if response.status_code == 403:
        print("✓ Invalid auth token returns 403")
    else:
        print(f"✗ FAIL: Invalid auth returned {response.status_code} (expected 403)")
except Exception as e:
    print(f"✗ Request failed: {e}")

# Malformed request body -> 422
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers={"Authorization": "Bearer dev-key-12345"},
        json={"user_id": "test", "content": "test", "type": "invalid_type"}
    )
    if response.status_code == 422:
        print("✓ Malformed request returns 422")
    else:
        print(f"  Note: Malformed request returned {response.status_code}")
except Exception as e:
    print(f"✗ Request failed: {e}")

# Test 3: .env.example verification
print("\n[3/4] Verifying .env.example")

try:
    with open(".env.example", "r") as f:
        env_content = f.read()
    
    if "ENCRYPTION_KEY" in env_content:
        print("✓ ENCRYPTION_KEY documented")
    else:
        print("✗ FAIL: ENCRYPTION_KEY missing")
    
    if "Generate with:" in env_content or "generate" in env_content.lower():
        print("✓ Key generation instructions present")
    else:
        print("✗ FAIL: No generation instructions")
    
    if "WARNING" in env_content or "Do not commit" in env_content:
        print("✓ Security warning present")
    else:
        print("✗ FAIL: No security warning")
        
except Exception as e:
    print(f"✗ Cannot read .env.example: {e}")

# Test 4: Quick Start verification
print("\n[4/4] Verifying Quick Start")

try:
    with open("QUICKSTART.md", "r") as f:
        qs_content = f.read()
    
    if "Encryption" in qs_content or "encryption" in qs_content:
        print("✓ Encryption mentioned in Quick Start")
    else:
        print("✗ FAIL: Encryption not mentioned")
    
    if "setup_db.py" in qs_content:
        print("✓ Non-Docker setup documented")
    else:
        print("✗ FAIL: Non-Docker setup missing")
    
    if "approximate" in qs_content.lower() or "Approximate" in qs_content:
        print("✓ Token limit clarification present")
    else:
        print("✗ FAIL: Token limit not clarified")
        
except Exception as e:
    print(f"✗ Cannot read QUICKSTART.md: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
