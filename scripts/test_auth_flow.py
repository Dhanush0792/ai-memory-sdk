
import os
import sys
import requests
import uuid

# Add parent to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

API_URL = "http://localhost:8000/api/v1/auth"

def test_auth_flow():
    print("🧪 Testing Authentication Flow...")
    
    # Generate unique user
    suffix = str(uuid.uuid4())[:8]
    email = f"test_{suffix}@example.com"
    password = "secure_password_123"
    name = f"Test User {suffix}"
    
    print(f"   Using email: {email}")
    
    # 1. Signup
    print("\n[1] Testing Signup...")
    try:
        res = requests.post(f"{API_URL}/signup", json={
            "email": email,
            "password": password,
            "name": name
        })
        
        if res.status_code == 200:
            data = res.json()
            if "access_token" in data and data["user"]["email"] == email:
                print("✅ Signup Successful! Token received.")
                access_token = data["access_token"]
            else:
                print(f"❌ Signup Failed: Unexpected response {data}")
                return
        else:
            print(f"❌ Signup Failed: {res.status_code} - {res.text}")
            return
            
    except Exception as e:
        print(f"❌ Signup Error: {e}")
        return

    # 2. Login
    print("\n[2] Testing Login...")
    try:
        res = requests.post(f"{API_URL}/login", json={
            "email": email,
            "password": password
        })
        
        if res.status_code == 200:
            data = res.json()
            if "access_token" in data:
                print("✅ Login Successful! Token received.")
            else:
                print(f"❌ Login Failed: No token in response {data}")
        else:
            print(f"❌ Login Failed: {res.status_code} - {res.text}")
            
    except Exception as e:
        print(f"❌ Login Error: {e}")

    # 3. Duplicate Email
    print("\n[3] Testing Duplicate Email...")
    try:
        res = requests.post(f"{API_URL}/signup", json={
            "email": email,
            "password": "another_password",
            "name": "Imposter"
        })
        
        if res.status_code == 400:
            print("✅ Duplicate Email Rejected (Correctly).")
        else:
            print(f"❌ Duplicate Email Check Failed: {res.status_code}")
            
    except Exception as e:
        print(f"❌ Duplicate Error: {e}")

    # 4. Invalid Password
    print("\n[4] Testing Invalid Password...")
    try:
        res = requests.post(f"{API_URL}/login", json={
            "email": email,
            "password": "wrong_password"
        })
        
        if res.status_code == 401:
            print("✅ Invalid Password Rejected (Correctly).")
        else:
            print(f"❌ Invalid Password Check Failed: {res.status_code}")
            
    except Exception as e:
        print(f"❌ Invalid Password Error: {e}")

if __name__ == "__main__":
    print("ℹ️  Make sure backend is running on localhost:8000")
    test_auth_flow()
