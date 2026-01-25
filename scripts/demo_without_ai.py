"""
Interactive Demo - AI Memory SDK Without API Keys
This demonstrates all functionality that works without AI API calls.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.memory import MemorySDK

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_section(text):
    """Print a section header."""
    print(f"\n📌 {text}")
    print("-" * 60)

def demo_add_memories():
    """Demonstrate adding memories manually."""
    print_section("Adding Memories Manually (No AI Required)")
    
    sdk = MemorySDK()
    
    # Add a fact
    print("\n1️⃣ Adding a fact: User's name is 'Alice'")
    memory_id = sdk.add_memory(
        user_id="alice",
        memory_type="fact",
        key="name",
        value="Alice"
    )
    print(f"   ✅ Memory added with ID: {memory_id}")
    
    # Add a preference
    print("\n2️⃣ Adding a preference: Loves pizza")
    memory_id = sdk.add_memory(
        user_id="alice",
        memory_type="preference",
        key="favorite_food",
        value="pizza"
    )
    print(f"   ✅ Memory added with ID: {memory_id}")
    
    # Add another preference
    print("\n3️⃣ Adding a preference: Dislikes broccoli")
    memory_id = sdk.add_memory(
        user_id="alice",
        memory_type="preference",
        key="disliked_food",
        value="broccoli"
    )
    print(f"   ✅ Memory added with ID: {memory_id}")
    
    # Add an event
    print("\n4️⃣ Adding an event: Visited Paris")
    memory_id = sdk.add_memory(
        user_id="alice",
        memory_type="event",
        key="travel",
        value={"location": "Paris", "year": 2025}
    )
    print(f"   ✅ Memory added with ID: {memory_id}")
    
    # Add context
    print("\n5️⃣ Adding context: Works as a software engineer")
    memory_id = sdk.add_memory(
        user_id="alice",
        memory_type="context",
        key="occupation",
        value="software engineer"
    )
    print(f"   ✅ Memory added with ID: {memory_id}")

def demo_retrieve_memories():
    """Demonstrate retrieving memories."""
    print_section("Retrieving Memories")
    
    sdk = MemorySDK()
    
    # Retrieve all memories
    print("\n1️⃣ Retrieving all memories for 'alice':")
    memories = sdk.retrieve_memory(user_id="alice")
    print(f"   Found {len(memories)} memories:")
    for mem in memories:
        print(f"   - [{mem['type']}] {mem['key']}: {mem['value']}")
    
    # Retrieve by type
    print("\n2️⃣ Retrieving only 'preference' memories:")
    preferences = sdk.retrieve_memory(user_id="alice", memory_type="preference")
    print(f"   Found {len(preferences)} preferences:")
    for mem in preferences:
        print(f"   - {mem['key']}: {mem['value']}")
    
    # Retrieve by key
    print("\n3️⃣ Retrieving memory with key 'name':")
    name_memories = sdk.retrieve_memory(user_id="alice", key="name")
    if name_memories:
        print(f"   - {name_memories[0]['value']}")

def demo_memory_stats():
    """Demonstrate memory statistics."""
    print_section("Memory Statistics")
    
    sdk = MemorySDK()
    
    stats = sdk.get_memory_stats(user_id="alice")
    print(f"\n📊 Statistics for 'alice':")
    print(f"   Total memories: {stats['total']}")
    print(f"   Memory types breakdown:")
    for mem_type, count in stats['by_type'].items():
        print(f"   - {mem_type}: {count}")

def demo_delete_specific():
    """Demonstrate deleting specific memories."""
    print_section("Deleting Specific Memories")
    
    sdk = MemorySDK()
    
    # Find and delete memories with specific key
    print("\n1️⃣ Finding memories with key 'disliked_food':")
    to_delete = sdk.retrieve_memory(user_id="alice", key="disliked_food")
    print(f"   Found {len(to_delete)} memory(ies) to delete")
    
    # Delete each one
    deleted_count = 0
    for mem in to_delete:
        if sdk.delete_memory(mem['id']):
            deleted_count += 1
    print(f"   ✅ Deleted {deleted_count} memory(ies)")
    
    # Verify deletion
    remaining = sdk.retrieve_memory(user_id="alice")
    print(f"\n2️⃣ Remaining memories: {len(remaining)}")
    for mem in remaining:
        print(f"   - [{mem['type']}] {mem['key']}: {mem['value']}")

def demo_add_another_user():
    """Demonstrate multi-user support."""
    print_section("Multi-User Support")
    
    sdk = MemorySDK()
    
    print("\n1️⃣ Adding memories for user 'bob':")
    sdk.add_memory(user_id="bob", memory_type="fact", key="name", value="Bob")
    sdk.add_memory(user_id="bob", memory_type="preference", key="hobby", value="gaming")
    print("   ✅ Memories added for Bob")
    
    print("\n2️⃣ Comparing memory counts:")
    alice_count = sdk.get_memory_stats(user_id="alice")['total']
    bob_count = sdk.get_memory_stats(user_id="bob")['total']
    print(f"   - Alice has {alice_count} memories")
    print(f"   - Bob has {bob_count} memories")

def demo_cleanup():
    """Clean up demo data."""
    print_section("Cleanup")
    
    sdk = MemorySDK()
    
    print("\n🧹 Cleaning up demo data...")
    alice_deleted = sdk.delete_all_memory(user_id="alice")
    bob_deleted = sdk.delete_all_memory(user_id="bob")
    
    print(f"   ✅ Deleted {alice_deleted} memories for Alice")
    print(f"   ✅ Deleted {bob_deleted} memories for Bob")

def main():
    """Run the complete demo."""
    print_header("🧠 AI Memory SDK - Interactive Demo (No API Keys)")
    
    print("\n💡 This demo shows all features that work WITHOUT AI API keys:")
    print("   ✅ Manual memory storage")
    print("   ✅ Memory retrieval (all, by type, by key)")
    print("   ✅ Memory statistics")
    print("   ✅ Memory deletion")
    print("   ✅ Multi-user support")
    
    try:
        # Run all demos
        demo_add_memories()
        demo_retrieve_memories()
        demo_memory_stats()
        demo_delete_specific()
        demo_add_another_user()
        demo_cleanup()
        
        print_header("✅ Demo Complete!")
        
        print("\n📝 What you learned:")
        print("   1. How to add memories manually using the SDK")
        print("   2. How to retrieve memories with filters")
        print("   3. How to get memory statistics")
        print("   4. How to delete specific or all memories")
        print("   5. How the system supports multiple users")
        
        print("\n🚀 Next Steps:")
        print("   - Explore the API at: http://localhost:8000/docs")
        print("   - Try the REST API with curl (see CURL_TESTS.md)")
        print("   - Add an API key later to enable AI features")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
