"""
Create User and Generate API Key
Helper script for user management
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.auth import user_manager, api_key_manager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_user_with_key():
    """Interactive script to create user and generate API key"""
    
    print("=" * 80)
    print("  👤 Create User & Generate API Key")
    print("=" * 80)
    print()
    
    # Get user input
    email = input("Email: ").strip()
    name = input("Name: ").strip()
    
    print()
    print("Tier options:")
    print("  1. free (10K memories/month, 100 requests/hour)")
    print("  2. pro (1M memories/month, 10K requests/hour)")
    print("  3. enterprise (unlimited)")
    
    tier_choice = input("Choose tier (1-3): ").strip()
    tier_map = {"1": "free", "2": "pro", "3": "enterprise"}
    tier = tier_map.get(tier_choice, "free")
    
    print()
    print(f"Creating user: {name} ({email}) - {tier} tier")
    
    try:
        # Create user
        user = user_manager.create_user(
            email=email,
            name=name,
            tier=tier
        )
        
        print(f"✅ User created: {user['id']}")
        print()
        
        # Generate API key
        print("Generating API key...")
        api_key = api_key_manager.generate_api_key(
            user_id=user['id'],
            name="Default Key"
        )
        
        print()
        print("=" * 80)
        print("  🔑 API KEY GENERATED")
        print("=" * 80)
        print()
        print(f"  {api_key}")
        print()
        print("⚠️  IMPORTANT: Save this API key! It won't be shown again.")
        print()
        print("=" * 80)
        print()
        print("📋 User Details:")
        print(f"   ID: {user['id']}")
        print(f"   Email: {user['email']}")
        print(f"   Name: {user['name']}")
        print(f"   Tier: {user['tier']}")
        print()
        print("🧪 Test your API key:")
        print(f'   curl -H "X-API-Key: {api_key}" http://localhost:8000/api/v1/auth/me')
        print()
        
        return True
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_user_with_key()
    sys.exit(0 if success else 1)
