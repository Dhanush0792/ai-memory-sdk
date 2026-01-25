"""
Example demonstrating automatic memory extraction from user messages.

This shows how the LLM can intelligently extract facts, preferences, and events.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal
from app.core.memory_sdk import MemorySDK
from app.core.llm_client import LLMClient, MemoryExtractor


def main():
    """Demonstrate automatic memory extraction."""
    
    # Create database session
    db = SessionLocal()
    
    # Initialize SDK and LLM
    print("Initializing Memory SDK and LLM client...")
    sdk = MemorySDK(db, enable_embeddings=False)  # Disable embeddings for this demo
    llm = LLMClient(provider="openai")
    extractor = MemoryExtractor(llm)
    
    user_id = "extraction_demo_user"
    
    print("\n=== Automatic Memory Extraction Demo ===\n")
    
    # Test messages
    test_messages = [
        "Hi! I'm Alex and I work as a data scientist at Microsoft.",
        "I prefer detailed explanations and I love using Python and R for analysis.",
        "Just completed a machine learning certification from Stanford yesterday!",
        "What's the weather like today?",  # Should extract nothing
        "I really dislike meetings before 10am, and I'm a vegetarian.",
        "My favorite music is jazz and I play the saxophone on weekends.",
        "I'm planning to move to Seattle next month for a new job.",
    ]
    
    print("Processing user messages...\n")
    
    total_extracted = {"facts": 0, "preferences": 0, "events": 0}
    
    for i, message in enumerate(test_messages, 1):
        print(f"{i}. User: \"{message}\"")
        
        # Extract and store memories
        result = extractor.extract_and_store(user_id, message, sdk)
        
        # Display results
        if result["total_stored"] > 0:
            print(f"   ✓ Extracted {result['total_stored']} memories:")
            
            for fact in result["extracted"]["facts"]:
                print(f"     [FACT] {fact['key']}: {fact['value']}")
                total_extracted["facts"] += 1
            
            for pref in result["extracted"]["preferences"]:
                print(f"     [PREF] {pref['key']}: {pref['value']}")
                total_extracted["preferences"] += 1
            
            for event in result["extracted"]["events"]:
                print(f"     [EVENT] {event['key']}: {event['value']}")
                total_extracted["events"] += 1
        else:
            print("   ⊘ No meaningful memories extracted (small talk/question)")
        
        print()
    
    # Summary
    print("=" * 60)
    print(f"Total Extracted:")
    print(f"  Facts: {total_extracted['facts']}")
    print(f"  Preferences: {total_extracted['preferences']}")
    print(f"  Events: {total_extracted['events']}")
    print(f"  TOTAL: {sum(total_extracted.values())}")
    print()
    
    # Show all stored memories
    print("All stored memories:")
    all_memories = sdk.retrieve_memory(user_id=user_id)
    
    for memory in all_memories:
        mem_type = memory['memory_type'].upper()
        key = memory['key']
        value = memory['value'].get('value', memory['value'])
        print(f"  [{mem_type}] {key}: {value}")
    
    print()
    
    # Format for LLM context
    print("Memory context for LLM:")
    print("-" * 60)
    context = sdk.format_memories_for_llm(user_id)
    print(context)
    print("-" * 60)
    print()
    
    # Cleanup
    print("Cleaning up...")
    deleted = sdk.delete_all_memory(user_id)
    print(f"✓ Deleted {deleted} memories\n")
    
    db.close()
    
    print("=== Demo Complete ===")
    print("\nKey Takeaway:")
    print("The LLM automatically extracts structured memories from natural")
    print("conversation, ignoring small talk and questions. This enables")
    print("AI assistants to remember users across sessions!")


if __name__ == "__main__":
    main()
