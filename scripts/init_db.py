"""
Database initialization script.
Creates schema and tables.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from dotenv import load_dotenv

load_dotenv()


def init_database():
    """Initialize database schema."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not set in environment")
        sys.exit(1)
    
    print(f"🔗 Connecting to database...")
    
    try:
        # Read schema file
        schema_file = Path(__file__).parent.parent / "schema.sql"
        
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            sys.exit(1)
        
        with open(schema_file, "r") as f:
            schema_sql = f.read()
        
        # Connect and execute
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                print("📝 Executing schema...")
                cur.execute(schema_sql)
                conn.commit()
                print("✅ Database schema initialized successfully!")
                
                # Verify table creation
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'memories'
                """)
                count = cur.fetchone()[0]
                
                if count > 0:
                    print("✅ Table 'memories' created successfully")
                else:
                    print("⚠️  Warning: Table 'memories' not found")
    
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_database()
