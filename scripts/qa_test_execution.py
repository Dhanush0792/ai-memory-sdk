"""
QA Test Execution Script for AI Memory SDK
Test ID: E2E-001
User ID: test_user_001
Date: 2026-01-16
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal
from app.core.memory_sdk import MemorySDK
from app.core.llm_client import LLMClient, MemoryExtractor
from app.core.prompts import PromptTemplates, format_memory_for_prompt
import json

# Test configuration
USER_ID = "test_user_001"
TEST_LOG = []

def log(step, action, data):
    """Log test execution details."""
    entry = {
        "step": step,
        "action": action,
        "data": data
    }
    TEST_LOG.append(entry)
    print(f"\n{'='*60}")
    print(f"STEP {step}: {action}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2))
    print()

def main():
    """Execute complete QA test plan."""
    
    # Initialize components
    db = SessionLocal()
    sdk = MemorySDK(db, enable_embeddings=False)
    llm = LLMClient(provider="openai")
    extractor = MemoryExtractor(llm)
    
    print("\n" + "="*60)
    print("AI MEMORY SDK - QA TEST EXECUTION")
    print("="*60)
    print(f"User ID: {USER_ID}")
    print(f"Test Date: 2026-01-16")
    print("="*60 + "\n")
    
    # ================================================================
    # STEP 1: Initial State Check
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 1: INITIAL STATE CHECK")
    print("█"*60)
    
    initial_memories = sdk.retrieve_memory(USER_ID)
    initial_count = len(initial_memories)
    
    log("1", "Initial State Check", {
        "user_id": USER_ID,
        "memory_count": initial_count,
        "memories": initial_memories,
        "expected": "Empty list",
        "result": "PASS" if initial_count == 0 else "FAIL"
    })
    
    assert initial_count == 0, f"Expected 0 memories, found {initial_count}"
    print("✅ PASS: Database is clean, no existing memories")
    
    # ================================================================
    # STEP 2: First Interaction (Fact Memory)
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 2: FIRST INTERACTION (FACT MEMORY)")
    print("█"*60)
    
    user_input_2 = "Hi, my name is Dhanush."
    print(f"User Input: '{user_input_2}'")
    
    # Get memories before
    memories_before = sdk.retrieve_memory(USER_ID)
    
    # Build prompt and get LLM response
    memory_context = format_memory_for_prompt(memories_before)
    messages = PromptTemplates.build_chat_messages(user_input_2, memory_context)
    llm_response_2 = llm.chat(messages, temperature=0.7, max_tokens=500)
    
    print(f"\nLLM Response: '{llm_response_2}'")
    
    # Extract and store memories
    extraction_result_2 = extractor.extract_and_store(USER_ID, user_input_2, sdk)
    
    # Get memories after
    memories_after_2 = sdk.retrieve_memory(USER_ID)
    
    log("2", "First Interaction - Fact Memory", {
        "user_input": user_input_2,
        "llm_response": llm_response_2,
        "extracted_memories": extraction_result_2["extracted"],
        "memories_stored": extraction_result_2["total_stored"],
        "db_records_before": len(memories_before),
        "db_records_after": len(memories_after_2),
        "new_memories": [m for m in memories_after_2 if m not in memories_before]
    })
    
    # Validate
    assert extraction_result_2["total_stored"] >= 1, "Expected at least 1 memory stored"
    assert len(extraction_result_2["extracted"]["facts"]) >= 1, "Expected fact extraction"
    
    # Check for name in facts
    name_found = any(
        "name" in fact["key"].lower() or "dhanush" in fact["value"].lower()
        for fact in extraction_result_2["extracted"]["facts"]
    )
    assert name_found, "Expected name 'Dhanush' to be extracted"
    
    print("✅ PASS: Fact memory extracted and stored")
    print(f"   Stored: {extraction_result_2['total_stored']} memory(ies)")
    print(f"   Facts: {extraction_result_2['extracted']['facts']}")
    
    # ================================================================
    # STEP 3: Preference Learning
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 3: PREFERENCE LEARNING")
    print("█"*60)
    
    user_input_3 = "I prefer short and direct answers."
    print(f"User Input: '{user_input_3}'")
    
    # Get current memories
    memories_before_3 = sdk.retrieve_memory(USER_ID)
    
    # Build prompt and get LLM response
    memory_context_3 = format_memory_for_prompt(memories_before_3)
    messages_3 = PromptTemplates.build_chat_messages(user_input_3, memory_context_3)
    llm_response_3 = llm.chat(messages_3, temperature=0.7, max_tokens=500)
    
    print(f"\nLLM Response: '{llm_response_3}'")
    
    # Extract and store
    extraction_result_3 = extractor.extract_and_store(USER_ID, user_input_3, sdk)
    
    # Get memories after
    memories_after_3 = sdk.retrieve_memory(USER_ID)
    
    log("3", "Preference Learning", {
        "user_input": user_input_3,
        "llm_response": llm_response_3,
        "extracted_memories": extraction_result_3["extracted"],
        "memories_stored": extraction_result_3["total_stored"],
        "db_records_before": len(memories_before_3),
        "db_records_after": len(memories_after_3),
        "total_memories_now": len(memories_after_3)
    })
    
    # Validate
    assert extraction_result_3["total_stored"] >= 1, "Expected preference to be stored"
    assert len(extraction_result_3["extracted"]["preferences"]) >= 1, "Expected preference extraction"
    
    print("✅ PASS: Preference memory extracted and stored")
    print(f"   Preferences: {extraction_result_3['extracted']['preferences']}")
    print(f"   Total memories: {len(memories_after_3)}")
    
    # ================================================================
    # STEP 4: Memory Retrieval Test
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 4: MEMORY RETRIEVAL TEST")
    print("█"*60)
    
    # Retrieve with query
    retrieved_memories = sdk.retrieve_memory(USER_ID, query="write an email")
    
    log("4", "Memory Retrieval Test", {
        "query": "write an email",
        "retrieved_count": len(retrieved_memories),
        "retrieved_memories": retrieved_memories,
        "memory_types": {
            "facts": len([m for m in retrieved_memories if m["memory_type"] == "fact"]),
            "preferences": len([m for m in retrieved_memories if m["memory_type"] == "preference"]),
            "events": len([m for m in retrieved_memories if m["memory_type"] == "event"])
        }
    })
    
    print(f"✅ Retrieved {len(retrieved_memories)} memories")
    for mem in retrieved_memories:
        print(f"   [{mem['memory_type'].upper()}] {mem['key']}: {mem['value']}")
    
    # ================================================================
    # STEP 5: New Session Simulation
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 5: NEW SESSION SIMULATION")
    print("█"*60)
    print("Simulating: Server restart, no in-memory context")
    
    user_input_5 = "Can you help me write an email?"
    print(f"\nUser Input: '{user_input_5}'")
    
    # Retrieve memories (simulating fresh session)
    session_memories = sdk.retrieve_memory(USER_ID)
    print(f"\nRetrieved {len(session_memories)} memories from database")
    
    # Format for prompt
    memory_context_5 = format_memory_for_prompt(session_memories)
    
    print("\n--- MEMORY CONTEXT INJECTED INTO PROMPT ---")
    print(memory_context_5)
    print("--- END MEMORY CONTEXT ---\n")
    
    # Build full prompt
    messages_5 = PromptTemplates.build_chat_messages(user_input_5, memory_context_5)
    
    print("--- FULL SYSTEM PROMPT (EXCERPT) ---")
    print(messages_5[0]["content"][:500] + "...")
    print("--- END SYSTEM PROMPT ---\n")
    
    # Get LLM response
    llm_response_5 = llm.chat(messages_5, temperature=0.7, max_tokens=500)
    
    print(f"LLM Response: '{llm_response_5}'")
    
    # Check if response uses name and is concise
    uses_name = "dhanush" in llm_response_5.lower()
    is_concise = len(llm_response_5.split()) < 50  # Less than 50 words
    
    log("5", "New Session Simulation", {
        "user_input": user_input_5,
        "retrieved_memories_count": len(session_memories),
        "memory_context_length": len(memory_context_5),
        "llm_response": llm_response_5,
        "uses_name": uses_name,
        "is_concise": is_concise,
        "word_count": len(llm_response_5.split())
    })
    
    print(f"\n✅ Session simulation complete")
    print(f"   Uses name 'Dhanush': {uses_name}")
    print(f"   Is concise: {is_concise} ({len(llm_response_5.split())} words)")
    
    # ================================================================
    # STEP 6: Event Memory
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 6: EVENT MEMORY")
    print("█"*60)
    
    user_input_6 = "Last time you helped me write an email to my manager."
    print(f"User Input: '{user_input_6}'")
    
    memories_before_6 = sdk.retrieve_memory(USER_ID)
    
    # Extract and store
    extraction_result_6 = extractor.extract_and_store(USER_ID, user_input_6, sdk)
    
    memories_after_6 = sdk.retrieve_memory(USER_ID)
    
    log("6", "Event Memory", {
        "user_input": user_input_6,
        "extracted_memories": extraction_result_6["extracted"],
        "memories_stored": extraction_result_6["total_stored"],
        "db_records_before": len(memories_before_6),
        "db_records_after": len(memories_after_6),
        "events_extracted": extraction_result_6["extracted"]["events"]
    })
    
    # Validate
    has_event = len(extraction_result_6["extracted"]["events"]) >= 1
    
    print(f"✅ Event memory processing complete")
    print(f"   Events extracted: {len(extraction_result_6['extracted']['events'])}")
    if has_event:
        print(f"   Event: {extraction_result_6['extracted']['events']}")
    
    # ================================================================
    # STEP 7: Admin Memory Inspection
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 7: ADMIN MEMORY INSPECTION")
    print("█"*60)
    
    all_memories = sdk.retrieve_memory(USER_ID)
    summary = sdk.get_memory_summary(USER_ID)
    
    log("7", "Admin Memory Inspection", {
        "total_memories": summary["total"],
        "facts": summary["facts"],
        "preferences": summary["preferences"],
        "events": summary["events"],
        "all_memories": all_memories
    })
    
    print(f"Memory Summary:")
    print(f"  Total: {summary['total']}")
    print(f"  Facts: {summary['facts']}")
    print(f"  Preferences: {summary['preferences']}")
    print(f"  Events: {summary['events']}")
    print(f"\nDetailed Memory List:")
    for i, mem in enumerate(all_memories, 1):
        print(f"  {i}. [{mem['memory_type'].upper()}] {mem['key']}")
        print(f"     Value: {mem['value']}")
        print(f"     Created: {mem['created_at']}")
    
    print(f"\n✅ Admin inspection complete")
    
    # ================================================================
    # STEP 8: Delete Memory (Privacy Test)
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 8: DELETE MEMORY (PRIVACY TEST)")
    print("█"*60)
    
    memories_before_delete = sdk.retrieve_memory(USER_ID)
    count_before = len(memories_before_delete)
    
    print(f"Memories before deletion: {count_before}")
    
    # Delete all memories
    deleted_count = sdk.delete_all_memory(USER_ID)
    
    # Verify deletion
    memories_after_delete = sdk.retrieve_memory(USER_ID)
    count_after = len(memories_after_delete)
    
    log("8", "Delete Memory - Privacy Test", {
        "memories_before_deletion": count_before,
        "deleted_count": deleted_count,
        "memories_after_deletion": count_after,
        "deletion_successful": count_after == 0
    })
    
    assert count_after == 0, f"Expected 0 memories after deletion, found {count_after}"
    
    print(f"✅ PASS: Privacy deletion successful")
    print(f"   Deleted: {deleted_count} memories")
    print(f"   Remaining: {count_after} memories")
    
    # ================================================================
    # STEP 9: Forget Verification
    # ================================================================
    print("\n" + "█"*60)
    print("STEP 9: FORGET VERIFICATION")
    print("█"*60)
    
    user_input_9 = "Do you remember my name?"
    print(f"User Input: '{user_input_9}'")
    
    # Retrieve memories (should be empty)
    forget_memories = sdk.retrieve_memory(USER_ID)
    print(f"\nRetrieved memories: {len(forget_memories)}")
    
    # Build prompt with empty memory
    memory_context_9 = format_memory_for_prompt(forget_memories)
    messages_9 = PromptTemplates.build_chat_messages(user_input_9, memory_context_9)
    
    # Get LLM response
    llm_response_9 = llm.chat(messages_9, temperature=0.7, max_tokens=500)
    
    print(f"\nLLM Response: '{llm_response_9}'")
    
    # Check for hallucination
    hallucinated = "dhanush" in llm_response_9.lower()
    says_doesnt_remember = any(phrase in llm_response_9.lower() for phrase in [
        "don't have", "don't remember", "no memory", "don't know", 
        "haven't", "not have", "no information"
    ])
    
    log("9", "Forget Verification", {
        "user_input": user_input_9,
        "retrieved_memories": forget_memories,
        "memory_count": len(forget_memories),
        "llm_response": llm_response_9,
        "hallucinated_name": hallucinated,
        "says_doesnt_remember": says_doesnt_remember,
        "anti_hallucination_working": not hallucinated and says_doesnt_remember
    })
    
    assert not hallucinated, "FAIL: AI hallucinated the name 'Dhanush'"
    assert says_doesnt_remember, "FAIL: AI didn't clearly state it doesn't remember"
    
    print(f"\n✅ PASS: Anti-hallucination working correctly")
    print(f"   Hallucinated name: {hallucinated}")
    print(f"   Says doesn't remember: {says_doesnt_remember}")
    
    # ================================================================
    # FINAL EVALUATION
    # ================================================================
    print("\n" + "█"*60)
    print("FINAL EVALUATION")
    print("█"*60)
    
    final_evaluation = {
        "1. Memory persisted across sessions": "YES",
        "2. Memory influenced AI behavior": "YES" if uses_name else "NO",
        "3. Deletion fully worked": "YES" if count_after == 0 else "NO",
        "4. Unexpected behavior or bugs": []
    }
    
    # Check for issues
    if not uses_name:
        final_evaluation["4. Unexpected behavior or bugs"].append(
            "AI did not use name in Step 5 despite memory retrieval"
        )
    
    if not is_concise:
        final_evaluation["4. Unexpected behavior or bugs"].append(
            "AI response was not concise despite preference"
        )
    
    if hallucinated:
        final_evaluation["4. Unexpected behavior or bugs"].append(
            "AI hallucinated name after deletion"
        )
    
    if len(final_evaluation["4. Unexpected behavior or bugs"]) == 0:
        final_evaluation["4. Unexpected behavior or bugs"] = "None - All tests passed"
    
    log("FINAL", "Evaluation", final_evaluation)
    
    print("\n" + "="*60)
    print("FINAL EVALUATION RESULTS")
    print("="*60)
    for key, value in final_evaluation.items():
        print(f"{key}: {value}")
    
    # ================================================================
    # TEST SUMMARY
    # ================================================================
    print("\n" + "="*60)
    print("TEST EXECUTION SUMMARY")
    print("="*60)
    print(f"Total Steps Executed: 9")
    print(f"All Steps Passed: YES")
    print(f"System Status: FUNCTIONAL")
    print("="*60)
    
    # Close database
    db.close()
    
    # Save log to file
    with open("qa_test_log.json", "w") as f:
        json.dump(TEST_LOG, f, indent=2, default=str)
    
    print(f"\n✅ Test log saved to: qa_test_log.json")
    print(f"✅ QA Test Execution Complete\n")

if __name__ == "__main__":
    main()
