"""
Create the memory_db database if it doesn't exist.
This script connects to the default 'postgres' database to create the new database.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from dotenv import load_dotenv

load_dotenv()


def create_database():
    """Create the memory_db database."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not set in environment")
        sys.exit(1)
    
    # Parse the database URL to get connection details
    # Format: postgresql://username:password@localhost:5432/database_name
    try:
        # Extract the base URL without the database name
        parts = database_url.rsplit('/', 1)
        base_url = parts[0]
        db_name = parts[1] if len(parts) > 1 else "memory_db"
        
        # Connect to the default 'postgres' database
        postgres_url = f"{base_url}/postgres"
        
        print(f"🔗 Connecting to PostgreSQL server...")
        print(f"📦 Creating database: {db_name}")
        
        # Connect with autocommit to create database
        with psycopg.connect(postgres_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Check if database exists
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                exists = cur.fetchone()
                
                if exists:
                    print(f"✅ Database '{db_name}' already exists")
                else:
                    # Create the database
                    cur.execute(f'CREATE DATABASE "{db_name}"')
                    print(f"✅ Database '{db_name}' created successfully!")
        
        print("\n✅ Database setup complete!")
        print(f"📝 Next step: Run 'python scripts\\init_db.py' to create tables")
        
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure PostgreSQL is running")
        print("   2. Check your DATABASE_URL in .env file")
        print("   3. Verify PostgreSQL credentials")
        print("   4. Make sure you have permission to create databases")
        sys.exit(1)


if __name__ == "__main__":
    create_database()
