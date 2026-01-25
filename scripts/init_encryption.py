"""
Initialize Encryption Schema
Adds encryption support to the database
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.connection import db
from app.security import get_encryption
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def init_encryption_schema():
    """Initialize encryption schema"""
    
    print("=" * 80)
    print("  🔐 Initializing Encryption Schema")
    print("=" * 80)
    print()
    
    # Read schema file
    schema_file = project_root / "schema_encryption.sql"
    
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False
    
    print(f"📄 Reading schema from: {schema_file}")
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    try:
        print("🔗 Connecting to database...")
        
        # Execute schema
        print("📊 Adding encryption columns...")
        db.execute_write(schema_sql, ())
        
        print()
        print("✅ Encryption schema initialized successfully!")
        print()
        print("📋 Added:")
        print("   - is_encrypted column")
        print("   - encrypted_value column")
        print("   - encryption_version column")
        print("   - encryption_keys table")
        print()
        print("🔧 Created functions:")
        print("   - count_encrypted_memories()")
        print("   - get_encryption_stats()")
        print()
        
        # Check for encryption key
        print("🔑 Checking encryption key...")
        encryption = get_encryption()
        
        print()
        print("✅ Encryption key loaded successfully!")
        print()
        print("⚠️  IMPORTANT: Make sure ENCRYPTION_KEY is set in your .env file")
        print("   Without it, encrypted data cannot be decrypted!")
        print()
        print("🎯 Next steps:")
        print("   1. Test encryption: python scripts/test_encryption.py")
        print("   2. Encrypt existing data: python scripts/encrypt_existing_data.py")
        print("   3. Use encrypt_value=True when adding memories")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing schema: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_encryption_schema()
    sys.exit(0 if success else 1)
