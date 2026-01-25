"""
Example demonstrating semantic search capabilities.

This shows how the Memory SDK uses embeddings for intelligent retrieval.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal
from app.core.memory_sdk import MemorySDK


def main():
    """Demonstrate semantic search with embeddings."""
    
    # Create database session
    db = SessionLocal()
    
    # Initialize SDK with embeddings enabled
    print("Initializing Memory SDK with semantic search...")
    sdk = MemorySDK(db, enable_embeddings=True, embedding_provider="openai")
    
    if not sdk.enable_embeddings:
        print("⚠️  Embeddings not enabled. Make sure OPENAI_API_KEY is set.")
        print("Falling back to keyword search demo.\n")
    
    user_id = "semantic_demo_user"
    
    print("\n=== Semantic Search Demo ===\n")
    
    # 1. Add diverse memories
    print("1. Adding memories about different topics...")
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="preference",
        key="food_preference",
        value="Loves Italian cuisine, especially pasta carbonara and tiramisu"
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="preference",
        key="drink_preference",
        value="Prefers oat milk lattes and herbal tea in the evening"
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="fact",
        key="occupation",
        value="Works as a software engineer specializing in machine learning"
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="fact",
        key="hobbies",
        value="Enjoys hiking, photography, and playing guitar on weekends"
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="event",
        key="recent_trip",
        value="Just returned from a vacation in Japan, loved the food and culture"
    )
    
    sdk.add_memory(
        user_id=user_id,
        memory_type="preference",
        key="music_taste",
        value="Listens to indie rock and jazz, favorite artist is Radiohead"
    )
    
    print("✓ Added 6 memories\n")
    
    # 2. Semantic search examples
    print("2. Testing semantic search...\n")
    
    queries = [
        "What does the user like to eat?",
        "What is their job?",
        "What activities do they enjoy?",
        "Tell me about their recent travels",
        "What kind of music do they like?"
    ]
    
    for query in queries:
        print(f"Query: '{query}'")
        results = sdk.retrieve_memory(user_id=user_id, query=query, limit=2)
        
        if results:
            for i, memory in enumerate(results, 1):
                similarity = memory.get('similarity_score', 'N/A')
                print(f"  {i}. [{memory['memory_type']}] {memory['key']}")
                print(f"     Value: {memory['value']}")
                if similarity != 'N/A':
                    print(f"     Similarity: {similarity}")
        else:
            print("  No results found")
        print()
    
    # 3. Compare with keyword search
    print("3. Comparing semantic vs keyword search...\n")
    
    # Semantic: "What beverages does the user enjoy?"
    print("Semantic query: 'What beverages does the user enjoy?'")
    semantic_results = sdk.retrieve_memory(user_id=user_id, query="What beverages does the user enjoy?", limit=3)
    print(f"  Found {len(semantic_results)} results")
    for mem in semantic_results:
        print(f"  - {mem['key']}: {mem['value'].get('value', mem['value'])}")
    print()
    
    # Keyword: exact match required
    print("Keyword search: key='drink_preference'")
    keyword_results = sdk.retrieve_memory(user_id=user_id, query="drink_preference")
    print(f"  Found {len(keyword_results)} results")
    for mem in keyword_results:
        print(f"  - {mem['key']}: {mem['value'].get('value', mem['value'])}")
    print()
    
    # 4. Get all memories
    print("4. Retrieving all memories...")
    all_memories = sdk.retrieve_memory(user_id=user_id)
    print(f"✓ Total memories: {len(all_memories)}\n")
    
    # 5. Cleanup
    print("5. Cleaning up...")
    deleted = sdk.delete_all_memory(user_id=user_id)
    print(f"✓ Deleted {deleted} memories\n")
    
    db.close()
    
    print("=== Demo Complete ===")
    print("\nKey Takeaway:")
    print("Semantic search understands MEANING, not just keywords.")
    print("'What beverages does the user enjoy?' finds 'drink_preference'")
    print("even though the words don't match exactly!")


if __name__ == "__main__":
    main()
