import requests
import uuid

BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = f"test_{uuid.uuid4()}@example.com"
TEST_PASSWORD = "secure_password_123"

def test_auth_flow():
    print(f"Testing Auth Flow with {TEST_EMAIL}...\n")

    # 1. Signup
    print("1. Testing Signup...")
    signup_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": "Test User"
    }
    try:
        resp = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
        if resp.status_code == 200:
            print(f"✅ Signup Success: {resp.json().keys()}")
            token = resp.json()["access_token"]
        else:
            print(f"❌ Signup Failed: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    # 2. Login
    print("\n2. Testing Login...")
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if resp.status_code == 200:
            print(f"✅ Login Success: {resp.json().keys()}")
            token = resp.json()["access_token"]
        else:
            print(f"❌ Login Failed: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    # 3. Protected Route (Memory List)
    print("\n3. Testing Protected Route (List Memories)...")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "default-tenant"
    }
    try:
        resp = requests.get(f"{BASE_URL}/user/memories", headers=headers)
        if resp.status_code == 200:
            print(f"✅ Protected Route Access Success: {resp.status_code}")
        else:
            print(f"❌ Protected Route Access Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

    # 4. Invalid Token
    print("\n4. Testing Invalid Token...")
    bad_headers = {
        "Authorization": "Bearer invalid_token",
        "X-Tenant-ID": "default-tenant"
    }
    try:
        resp = requests.get(f"{BASE_URL}/user/memories", headers=bad_headers)
        if resp.status_code == 401:
            print(f"✅ Invalid Token Blocked Correctly: {resp.status_code}")
        else:
            print(f"❌ Invalid Token Allowed (Unexpected): {resp.status_code}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_auth_flow()
