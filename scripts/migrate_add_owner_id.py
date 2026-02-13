"""
Database Migration Script - Add owner_id column

This script migrates the existing database schema to support the new API key system
by adding the owner_id column to the memories table.

Run this script ONCE before deploying the new version.
"""

import psycopg
import os
import sys

def run_migration():
    """Run database migration to add owner_id column"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print("Connecting to database...")
    try:
        conn = psycopg.connect(database_url)
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)
    
    print("Connected successfully!")
    
    try:
        with conn.cursor() as cur:
            # Check if owner_id column already exists
            print("Checking if owner_id column exists...")
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='memories' AND column_name='owner_id'
            """)
            
            if cur.fetchone():
                print("✅ owner_id column already exists. No migration needed.")
                return
            
            print("Adding owner_id column to memories table...")
            
            # Add owner_id column (nullable first, then we'll populate it)
            cur.execute("""
                ALTER TABLE memories 
                ADD COLUMN IF NOT EXISTS owner_id TEXT
            """)
            
            print("Populating owner_id with user_id values (backward compatibility)...")
            
            # Populate owner_id with user_id for existing records
            # This ensures backward compatibility
            cur.execute("""
                UPDATE memories 
                SET owner_id = user_id 
                WHERE owner_id IS NULL
            """)
            
            print("Making owner_id NOT NULL...")
            
            # Now make it NOT NULL
            cur.execute("""
                ALTER TABLE memories 
                ALTER COLUMN owner_id SET NOT NULL
            """)
            
            print("Creating index on owner_id...")
            
            # Create index for performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_owner_id ON memories(owner_id)
            """)
            
            # Commit the transaction
            conn.commit()
            
            print("✅ Migration completed successfully!")
            print("   - Added owner_id column")
            print("   - Populated with user_id values")
            print("   - Created index for performance")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION: Add owner_id column")
    print("=" * 60)
    print()
    
    run_migration()
    
    print()
    print("=" * 60)
    print("Migration complete! You can now deploy the new version.")
    print("=" * 60)
