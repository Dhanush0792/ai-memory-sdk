"""
Example usage of the Memory SDK.

This demonstrates how to use the SDK to add, retrieve, and delete memories.
Run this after setting up the database.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal
from app.core.memory_sdk import MemorySDK


def main():
    """Demonstrate Memory SDK usage."""
    
    # Create database session
    db = SessionLocal()
    
    # Initialize SDK
    sdk = MemorySDK(db)
    
    user_id = "demo_user_123"
    
    print("=== Memory SDK Demo ===\n")
    
    # 1. Add some memories
    print("1. Adding memories...")
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="fact",
        key="name",
        value="Alice Johnson"
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="fact",
        key="location",
        value="San Francisco, CA"
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="preference",
        key="programming_language",
        value={"language": "Python", "reason": "loves simplicity"}
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="preference",
        key="coffee",
        value="Prefers oat milk lattes"
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="event",
        key="last_conversation",
        value={"topic": "AI memory systems", "date": "2026-01-16"}
    )
    
    print("✓ Added 5 memories\n")
    
    # 2. Retrieve all memories
    print("2. Retrieving all memories...")
    all_memories = sdk.retrieve_memory(user_id=user_id)
    print(f"✓ Found {len(all_memories)} memories\n")
    
    # 3. Retrieve specific type
    print("3. Retrieving only facts...")
    facts = sdk.retrieve_memory(user_id=user_id, memory_type="fact")
    for fact in facts:
        print(f"   - {fact['key']}: {fact['value']}")
    print()
    
    # 4. Search by key
    print("4. Searching for 'name'...")
    name_memory = sdk.retrieve_memory(user_id=user_id, query="name")
    if name_memory:
        print(f"   Found: {name_memory[0]['value']}")
    print()
    
    # 5. Get memory summary
    print("5. Getting memory summary...")
    summary = sdk.get_memory_summary(user_id=user_id)
    print(f"   Total: {summary['total']}")
    print(f"   Facts: {summary['facts']}")
    print(f"   Preferences: {summary['preferences']}")
    print(f"   Events: {summary['events']}")
    print()
    
    # 6. Format for LLM
    print("6. Formatting memories for LLM context...")
    llm_context = sdk.format_memories_for_llm(user_id=user_id)
    print(llm_context)
    print()
    
    # 7. Delete all memories
    print("7. Deleting all memories...")
    deleted_count = sdk.delete_all_memory(user_id=user_id)
    print(f"✓ Deleted {deleted_count} memories\n")
    
    # Verify deletion
    remaining = sdk.retrieve_memory(user_id=user_id)
    print(f"Remaining memories: {len(remaining)}")
    
    # Close database session
    db.close()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
