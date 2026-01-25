"""
Initialize Authentication Database
Sets up users, API keys, and usage tracking tables
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.connection import db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def init_auth_database():
    """Initialize authentication database schema"""
    
    print("=" * 80)
    print("  🔐 Initializing Authentication Database")
    print("=" * 80)
    print()
    
    # Read schema file
    schema_file = project_root / "schema_auth.sql"
    
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False
    
    print(f"📄 Reading schema from: {schema_file}")
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    try:
        print("🔗 Connecting to database...")
        
        # Execute schema
        print("📊 Creating tables...")
        db.execute_write(schema_sql, ())
        
        print()
        print("✅ Authentication database initialized successfully!")
        print()
        print("📋 Created:")
        print("   - users table")
        print("   - api_keys table")
        print("   - api_usage table")
        print("   - tier_limits table")
        print()
        print("🔧 Created functions:")
        print("   - check_rate_limit()")
        print("   - get_user_usage_stats()")
        print()
        print("🎯 Next steps:")
        print("   1. Create a user: python scripts/create_user.py")
        print("   2. Generate API key: Use /api/v1/auth/keys endpoint")
        print("   3. Test authentication: Include X-API-Key header")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_auth_database()
    sys.exit(0 if success else 1)
