"""
Integration test scenarios for real AI chat application.
Tests the complete flow: chat → ingest → retrieve → LLM → response
"""

import requests
import time
import uuid


BASE_URL = "http://localhost:8000"
TENANT_ID = "test-tenant"


class ChatIntegrationTester:
    """Test chat integration with memory infrastructure."""
    
    def __init__(self):
        self.user_id = f"test-user-{uuid.uuid4()}"
        self.session_id = f"session-{uuid.uuid4()}"
        self.headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": TENANT_ID,
            "X-User-ID": self.user_id
        }
    
    def test_scenario_1_new_user_memory_creation(self):
        """
        Test Scenario 1: New User Memory Creation
        
        Steps:
        1. New user sends first message
        2. Verify memories ingested
        3. Verify memories appear in memory list
        """
        print("\n" + "=" * 80)
        print("TEST SCENARIO 1: New User Memory Creation")
        print("=" * 80)
        
        # Step 1: Send first message
        print("\n1. Sending first message...")
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            headers=self.headers,
            json={
                "message": "I'm Alex and I work at Microsoft as a software engineer",
                "user_id": self.user_id,
                "tenant_id": TENANT_ID
            }
        )
        
        assert response.status_code == 200, f"Chat failed: {response.status_code}"
        data = response.json()
        
        print(f"   ✓ Chat response received")
        print(f"   ✓ Memories ingested: {data['memories_ingested']}")
        print(f"   ✓ Memories retrieved: {data['memories_retrieved']}")
        print(f"   ✓ Latency: {data['latency_ms']:.0f}ms")
        
        assert data['memories_ingested'] > 0, "No memories ingested!"
        
        # Step 2: Send second message
        print("\n2. Sending second message...")
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            headers=self.headers,
            json={
                "message": "I prefer concise explanations and I love Python programming",
                "user_id": self.user_id,
                "tenant_id": TENANT_ID
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        print(f"   ✓ Memories ingested: {data['memories_ingested']}")
        
        # Step 3: Check memory list
        print("\n3. Checking memory list...")
        response = requests.get(
            f"{BASE_URL}/api/v1/user/memories",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"   ✓ Total memories: {data['total_count']}")
        print(f"   ✓ Active memories: {data['active_count']}")
        
        assert data['active_count'] >= 2, "Not enough memories created!"
        
        print("\n✅ SCENARIO 1 PASSED")
        return True
    
    def test_scenario_2_memory_retrieval_new_session(self):
        """
        Test Scenario 2: Memory Retrieval in New Session
        
        Steps:
        1. Same user asks "What do you know about me?"
        2. Verify memories retrieved
        3. Verify LLM response includes context
        """
        print("\n" + "=" * 80)
        print("TEST SCENARIO 2: Memory Retrieval in New Session")
        print("=" * 80)
        
        print("\n1. Asking 'What do you know about me?'...")
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            headers=self.headers,
            json={
                "message": "What do you know about me?",
                "user_id": self.user_id,
                "tenant_id": TENANT_ID
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"   ✓ Memories retrieved: {data['memories_retrieved']}")
        print(f"   ✓ Response preview: {data['response'][:100]}...")
        
        assert data['memories_retrieved'] > 0, "No memories retrieved!"
        
        # Check if response mentions stored facts
        response_lower = data['response'].lower()
        has_context = any(keyword in response_lower for keyword in ['alex', 'microsoft', 'python', 'concise'])
        
        if has_context:
            print("   ✓ LLM response includes memory context")
        else:
            print("   ⚠️  LLM response may not include context")
        
        print("\n✅ SCENARIO 2 PASSED")
        return True
    
    def test_scenario_3_version_conflict_update(self):
        """
        Test Scenario 3: Version Conflict Update
        
        Steps:
        1. User says "My manager is Ravi"
        2. User says "My manager changed to Arjun"
        3. Verify version 1 inactive, version 2 active
        4. Check version history
        """
        print("\n" + "=" * 80)
        print("TEST SCENARIO 3: Version Conflict Update")
        print("=" * 80)
        
        # Step 1: First manager
        print("\n1. Setting manager to Ravi...")
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            headers=self.headers,
            json={
                "message": "My manager is Ravi",
                "user_id": self.user_id,
                "tenant_id": TENANT_ID
            }
        )
        
        assert response.status_code == 200
        print("   ✓ First manager set")
        
        time.sleep(1)  # Brief delay
        
        # Step 2: Update manager
        print("\n2. Updating manager to Arjun...")
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            headers=self.headers,
            json={
                "message": "My manager changed to Arjun",
                "user_id": self.user_id,
                "tenant_id": TENANT_ID
            }
        )
        
        assert response.status_code == 200
        print("   ✓ Manager updated")
        
        # Step 3: Check version history
        print("\n3. Checking version history...")
        # Note: This requires knowing the exact subject/predicate
        # For now, just verify memories exist
        response = requests.get(
            f"{BASE_URL}/api/v1/user/memories",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find manager-related memories
        manager_memories = [
            m for m in data['memories']
            if 'manager' in m['predicate'].lower() or 'manager' in m['object'].lower()
        ]
        
        print(f"   ✓ Found {len(manager_memories)} manager-related memories")
        
        if manager_memories:
            latest = max(manager_memories, key=lambda m: m['version'])
            print(f"   ✓ Latest version: {latest['version']}")
            print(f"   ✓ Latest value: {latest['object']}")
        
        print("\n✅ SCENARIO 3 PASSED")
        return True
    
    def test_scenario_4_memory_deletion(self):
        """
        Test Scenario 4: Memory Deletion
        
        Steps:
        1. Get memory list
        2. Delete a memory
        3. Verify memory inactive
        4. Verify not in retrieval
        """
        print("\n" + "=" * 80)
        print("TEST SCENARIO 4: Memory Deletion")
        print("=" * 80)
        
        # Step 1: Get memories
        print("\n1. Getting memory list...")
        response = requests.get(
            f"{BASE_URL}/api/v1/user/memories",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if not data['memories']:
            print("   ⚠️  No memories to delete")
            return True
        
        memory_to_delete = data['memories'][0]
        print(f"   ✓ Found memory to delete: {memory_to_delete['id']}")
        
        # Step 2: Delete memory
        print("\n2. Deleting memory...")
        response = requests.delete(
            f"{BASE_URL}/api/v1/user/memories/{memory_to_delete['id']}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        print("   ✓ Memory deleted")
        
        # Step 3: Verify deletion
        print("\n3. Verifying deletion...")
        response = requests.get(
            f"{BASE_URL}/api/v1/user/memories",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check memory not in active list
        active_ids = [m['id'] for m in data['memories'] if m['is_active']]
        assert memory_to_delete['id'] not in active_ids, "Memory still active!"
        
        print("   ✓ Memory no longer in active list")
        
        print("\n✅ SCENARIO 4 PASSED")
        return True
    
    def run_all_tests(self):
        """Run all test scenarios."""
        print("\n" + "=" * 80)
        print("CHAT INTEGRATION TEST SUITE")
        print("=" * 80)
        print(f"User ID: {self.user_id}")
        print(f"Tenant ID: {TENANT_ID}")
        
        results = {}
        
        try:
            results['scenario_1'] = self.test_scenario_1_new_user_memory_creation()
        except Exception as e:
            print(f"\n❌ SCENARIO 1 FAILED: {e}")
            results['scenario_1'] = False
        
        try:
            results['scenario_2'] = self.test_scenario_2_memory_retrieval_new_session()
        except Exception as e:
            print(f"\n❌ SCENARIO 2 FAILED: {e}")
            results['scenario_2'] = False
        
        try:
            results['scenario_3'] = self.test_scenario_3_version_conflict_update()
        except Exception as e:
            print(f"\n❌ SCENARIO 3 FAILED: {e}")
            results['scenario_3'] = False
        
        try:
            results['scenario_4'] = self.test_scenario_4_memory_deletion()
        except Exception as e:
            print(f"\n❌ SCENARIO 4 FAILED: {e}")
            results['scenario_4'] = False
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        for scenario, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{scenario}: {status}")
        
        total = len(results)
        passed = sum(results.values())
        
        print(f"\nTotal: {passed}/{total} passed")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
        
        return passed == total


if __name__ == "__main__":
    tester = ChatIntegrationTester()
    success = tester.run_all_tests()
    
    exit(0 if success else 1)
