"""Direct test of extract endpoint"""
import requests

url = "http://localhost:8001/api/v1/memory/extract"
headers = {
    "Authorization": "Bearer dev-key-12345",
    "X-User-ID": "test-direct",
    "Content-Type": "application/json"
}
data = {"message": "My name is Alice"}

print("Testing extract endpoint directly...")
print(f"URL: {url}")
print(f"Data: {data}\n")

try:
    response = requests.post(url, headers=headers, json=data, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except requests.exceptions.Timeout:
    print("Request timed out")
except Exception as e:
    print(f"Error: {e}")
