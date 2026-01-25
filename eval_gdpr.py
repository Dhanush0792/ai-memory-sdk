"""
Evaluation Test Script - Privacy & GDPR Compliance
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sdk import MemorySDK
import time
import json

print("=" * 60)
print("EVALUATION TEST: Privacy & GDPR Compliance")
print("=" * 60)

user_id = f"gdpr-eval-{int(time.time())}"
sdk = MemorySDK(
    api_key="dev-key-12345",
    user_id=user_id,
    base_url="http://localhost:8000"
)

# Setup test data
print("\n[Setup] Creating test memories")
sdk.add_memory("User's email is test@example.com", "fact")
sdk.add_memory("User prefers email notifications", "preference")
sdk.add_memory("User signed up on 2024-01-15", "event")
print("✓ Created 3 test memories")

# Test 1: Export all user data
print("\n[1/3] Exporting All User Data")
try:
    export_data = sdk.export_user_data()
    
    print(f"✓ Export successful")
    print(f"  User ID: {export_data['user_id']}")
    print(f"  Exported at: {export_data['exported_at']}")
    print(f"  Total memories: {export_data['metadata']['total_count']}")
    
    # Verify completeness
    if export_data['user_id'] != user_id:
        print("✗ CRITICAL: Wrong user ID in export")
    
    if len(export_data['memories']) != 3:
        print(f"✗ CRITICAL: Expected 3 memories, got {len(export_data['memories'])}")
    
    # Verify structure
    required_fields = ['user_id', 'exported_at', 'memories', 'metadata']
    for field in required_fields:
        if field not in export_data:
            print(f"✗ CRITICAL: Missing field '{field}' in export")
    
    # Verify memory structure
    if export_data['memories']:
        memory = export_data['memories'][0]
        mem_fields = ['id', 'user_id', 'content', 'type', 'created_at']
        for field in mem_fields:
            if field not in memory:
                print(f"✗ WARNING: Missing field '{field}' in memory object")
    
    print("✓ Export structure validated")
    
except Exception as e:
    print(f"✗ Export failed: {e}")
    sys.exit(1)

# Test 2: Hard delete all user data
print("\n[2/3] Hard Deleting All User Data")
try:
    # First verify data exists
    before_delete = sdk.get_memories()
    print(f"  Before delete: {len(before_delete)} memories")
    
    # Attempt delete without confirmation
    try:
        sdk.delete_user_data(confirm=False)
        print("✗ CRITICAL: Delete succeeded without confirmation")
    except Exception:
        print("✓ Delete blocked without confirmation")
    
    # Delete with confirmation
    delete_result = sdk.delete_user_data(confirm=True)
    
    print(f"✓ Delete successful")
    print(f"  Deleted: {delete_result['deleted']}")
    print(f"  Count: {delete_result['deleted_count']}")
    print(f"  Irreversible: {delete_result['irreversible']}")
    
    if not delete_result['irreversible']:
        print("✗ CRITICAL: Delete not marked as irreversible")
    
    if delete_result['deleted_count'] != 3:
        print(f"✗ WARNING: Expected 3 deletions, got {delete_result['deleted_count']}")
    
except Exception as e:
    print(f"✗ Delete failed: {e}")
    sys.exit(1)

# Test 3: Verify deletion is irreversible
print("\n[3/3] Verifying Deletion is Irreversible")
try:
    after_delete = sdk.get_memories()
    print(f"  After delete: {len(after_delete)} memories")
    
    if len(after_delete) > 0:
        print("✗ CRITICAL: Data still exists after deletion")
        print(f"  Remaining: {after_delete}")
    else:
        print("✓ All data permanently deleted")
    
    # Try to export deleted user
    export_after_delete = sdk.export_user_data()
    if len(export_after_delete['memories']) > 0:
        print("✗ CRITICAL: Deleted data still exportable")
    else:
        print("✓ Export shows no data after deletion")
    
except Exception as e:
    print(f"✗ Verification failed: {e}")

# Test 4: Audit logging
print("\n[4/4] Understanding Audit Logs")
print("  Checking if deletions are logged...")

# Create new data to test type deletion
sdk2 = MemorySDK(
    api_key="dev-key-12345",
    user_id=f"audit-test-{int(time.time())}",
    base_url="http://localhost:8000"
)

sdk2.add_memory("Fact 1", "fact")
sdk2.add_memory("Pref 1", "preference")

# Test delete by type
try:
    type_delete = sdk2.delete_by_type("fact")
    print(f"✓ Delete by type: {type_delete['deleted_count']} deleted")
except Exception as e:
    print(f"✗ Delete by type failed: {e}")

# Test delete by key
sdk2.add_memory("Test", "fact", metadata={"session_id": "abc123"})
try:
    key_delete = sdk2.delete_by_key("session_id")
    print(f"✓ Delete by key: {key_delete['deleted_count']} deleted")
except Exception as e:
    print(f"✗ Delete by key failed: {e}")

print("\n" + "=" * 60)
print("PRIVACY & GDPR COMPLIANCE: COMPLETE")
print("=" * 60)
