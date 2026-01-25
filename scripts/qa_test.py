"""
QA Test Script for AI Memory SDK
Tests all major functionality end-to-end.
"""
import requests
import time
import sys
from typing import Dict, Any


BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_qa_001"


class Colors:
    """Terminal colors."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_test(name: str):
    """Print test name."""
    print(f"\n{Colors.BLUE}▶ TEST: {name}{Colors.END}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.END}")


def test_health_check() -> bool:
    """Test 1: Health check."""
    print_test("Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health check passed: {data}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False


def test_extract_memory_name() -> bool:
    """Test 2: Extract memory from name."""
    print_test("Extract Memory - Name")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/memory/extract",
            params={
                "user_id": TEST_USER_ID,
                "message": "My name is Alice and I'm 28 years old"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            extracted_count = data.get("extracted_count", 0)
            
            if extracted_count > 0:
                print_success(f"Extracted {extracted_count} memories")
                print_info(f"Memories: {data.get('memories', [])}")
                return True
            else:
                print_error("No memories extracted")
                return False
        else:
            print_error(f"Extraction failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print_error(f"Extraction error: {e}")
        return False


def test_extract_memory_preference() -> bool:
    """Test 3: Extract preference memory."""
    print_test("Extract Memory - Preference")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/memory/extract",
            params={
                "user_id": TEST_USER_ID,
                "message": "I love pizza and hate broccoli"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            extracted_count = data.get("extracted_count", 0)
            
            if extracted_count > 0:
                print_success(f"Extracted {extracted_count} preferences")
                return True
            else:
                print_error("No preferences extracted")
                return False
        else:
            print_error(f"Extraction failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Extraction error: {e}")
        return False


def test_retrieve_memory() -> bool:
    """Test 4: Retrieve memories."""
    print_test("Retrieve Memories")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/memory/{TEST_USER_ID}")
        
        if response.status_code == 200:
            data = response.json()
            count = data.get("count", 0)
            memories = data.get("memories", [])
            
            print_success(f"Retrieved {count} memories")
            
            for mem in memories:
                print_info(f"  - {mem['type']}: {mem['key']} = {mem['value']}")
            
            return count > 0
        else:
            print_error(f"Retrieval failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Retrieval error: {e}")
        return False


def test_chat_with_memory() -> bool:
    """Test 5: Chat remembers user."""
    print_test("Chat with Memory")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={
                "user_id": TEST_USER_ID,
                "message": "What's my name?",
                "auto_save": False
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get("response", "")
            
            print_success("Chat response received")
            print_info(f"AI: {ai_response}")
            
            # Check if response mentions the name
            if "alice" in ai_response.lower():
                print_success("AI correctly remembered the name!")
                return True
            else:
                print_error("AI did not remember the name")
                return False
        else:
            print_error(f"Chat failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print_error(f"Chat error: {e}")
        return False


def test_memory_stats() -> bool:
    """Test 6: Get memory statistics."""
    print_test("Memory Statistics")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/memory/{TEST_USER_ID}/stats")
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get("stats", {})
            
            print_success(f"Stats retrieved: {stats}")
            return True
        else:
            print_error(f"Stats failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Stats error: {e}")
        return False


def test_delete_memory() -> bool:
    """Test 7: Delete all memories."""
    print_test("Delete All Memories")
    
    try:
        response = requests.delete(f"{BASE_URL}/api/v1/memory/{TEST_USER_ID}")
        
        if response.status_code == 200:
            data = response.json()
            deleted_count = data.get("deleted_count", 0)
            
            print_success(f"Deleted {deleted_count} memories")
            return True
        else:
            print_error(f"Deletion failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Deletion error: {e}")
        return False


def test_verify_deletion() -> bool:
    """Test 8: Verify memories are gone."""
    print_test("Verify Deletion")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/memory/{TEST_USER_ID}")
        
        if response.status_code == 200:
            data = response.json()
            count = data.get("count", 0)
            
            if count == 0:
                print_success("All memories successfully deleted")
                return True
            else:
                print_error(f"Still {count} memories remaining")
                return False
        else:
            print_error(f"Verification failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_error(f"Verification error: {e}")
        return False


def run_all_tests():
    """Run all QA tests."""
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}AI MEMORY SDK - QA TEST SUITE{Colors.END}")
    print(f"{'='*60}")
    
    tests = [
        ("Health Check", test_health_check),
        ("Extract Memory - Name", test_extract_memory_name),
        ("Extract Memory - Preference", test_extract_memory_preference),
        ("Retrieve Memories", test_retrieve_memory),
        ("Chat with Memory", test_chat_with_memory),
        ("Memory Statistics", test_memory_stats),
        ("Delete All Memories", test_delete_memory),
        ("Verify Deletion", test_verify_deletion),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            time.sleep(0.5)  # Small delay between tests
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results.append((name, False))
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{status} - {name}")
    
    print(f"\n{Colors.BLUE}Results: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ ALL TESTS PASSED!{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}✗ SOME TESTS FAILED{Colors.END}\n")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
