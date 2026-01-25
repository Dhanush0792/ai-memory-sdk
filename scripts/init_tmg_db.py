"""
Initialize Temporal Memory Graph Database
Applies the enhanced schema with temporal features and conflict detection.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from dotenv import load_dotenv

load_dotenv()


def init_tmg_database():
    """Initialize Temporal Memory Graph database schema."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not set in environment")
        sys.exit(1)
    
    print(f"🔗 Connecting to database...")
    
    try:
        # Read TMG schema file
        schema_file = Path(__file__).parent.parent / "schema_tmg.sql"
        
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            sys.exit(1)
        
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        # Connect and execute
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                print("📝 Executing Temporal Memory Graph schema...")
                print("   This will:")
                print("   - Drop existing tables (memories, memory_conflicts, memory_changes)")
                print("   - Create enhanced tables with temporal features")
                print("   - Add conflict detection capabilities")
                print("   - Set up versioning and change tracking")
                print("   - Create indexes for performance")
                print("   - Add triggers for automatic logging")
                
                # Execute the schema
                cur.execute(schema_sql)
                conn.commit()
                
                print("\n✅ Temporal Memory Graph schema initialized successfully!")
                
                # Verify table creation
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name IN ('memories', 'memory_conflicts', 'memory_changes')
                    ORDER BY table_name
                """)
                tables = cur.fetchall()
                
                print(f"\n✅ Created {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table[0]}")
                
                # Show some stats
                print("\n📊 Schema Features:")
                print("   ✨ Temporal tracking (created_at, valid_from, valid_until)")
                print("   ✨ Confidence scoring (0-1 scale)")
                print("   ✨ Temporal decay (automatic fading)")
                print("   ✨ Memory versioning (track evolution)")
                print("   ✨ Conflict detection (automatic)")
                print("   ✨ Change history (full audit trail)")
                print("   ✨ Status management (active, superseded, conflicted)")
                
                print("\n🎯 World-First Features Enabled:")
                print("   1. Automatic conflict detection between memories")
                print("   2. Temporal decay like human memory")
                print("   3. Memory versioning and evolution tracking")
                print("   4. Smart conflict resolution strategies")
                print("   5. Complete change audit trail")
                
                print("\n🚀 Next Steps:")
                print("   1. Run the demo: python scripts/demo_temporal_memory.py")
                print("   2. Explore the SDK: app/memory/temporal_sdk.py")
                print("   3. Read the proposal: docs/INNOVATION_PROPOSAL.md")
                
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 70)
    print("  Temporal Memory Graph - Database Initialization")
    print("=" * 70)
    print()
    
    response = input("⚠️  This will DROP existing tables. Continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        init_tmg_database()
    else:
        print("❌ Initialization cancelled")
        sys.exit(0)
