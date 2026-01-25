"""Demo Chat Application with Memory"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sdk import MemorySDK
from openai import OpenAI

def main():
    """Run demo chat application"""
    
    # Initialize SDK
    sdk = MemorySDK(
        api_key=os.getenv("API_KEY", "dev-key-12345"),
        user_id="demo-user-001",
        base_url="http://localhost:8000"
    )
    
    # Initialize OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("🧠 Secure AI Memory Demo")
    print("=" * 50)
    print("Commands:")
    print("  /remember <fact>     - Add a fact")
    print("  /prefer <preference> - Add a preference")
    print("  /event <event>       - Add an event")
    print("  /export              - Export all data")
    print("  /delete              - Delete all data")
    print("  /quit                - Exit")
    print("=" * 50)
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if not user_input:
            continue
        
        # Commands
        if user_input == "/quit":
            break
        
        elif user_input.startswith("/remember "):
            content = user_input.replace("/remember ", "")
            result = sdk.add_memory(content, "fact")
            print(f"✓ Remembered: {result['id']}")
            continue
        
        elif user_input.startswith("/prefer "):
            content = user_input.replace("/prefer ", "")
            result = sdk.add_memory(content, "preference")
            print(f"✓ Preference saved: {result['id']}")
            continue
        
        elif user_input.startswith("/event "):
            content = user_input.replace("/event ", "")
            result = sdk.add_memory(content, "event")
            print(f"✓ Event logged: {result['id']}")
            continue
        
        elif user_input == "/export":
            data = sdk.export_user_data()
            print(f"\n📦 Export Data:")
            print(f"User ID: {data['user_id']}")
            print(f"Exported at: {data['exported_at']}")
            print(f"Total memories: {data['metadata']['total_count']}")
            for mem in data['memories']:
                print(f"  - [{mem['type']}] {mem['content']}")
            continue
        
        elif user_input == "/delete":
            confirm = input("⚠️  Delete ALL data? Type 'yes' to confirm: ")
            if confirm.lower() == "yes":
                result = sdk.delete_user_data(confirm=True)
                print(f"✓ Deleted {result['deleted_count']} memories (irreversible)")
            else:
                print("Cancelled")
            continue
        
        # Regular chat with memory context
        context = sdk.get_context(query=user_input, max_tokens=1500)
        
        messages = []
        if context:
            messages.append({
                "role": "system",
                "content": f"{context}\n\nYou are a helpful assistant with access to user memory. Use the context above to personalize your responses."
            })
        else:
            messages.append({
                "role": "system",
                "content": "You are a helpful assistant."
            })
        
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Call OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500
        )
        
        assistant_message = response.choices[0].message.content
        print(f"\nAssistant: {assistant_message}")

if __name__ == "__main__":
    main()
