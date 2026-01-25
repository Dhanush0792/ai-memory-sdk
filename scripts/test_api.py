"""
Test script for FastAPI endpoints using requests library.

Run the server first: python -m app.main
Then run this script: python scripts/test_api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def test_health():
    """Test health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")


def test_chat(user_id: str, message: str):
    """Test chat endpoint."""
    print(f"Testing chat: '{message}'")
    
    payload = {
        "user_id": user_id,
        "message": message,
        "extract_memory": True
    }
    
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"AI Response: {data['response']}")
        print(f"Memories Stored: {data['memories_stored']}")
        
        if data['extracted_memories']:
            extracted = data['extracted_memories']
            if extracted['facts']:
                print(f"  Facts: {extracted['facts']}")
            if extracted['preferences']:
                print(f"  Preferences: {extracted['preferences']}")
            if extracted['events']:
                print(f"  Events: {extracted['events']}")
    else:
        print(f"Error: {response.text}")
    
    print()


def test_get_memories(user_id: str):
    """Test get memories endpoint."""
    print(f"Getting memories for {user_id}...")
    
    response = requests.get(f"{BASE_URL}/memory/{user_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total Memories: {data['total_memories']}")
        print(f"  Facts: {data['facts']}")
        print(f"  Preferences: {data['preferences']}")
        print(f"  Events: {data['events']}")
        print("\nMemories:")
        for mem in data['memories']:
            print(f"  [{mem['memory_type']}] {mem['key']}: {mem['value']}")
    else:
        print(f"Error: {response.text}")
    
    print()


def test_delete_memories(user_id: str):
    """Test delete memories endpoint."""
    print(f"Deleting memories for {user_id}...")
    
    response = requests.delete(f"{BASE_URL}/memory/{user_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Message: {data['message']}")
        print(f"Deleted: {data['deleted_count']} memories")
    else:
        print(f"Error: {response.text}")
    
    print()


def main():
    """Run API tests."""
    print("=" * 60)
    print("Memory SDK API Test")
    print("=" * 60)
    print()
    
    user_id = "test_user_123"
    
    # 1. Health check
    test_health()
    
    # 2. Chat with memory extraction
    test_chat(user_id, "Hi! I'm Alex and I work as a software engineer at Microsoft.")
    test_chat(user_id, "I prefer concise responses and I love Python programming.")
    test_chat(user_id, "Just finished a machine learning course yesterday!")
    
    # 3. Chat with context (should reference previous memories)
    test_chat(user_id, "What do you know about me?")
    
    # 4. Get all memories
    test_get_memories(user_id)
    
    # 5. Delete memories
    test_delete_memories(user_id)
    
    # 6. Verify deletion
    test_get_memories(user_id)
    
    print("=" * 60)
    print("Tests Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
