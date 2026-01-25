"""SDK Integration Tests"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sdk import MemorySDK, MemoryValidationError
import time

def test_full_workflow():
    """Test complete SDK workflow"""
    
    sdk = MemorySDK(
        api_key="dev-key-12345",
        user_id=f"test-user-{int(time.time())}",
        base_url="http://localhost:8000"
    )
    
    print("✓ SDK initialized")
    
    # Add memories
    fact = sdk.add_memory("User is a software engineer", "fact")
    assert fact["type"] == "fact"
    print("✓ Added fact")
    
    pref = sdk.add_memory("User prefers Python", "preference")
    assert pref["type"] == "preference"
    print("✓ Added preference")
    
    event = sdk.add_memory("User logged in", "event")
    assert event["type"] == "event"
    print("✓ Added event")
    
    # Get memories
    memories = sdk.get_memories()
    assert len(memories) == 3
    print("✓ Retrieved memories")
    
    # Get context (MANDATORY)
    context = sdk.get_context(max_tokens=1000)
    assert len(context) > 0
    assert "User Preferences" in context or "Known Facts" in context
    print("✓ Context injection works")
    
    # Filter by type
    facts = sdk.get_memories(memory_type="fact")
    assert len(facts) == 1
    print("✓ Type filtering works")
    
    # Delete specific memory
    result = sdk.delete_memory(fact["id"])
    assert result["deleted"] == True
    print("✓ Deleted specific memory")
    
    # Export data
    export = sdk.export_user_data()
    assert export["user_id"] == sdk.user_id
    assert len(export["memories"]) == 2  # 3 - 1 deleted
    print("✓ GDPR export works")
    
    # Delete by type
    result = sdk.delete_by_type("preference")
    assert result["deleted_count"] == 1
    print("✓ Delete by type works")
    
    # Hard delete all
    result = sdk.delete_user_data(confirm=True)
    assert result["irreversible"] == True
    print("✓ GDPR hard delete works")
    
    # Verify deletion
    memories = sdk.get_memories()
    assert len(memories) == 0
    print("✓ All data deleted")
    
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    test_full_workflow()
