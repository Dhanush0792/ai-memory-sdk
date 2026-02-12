"""
Database Migration Script: Memory Contract v1

This script migrates existing AI Memory SDK databases to the Memory Contract v1 schema.

IMPORTANT:
- This migration is ADDITIVE ONLY - no data will be lost
- Existing memories will continue to work
- New fields have sensible defaults
- Run this script BEFORE deploying the updated backend code

Usage:
    python backend/scripts/migrate_to_v1.py
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from backend.api.database import Database


def migrate_to_v1():
    """Migrate database to Memory Contract v1 schema"""
    
    print("\n" + "="*70)
    print("AI MEMORY SDK - MEMORY CONTRACT V1 MIGRATION")
    print("="*70 + "\n")
    
    db = Database()
    
    print("Connecting to database...")
    
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            print("✓ Connected successfully\n")
            
            print("Step 1: Adding new columns to memories table...")
            
            # Add owner_id column (required for tenant isolation)
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS owner_id TEXT;
                """)
                print("  ✓ Added owner_id column")
            except Exception as e:
                print(f"  ⚠ owner_id column may already exist: {e}")
            
            # Add key column
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS key TEXT;
                """)
                print("  ✓ Added key column")
            except Exception as e:
                print(f"  ⚠ key column may already exist: {e}")
            
            # Add value column
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS value JSONB;
                """)
                print("  ✓ Added value column")
            except Exception as e:
                print(f"  ⚠ value column may already exist: {e}")
            
            # Add confidence column
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS confidence REAL DEFAULT 1.0;
                """)
                print("  ✓ Added confidence column (default: 1.0)")
            except Exception as e:
                print(f"  ⚠ confidence column may already exist: {e}")
            
            # Add importance column
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS importance INTEGER;
                """)
                print("  ✓ Added importance column")
            except Exception as e:
                print(f"  ⚠ importance column may already exist: {e}")
            
            # Add updated_at column
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
                """)
                print("  ✓ Added updated_at column")
            except Exception as e:
                print(f"  ⚠ updated_at column may already exist: {e}")
            
            # Add is_deleted column
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
                """)
                print("  ✓ Added is_deleted column (default: FALSE)")
            except Exception as e:
                print(f"  ⚠ is_deleted column may already exist: {e}")
            
            # Add ttl_seconds column
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS ttl_seconds INTEGER;
                """)
                print("  ✓ Added ttl_seconds column")
            except Exception as e:
                print(f"  ⚠ ttl_seconds column may already exist: {e}")
            
            # Add ingestion_mode column
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ADD COLUMN IF NOT EXISTS ingestion_mode TEXT DEFAULT 'explicit';
                """)
                print("  ✓ Added ingestion_mode column (default: 'explicit')")
            except Exception as e:
                print(f"  ⚠ ingestion_mode column may already exist: {e}")
            
            print("\nStep 2: Adding constraints...")
            
            # Add memory_type constraint
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    DROP CONSTRAINT IF EXISTS memories_memory_type_check;
                """)
                cur.execute("""
                    ALTER TABLE memories 
                    ADD CONSTRAINT memories_memory_type_check 
                    CHECK (memory_type IN ('fact', 'preference', 'event', 'system'));
                """)
                print("  ✓ Added memory_type constraint (fact, preference, event, system)")
            except Exception as e:
                print(f"  ⚠ memory_type constraint may already exist: {e}")
            
            # Add confidence constraint
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    DROP CONSTRAINT IF EXISTS memories_confidence_check;
                """)
                cur.execute("""
                    ALTER TABLE memories 
                    ADD CONSTRAINT memories_confidence_check 
                    CHECK (confidence >= 0.0 AND confidence <= 1.0);
                """)
                print("  ✓ Added confidence constraint (0.0-1.0)")
            except Exception as e:
                print(f"  ⚠ confidence constraint may already exist: {e}")
            
            # Add importance constraint
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    DROP CONSTRAINT IF EXISTS memories_importance_check;
                """)
                cur.execute("""
                    ALTER TABLE memories 
                    ADD CONSTRAINT memories_importance_check 
                    CHECK (importance BETWEEN 1 AND 5);
                """)
                print("  ✓ Added importance constraint (1-5)")
            except Exception as e:
                print(f"  ⚠ importance constraint may already exist: {e}")
            
            # Add ingestion_mode constraint
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    DROP CONSTRAINT IF EXISTS memories_ingestion_mode_check;
                """)
                cur.execute("""
                    ALTER TABLE memories 
                    ADD CONSTRAINT memories_ingestion_mode_check 
                    CHECK (ingestion_mode IN ('explicit', 'rules'));
                """)
                print("  ✓ Added ingestion_mode constraint (explicit, rules)")
            except Exception as e:
                print(f"  ⚠ ingestion_mode constraint may already exist: {e}")
            
            print("\nStep 3: Creating indexes...")
            
            # Add indexes for performance
            try:
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_owner_id ON memories(owner_id);
                """)
                print("  ✓ Created index on owner_id")
            except Exception as e:
                print(f"  ⚠ owner_id index may already exist: {e}")
            
            try:
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_is_deleted ON memories(is_deleted);
                """)
                print("  ✓ Created index on is_deleted")
            except Exception as e:
                print(f"  ⚠ is_deleted index may already exist: {e}")
            
            try:
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at ON memories(expires_at);
                """)
                print("  ✓ Created index on expires_at")
            except Exception as e:
                print(f"  ⚠ expires_at index may already exist: {e}")
            
            print("\nStep 4: Backfilling data...")
            
            # Backfill owner_id from user_id (temporary - will be updated by API key context)
            try:
                cur.execute("""
                    UPDATE memories 
                    SET owner_id = user_id 
                    WHERE owner_id IS NULL;
                """)
                updated = cur.rowcount
                print(f"  ✓ Backfilled owner_id for {updated} existing memories")
            except Exception as e:
                print(f"  ⚠ Error backfilling owner_id: {e}")
            
            # Backfill updated_at from created_at
            try:
                cur.execute("""
                    UPDATE memories 
                    SET updated_at = created_at 
                    WHERE updated_at IS NULL;
                """)
                updated = cur.rowcount
                print(f"  ✓ Backfilled updated_at for {updated} existing memories")
            except Exception as e:
                print(f"  ⚠ Error backfilling updated_at: {e}")
            
            # Make owner_id NOT NULL after backfill
            try:
                cur.execute("""
                    ALTER TABLE memories 
                    ALTER COLUMN owner_id SET NOT NULL;
                """)
                print("  ✓ Set owner_id as NOT NULL")
            except Exception as e:
                print(f"  ⚠ Error setting owner_id NOT NULL: {e}")
            
            print("\nStep 5: Committing changes...")
            conn.commit()
            print("  ✓ All changes committed successfully")
    
    print("\n" + "="*70)
    print("MIGRATION COMPLETE!")
    print("="*70)
    print("\nYour database is now ready for Memory Contract v1.")
    print("\nNext steps:")
    print("1. Deploy the updated backend code")
    print("2. Verify API endpoints work correctly")
    print("3. Test the 5-minute quick start guide")
    print("\n")


if __name__ == "__main__":
    try:
        migrate_to_v1()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nPlease check your database connection and try again.")
        sys.exit(1)
