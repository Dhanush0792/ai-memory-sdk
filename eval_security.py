"""
Evaluation Test Script - Security Expectations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sdk import MemorySDK, MemoryAuthError
import requests
import time

print("=" * 60)
print("EVALUATION TEST: Security Expectations")
print("=" * 60)

BASE_URL = "http://localhost:8000"

# Test 1: Authentication enforcement
print("\n[1/4] Role Enforcement (API Key)")

# Test invalid API key
try:
    bad_sdk = MemorySDK(
        api_key="invalid-key-12345",
        user_id="test-user",
        base_url=BASE_URL
    )
    bad_sdk.add_memory("This should fail", "fact")
    print("✗ CRITICAL: Invalid API key accepted")
except MemoryAuthError:
    print("✓ Invalid API key rejected")
except Exception as e:
    print(f"✗ Unexpected error: {e}")

# Test missing API key
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/memory",
        json={"user_id": "test", "content": "test", "type": "fact"}
    )
    if response.status_code == 401:
        print("✓ Missing API key rejected")
    else:
        print(f"✗ CRITICAL: Missing API key got status {response.status_code}")
except Exception as e:
    print(f"✗ Request failed: {e}")

# Test malformed Authorization header
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers={"Authorization": "InvalidFormat"},
        json={"user_id": "test", "content": "test", "type": "fact"}
    )
    if response.status_code == 401:
        print("✓ Malformed auth header rejected")
    else:
        print(f"✗ WARNING: Malformed auth got status {response.status_code}")
except Exception as e:
    print(f"✗ Request failed: {e}")

# Test 2: Data encryption guarantees
print("\n[2/4] Data Encryption Guarantees")
print("  Checking for encryption documentation...")

# Check if .env mentions encryption
try:
    with open(".env.example", "r") as f:
        env_content = f.read()
        if "ENCRYPTION" in env_content or "encryption" in env_content:
            print("✓ Encryption configuration found")
        else:
            print("✗ WARNING: No encryption configuration visible")
except:
    print("✗ Cannot read .env.example")

# Check database schema for encryption
try:
    with open("api/database.py", "r") as f:
        db_content = f.read()
        if "encrypt" in db_content.lower() or "cipher" in db_content.lower():
            print("✓ Encryption code found in database layer")
        else:
            print("✗ CRITICAL: No encryption code visible in database layer")
except:
    print("✗ Cannot read database.py")

print("  Note: Field-level encryption not observable from SDK")

# Test 3: Audit log integrity
print("\n[3/4] Audit Log Integrity")

sdk = MemorySDK(
    api_key="dev-key-12345",
    user_id=f"audit-test-{int(time.time())}",
    base_url=BASE_URL
)

# Perform actions that should be logged
try:
    mem = sdk.add_memory("Test memory", "fact")
    sdk.delete_memory(mem['id'])
    sdk.export_user_data()
    sdk.delete_user_data(confirm=True)
    print("✓ Performed actions that should generate audit logs")
except Exception as e:
    print(f"✗ Actions failed: {e}")

# Check if audit logs table exists
try:
    with open("api/database.py", "r") as f:
        db_content = f.read()
        if "audit_logs" in db_content:
            print("✓ Audit logs table found in schema")
        else:
            print("✗ CRITICAL: No audit logs table")
        
        if "INSERT INTO audit_logs" in db_content:
            print("✓ Audit logging code found")
        else:
            print("✗ WARNING: Audit logging may not be implemented")
except:
    print("✗ Cannot verify audit logs")

print("  Note: Audit log tamper-evidence not verifiable from SDK")

# Test 4: Key management clarity
print("\n[4/4] Key Management Clarity")

# Check .env configuration
try:
    with open(".env.example", "r") as f:
        env_lines = f.readlines()
        
    api_key_found = False
    db_url_found = False
    
    for line in env_lines:
        if "API_KEY" in line:
            api_key_found = True
            if "your-" in line or "example" in line or "dev-" in line:
                print("✓ API_KEY placeholder found in .env.example")
            else:
                print("✗ WARNING: API_KEY may contain real value")
        
        if "DATABASE_URL" in line:
            db_url_found = True
    
    if not api_key_found:
        print("✗ CRITICAL: API_KEY not in .env.example")
    if not db_url_found:
        print("✗ WARNING: DATABASE_URL not in .env.example")
    
    print("✓ Environment variable pattern documented")
    
except Exception as e:
    print(f"✗ Cannot verify key management: {e}")

# Check for hardcoded secrets
try:
    with open("sdk/client.py", "r") as f:
        sdk_content = f.read()
        
    if "api_key" in sdk_content and "Bearer" in sdk_content:
        print("✓ API key passed via constructor (not hardcoded)")
    
    # Check for common hardcoded patterns
    dangerous_patterns = ["password=", "secret=", "token="]
    found_hardcoded = False
    for pattern in dangerous_patterns:
        if pattern in sdk_content.lower():
            print(f"✗ WARNING: Found '{pattern}' in SDK code")
            found_hardcoded = True
    
    if not found_hardcoded:
        print("✓ No obvious hardcoded secrets in SDK")
        
except Exception as e:
    print(f"✗ Cannot check for hardcoded secrets: {e}")

# Test 5: User isolation
print("\n[5/5] User Data Isolation")

user1 = MemorySDK(
    api_key="dev-key-12345",
    user_id=f"isolation-user1-{int(time.time())}",
    base_url=BASE_URL
)

user2 = MemorySDK(
    api_key="dev-key-12345",
    user_id=f"isolation-user2-{int(time.time())}",
    base_url=BASE_URL
)

try:
    # User 1 creates memory
    mem1 = user1.add_memory("User 1 secret data", "fact")
    
    # User 2 should not see User 1's data
    user2_memories = user2.get_memories()
    
    if len(user2_memories) == 0:
        print("✓ User isolation enforced")
    else:
        # Check if any memory belongs to user1
        leaked = False
        for mem in user2_memories:
            if mem['user_id'] == user1.user_id:
                print("✗ CRITICAL: User data leaked across users")
                leaked = True
                break
        
        if not leaked:
            print("✓ User isolation enforced (user2 has own data)")
    
except Exception as e:
    print(f"✗ Isolation test failed: {e}")

print("\n" + "=" * 60)
print("SECURITY EXPECTATIONS: COMPLETE")
print("=" * 60)
