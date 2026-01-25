"""
Evaluation Test Script - Core Product Usage
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sdk import MemorySDK
from datetime import datetime, timedelta
import time

print("=" * 60)
print("EVALUATION TEST: Core Product Usage")
print("=" * 60)

sdk = MemorySDK(
    api_key="dev-key-12345",
    user_id=f"core-eval-{int(time.time())}",
    base_url="http://localhost:8000"
)

# Test 1: Storing different memory types
print("\n[1/4] Storing Facts, Preferences, Events")
try:
    fact1 = sdk.add_memory("User is a Python developer", "fact")
    fact2 = sdk.add_memory("User works at TechCorp", "fact")
    pref1 = sdk.add_memory("User prefers dark mode", "preference")
    pref2 = sdk.add_memory("User likes concise responses", "preference")
    event1 = sdk.add_memory("User logged in at 9am", "event")
    event2 = sdk.add_memory("User completed onboarding", "event")
    print(f"✓ Created 6 memories (2 facts, 2 prefs, 2 events)")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 2: Retrieving relevant memories
print("\n[2/4] Retrieving Relevant Memories")
try:
    all_memories = sdk.get_memories()
    print(f"✓ All memories: {len(all_memories)}")
    
    facts = sdk.get_memories(memory_type="fact")
    print(f"✓ Facts only: {len(facts)}")
    
    prefs = sdk.get_memories(memory_type="preference")
    print(f"✓ Preferences only: {len(prefs)}")
    
    events = sdk.get_memories(memory_type="event")
    print(f"✓ Events only: {len(events)}")
    
    if len(facts) != 2 or len(prefs) != 2 or len(events) != 2:
        print(f"✗ WARNING: Type filtering incorrect")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 3: Context injection quality
print("\n[3/4] Injecting Context into LLM Prompt")
try:
    # Test with query
    context_with_query = sdk.get_context(
        query="developer preferences",
        max_tokens=1000
    )
    print(f"✓ Context with query: {len(context_with_query)} chars")
    
    # Test without query
    context_no_query = sdk.get_context(max_tokens=1000)
    print(f"✓ Context without query: {len(context_no_query)} chars")
    
    # Test token limiting
    context_limited = sdk.get_context(max_tokens=100)
    print(f"✓ Token-limited context: {len(context_limited)} chars")
    
    # Verify structure
    if "User Preferences" not in context_no_query:
        print("✗ WARNING: Missing 'User Preferences' section")
    if "Known Facts" not in context_no_query:
        print("✗ WARNING: Missing 'Known Facts' section")
    if "Recent Events" not in context_no_query:
        print("✗ WARNING: Missing 'Recent Events' section")
    else:
        print("✓ Context structure validated")
        
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 4: Edge cases
print("\n[4/4] Handling Edge Cases")

# Expired memory
try:
    past_time = datetime.utcnow() - timedelta(hours=1)
    expired = sdk.add_memory(
        "This should be expired",
        "fact",
        expires_at=past_time
    )
    
    context_with_expired = sdk.get_context()
    if "This should be expired" in context_with_expired:
        print("✗ CRITICAL: Expired memory included in context")
    else:
        print("✓ Expired memory correctly filtered")
except Exception as e:
    print(f"✗ Expired memory test failed: {e}")

# Large memory set
try:
    for i in range(100):
        sdk.add_memory(f"Bulk fact {i}", "fact")
    
    large_context = sdk.get_context(max_tokens=500)
    print(f"✓ Large memory set handled: {len(large_context)} chars")
    
    # Verify token limit respected
    if len(large_context) > 3000:  # Rough char estimate for 500 tokens
        print("✗ WARNING: Token limit may not be enforced")
except Exception as e:
    print(f"✗ Large memory test failed: {e}")

# Empty query
try:
    empty_query_context = sdk.get_context(query="")
    print(f"✓ Empty query handled: {len(empty_query_context)} chars")
except Exception as e:
    print(f"✗ Empty query failed: {e}")

print("\n" + "=" * 60)
print("CORE PRODUCT USAGE: COMPLETE")
print("=" * 60)
