"""Quick test to verify auth endpoints work."""
import requests
import sys

BASE = "http://localhost:8000"

print("1. Testing health...")
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    print(f"   Health: {r.status_code} {r.text}")
except Exception as e:
    print(f"   Health FAILED: {e}")
    sys.exit(1)

print("2. Testing signup...")
try:
    r = requests.post(
        f"{BASE}/api/v1/auth/signup",
        json={"email": "quicktest@test.com", "password": "testpass123", "full_name": "Quick Test"},
        timeout=15
    )
    print(f"   Signup: {r.status_code} {r.text}")
except requests.exceptions.Timeout:
    print("   Signup TIMED OUT after 15s!")
except Exception as e:
    print(f"   Signup FAILED: {e}")

print("3. Testing login...")
try:
    r = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"email": "quicktest@test.com", "password": "testpass123"},
        timeout=15
    )
    print(f"   Login: {r.status_code} {r.text}")
except requests.exceptions.Timeout:
    print("   Login TIMED OUT after 15s!")
except Exception as e:
    print(f"   Login FAILED: {e}")

print("Done.")
