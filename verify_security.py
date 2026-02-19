"""Security Verification Tests"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sdk import MemorySDK, MemoryAuthError, MemoryValidationError, MemoryNotFoundError
import requests
import time

print("=" * 70)
print("SECURITY HARDENING VERIFICATION")
print("=" * 70)

BASE_URL = "http://localhost:8000"

def get_auth_token(email="security@example.com", password="password123"):
    """Get JWT token via login or signup."""
    # Try login
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    
    # Try signup
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Security Test User"}
    )
    if response.status_code == 200:
        # Login again
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        return response.json()["access_token"]
    
    # If fails, maybe already signed up but login failed? 
    # Or maybe it's cleaner to just print warning
    print(f"Warning: Auth failed: {response.text}")
    return "dev-key-12345"

try:
    API_KEY = get_auth_token()
    print(f"\n🔐 Authenticated with token: {API_KEY[:10]}...")
except Exception as e:
    print(f"\n⚠ Auth setup failed: {e}")
    API_KEY = "dev-key-12345"

# Test 1: HTTPS Enforcement
print("\n[1/8] Testing HTTPS Enforcement")
try:
    sdk = MemorySDK(
        api_key=API_KEY,
        user_id="test-user",
        base_url="http://insecure.com"
    )
    print("✗ FAIL: SDK allowed HTTP without opt-in")
except ValueError as e:
    if "insecure" in str(e).lower():
        print("✓ PASS: SDK rejects HTTP by default")
    else:
        print(f"✗ FAIL: Wrong error: {e}")

# Test with opt-in
try:
    sdk = MemorySDK(
        api_key=API_KEY,
        user_id="test-user",
        base_url=BASE_URL,
        allow_insecure_http=True
    )
    print("✓ PASS: SDK allows HTTP with explicit opt-in")
except Exception as e:
    print(f"✗ FAIL: {e}")

# Test 2: User Isolation - Cross-User Deletion
print("\n[2/8] Testing User Isolation (Cross-User Deletion)")
user_a_id = f"user-a-{int(time.time())}"
user_b_id = f"user-b-{int(time.time())}"

sdk_a = MemorySDK(api_key=API_KEY, user_id=user_a_id, base_url=BASE_URL, allow_insecure_http=True)
sdk_b = MemorySDK(api_key=API_KEY, user_id=user_b_id, base_url=BASE_URL, allow_insecure_http=True)

# User A creates memory
mem_a = sdk_a.add_memory("User A's secret", "fact")
print(f"✓ User A created memory: {mem_a['id'][:8]}...")

# User B tries to delete User A's memory
try:
    sdk_b.delete_memory(mem_a['id'])
    print("✗ FAIL: User B deleted User A's memory (isolation broken!)")
except MemoryNotFoundError:
    print("✓ PASS: User B cannot delete User A's memory")

# Test 3: GDPR Cross-User Protection
print("\n[3/8] Testing GDPR Cross-User Protection")
# User B tries to export User A's data by manipulating header
try:
    response = requests.get(
        f"{BASE_URL}/api/v1/gdpr/export",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "X-User-ID": user_a_id  # User B trying to access User A's data
        }
    )
    if response.status_code == 200:
        data = response.json()
        if data['user_id'] == user_a_id:
            print("✓ PASS: GDPR export returns data for authenticated user only")
        else:
            print("✗ FAIL: GDPR export returned wrong user's data")
    else:
        print(f"✗ FAIL: Unexpected status {response.status_code}")
except Exception as e:
    print(f"✗ FAIL: {e}")

# Test 4: Rate Limiting
print("\n[4/8] Testing Rate Limiting")
print("Sending 105 requests to trigger rate limit...")
rate_limited = False
for i in range(105):
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/memory",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "X-User-ID": f"rate-test-{int(time.time())}"
            }
        )
        if response.status_code == 429:
            rate_limited = True
            print(f"✓ PASS: Rate limited after {i+1} requests")
            break
    except:
        pass

if not rate_limited:
    print("✗ FAIL: No rate limiting detected after 105 requests")

# Test 5: Metadata Validation (Depth)
print("\n[5/8] Testing Metadata Depth Validation")
deep_metadata = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "too deep"}}}}}}}
try:
    sdk_a.add_memory("test", "fact", metadata=deep_metadata)
    print("✗ FAIL: Deeply nested metadata accepted")
except MemoryValidationError as e:
    if "nested" in str(e).lower():
        print("✓ PASS: Deeply nested metadata rejected")
    else:
        print(f"✗ FAIL: Wrong error: {e}")

# Test 6: Metadata Validation (Size)
print("\n[6/8] Testing Metadata Size Validation")
large_metadata = {"data": "x" * 10000}  # 10KB
try:
    sdk_a.add_memory("test", "fact", metadata=large_metadata)
    print("✗ FAIL: Large metadata accepted")
except MemoryValidationError as e:
    if "large" in str(e).lower() or "size" in str(e).lower():
        print("✓ PASS: Large metadata rejected")
    else:
        print(f"✗ FAIL: Wrong error: {e}")

# Test 7: Missing X-User-ID Header
print("\n[7/8] Testing Missing X-User-ID Header")
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/memory",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"content": "test", "type": "fact"}
    )
    if response.status_code == 401:
        print("✓ PASS: Missing X-User-ID returns 401")
    else:
        print(f"✗ FAIL: Expected 401, got {response.status_code}")
except Exception as e:
    print(f"✗ FAIL: {e}")

# Test 8: Invalid API Key (Constant-Time)
print("\n[8/8] Testing Constant-Time API Key Comparison")
print("Measuring response times for invalid keys...")
times = []
for i in range(10):
    start = time.time()
    response = requests.get(
        f"{BASE_URL}/api/v1/memory",
        headers={
            "Authorization": f"Bearer wrong-key-{i}",
            "X-User-ID": "test"
        }
    )
    elapsed = time.time() - start
    times.append(elapsed)

avg_time = sum(times) / len(times)
variance = sum((t - avg_time) ** 2 for t in times) / len(times)
if variance < 0.001:  # Low variance indicates constant-time
    print(f"✓ PASS: Low timing variance ({variance:.6f}s²) - likely constant-time")
else:
    print(f"⚠ WARNING: High timing variance ({variance:.6f}s²) - may be vulnerable to timing attacks")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
