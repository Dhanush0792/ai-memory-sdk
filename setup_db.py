"""Database Setup Script - Fresh Schema"""

import psycopg
import os

def setup_database():
    """Setup PostgreSQL database - drop and recreate"""
    
    try:
        # Connect to postgres database
        conn_string = "postgresql://postgres:postgres@localhost:5432/postgres"
        print(f"Connecting to PostgreSQL...")
        
        with psycopg.connect(conn_string, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Drop existing database
                print("Dropping existing database...")
                cur.execute("DROP DATABASE IF EXISTS memory_db")
                
                # Create fresh database
                print("Creating memory_db database...")
                cur.execute("CREATE DATABASE memory_db")
                print("✓ Database created")
        
        # Connect to memory_db and create schema
        conn_string = "postgresql://postgres:postgres@localhost:5432/memory_db"
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                print("Creating schema...")
                cur.execute("""
                    CREATE TABLE memories (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP
                    );
                    
                    CREATE INDEX idx_user_id ON memories(user_id);
                    CREATE INDEX idx_type ON memories(memory_type);
                    
                    CREATE TABLE audit_logs (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource_id TEXT,
                        timestamp TIMESTAMP DEFAULT NOW(),
                        metadata JSONB DEFAULT '{}'
                    );
                """)
                conn.commit()
                print("✓ Schema created")
        
        print("\n✅ Database setup complete!")
        return True
        
    except psycopg.OperationalError as e:
        print(f"\n❌ PostgreSQL connection failed: {e}")
        print("\nPlease ensure PostgreSQL is installed and running:")
        print("  - Windows: Download from https://www.postgresql.org/download/windows/")
        print("  - Default credentials: postgres/postgres")
        return False

if __name__ == "__main__":
    setup_database()
