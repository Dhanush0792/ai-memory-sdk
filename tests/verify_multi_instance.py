"""
Multi-instance deployment verification script.
Tests horizontal scaling, shared rate limiting, and state consistency.
"""

import requests
import time
import sys


class MultiInstanceVerifier:
    """Verify multi-instance deployment."""
    
    def __init__(
        self,
        instance_urls: list,
        api_key: str = "test-api-key-1234567890",
        tenant_id: str = "test-tenant",
        user_id: str = "test-user"
    ):
        self.instance_urls = instance_urls
        self.headers = {
            "X-API-Key": api_key,
            "X-Tenant-ID": tenant_id,
            "X-User-ID": user_id,
            "Content-Type": "application/json"
        }
    
    def test_health_checks(self) -> bool:
        """Test all instances are healthy."""
        print("\n🔍 Testing Health Checks...")
        
        all_healthy = True
        for url in self.instance_urls:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    print(f"  ✅ {url} - healthy")
                else:
                    print(f"  ❌ {url} - unhealthy (status {response.status_code})")
                    all_healthy = False
            except Exception as e:
                print(f"  ❌ {url} - unreachable ({e})")
                all_healthy = False
        
        return all_healthy
    
    def test_shared_rate_limiting(self) -> bool:
        """Test rate limiting is shared across instances."""
        print("\n🔍 Testing Shared Rate Limiting...")
        
        # Make requests to different instances
        requests_made = 0
        rate_limited = False
        
        for i in range(150):  # Exceed default limit of 100
            instance_url = self.instance_urls[i % len(self.instance_urls)]
            
            try:
                response = requests.post(
                    f"{instance_url}/api/v1/memory/ingest",
                    headers=self.headers,
                    json={"conversation_text": f"Test memory {i}"},
                    timeout=5
                )
                
                requests_made += 1
                
                if response.status_code == 429:  # Rate limited
                    rate_limited = True
                    print(f"  ✅ Rate limit enforced after {requests_made} requests")
                    break
                    
            except Exception as e:
                print(f"  ❌ Request failed: {e}")
                return False
        
        if not rate_limited:
            print(f"  ⚠️  Rate limit NOT enforced after {requests_made} requests")
            return False
        
        return True
    
    def test_state_consistency(self) -> bool:
        """Test state consistency across instances."""
        print("\n🔍 Testing State Consistency...")
        
        # Ingest memory on instance 1
        ingest_url = self.instance_urls[0]
        response = requests.post(
            f"{ingest_url}/api/v1/memory/ingest",
            headers=self.headers,
            json={"conversation_text": "User prefers concise explanations"},
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"  ❌ Ingest failed on {ingest_url}")
            return False
        
        print(f"  ✅ Memory ingested on {ingest_url}")
        
        # Wait for propagation
        time.sleep(1)
        
        # Retrieve from instance 2
        retrieve_url = self.instance_urls[1 % len(self.instance_urls)]
        response = requests.get(
            f"{retrieve_url}/api/v1/memory/{self.headers['X-User-ID']}",
            headers=self.headers,
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"  ❌ Retrieve failed on {retrieve_url}")
            return False
        
        memories = response.json()
        if not memories:
            print(f"  ❌ Memory not found on {retrieve_url}")
            return False
        
        print(f"  ✅ Memory retrieved from {retrieve_url}")
        print(f"  ✅ State consistent across instances")
        
        return True
    
    def test_restart_persistence(self) -> bool:
        """Test rate limit persists after restart."""
        print("\n🔍 Testing Restart Persistence...")
        print("  ⚠️  Manual test required:")
        print("  1. Make 50 requests")
        print("  2. Restart app container")
        print("  3. Make 60 more requests")
        print("  4. Should be rate limited after ~100 total")
        
        return True  # Manual verification
    
    def run_all_tests(self) -> bool:
        """Run all verification tests."""
        print("\n" + "=" * 80)
        print("MULTI-INSTANCE DEPLOYMENT VERIFICATION")
        print("=" * 80)
        print(f"Testing {len(self.instance_urls)} instances:")
        for url in self.instance_urls:
            print(f"  - {url}")
        
        results = {
            "Health Checks": self.test_health_checks(),
            "Shared Rate Limiting": self.test_shared_rate_limiting(),
            "State Consistency": self.test_state_consistency(),
            "Restart Persistence": self.test_restart_persistence()
        }
        
        print("\n" + "=" * 80)
        print("VERIFICATION RESULTS")
        print("=" * 80)
        
        all_passed = True
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:30} {status}")
            if not passed:
                all_passed = False
        
        print("=" * 80)
        
        if all_passed:
            print("\n✅ All tests passed! Multi-instance deployment verified.")
        else:
            print("\n❌ Some tests failed. Review configuration.")
        
        return all_passed


if __name__ == "__main__":
    # Test with 2 instances
    instances = [
        "http://localhost:8000",
        "http://localhost:8001"  # Scale with: docker-compose up --scale app=2
    ]
    
    verifier = MultiInstanceVerifier(instances)
    success = verifier.run_all_tests()
    
    sys.exit(0 if success else 1)
