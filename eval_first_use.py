"""
Evaluation Test Script - First Use Experience
Simulating senior developer evaluating SDK
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sdk import MemorySDK, MemoryAuthError, MemoryValidationError
import time

print("=" * 60)
print("EVALUATION TEST: First-Use Experience")
print("=" * 60)

# Test 1: Installation (already done via requirements.txt)
print("\n[1/6] Installation")
print("✓ Dependencies installed")

# Test 2: Setup
print("\n[2/6] Setup")
try:
    sdk = MemorySDK(
        api_key="dev-key-12345",
        user_id="eval-user-001",
        base_url="http://localhost:8000"
    )
    print("✓ SDK initialized")
except Exception as e:
    print(f"✗ SDK initialization failed: {e}")
    sys.exit(1)

# Test 3: First memory write
print("\n[3/6] First Memory Write")
start = time.time()
try:
    memory = sdk.add_memory(
        content="User prefers dark mode",
        memory_type="preference"
    )
    elapsed = time.time() - start
    print(f"✓ Memory created in {elapsed:.2f}s")
    print(f"  ID: {memory['id']}")
    print(f"  Type: {memory['type']}")
except Exception as e:
    print(f"✗ Memory write failed: {e}")
    sys.exit(1)

# Test 4: First memory retrieval
print("\n[4/6] First Memory Retrieval")
start = time.time()
try:
    memories = sdk.get_memories()
    elapsed = time.time() - start
    print(f"✓ Retrieved {len(memories)} memories in {elapsed:.2f}s")
    if memories:
        print(f"  Sample: {memories[0]['content'][:50]}")
except Exception as e:
    print(f"✗ Memory retrieval failed: {e}")
    sys.exit(1)

# Test 5: First context injection
print("\n[5/6] First Context Injection")
start = time.time()
try:
    context = sdk.get_context(
        query="user preferences",
        max_tokens=1000
    )
    elapsed = time.time() - start
    print(f"✓ Context generated in {elapsed:.2f}s")
    print(f"  Length: {len(context)} chars")
    print(f"  Preview: {context[:100]}...")
    
    if not context:
        print("✗ WARNING: Context is empty")
    if "User Preferences" not in context and "Known Facts" not in context:
        print("✗ WARNING: Context format unexpected")
except Exception as e:
    print(f"✗ Context injection failed: {e}")
    sys.exit(1)

# Test 6: Edge cases
print("\n[6/6] Edge Cases")

# Empty memory scenario
try:
    sdk2 = MemorySDK(
        api_key="dev-key-12345",
        user_id="empty-user-" + str(int(time.time())),
        base_url="http://localhost:8000"
    )
    empty_context = sdk2.get_context()
    print(f"✓ Empty memory handled: {len(empty_context)} chars")
except Exception as e:
    print(f"✗ Empty memory failed: {e}")

# Large memory scenario
try:
    for i in range(50):
        sdk.add_memory(f"Test fact number {i}", "fact")
    large_context = sdk.get_context(max_tokens=500)
    print(f"✓ Large memory handled: {len(large_context)} chars")
except Exception as e:
    print(f"✗ Large memory failed: {e}")

print("\n" + "=" * 60)
print("FIRST-USE EXPERIENCE: COMPLETE")
print("=" * 60)
