
import os
import sys
import psycopg
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def verify_connection():
    print("🔌 Verifying Database Connection...")
    
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ Error: DATABASE_URL not found in environment.")
        print("   Please set it in your .env file or environment variables.")
        sys.exit(1)
        
    print(f"   Target: {database_url.split('@')[-1]}")  # Hide credentials
    
    try:
        with psycopg.connect(database_url) as conn:
            print("✅ Connection Successful!")
            
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                print(f"   DB Version: {version}")
                
                # Check for tables
                cur.execute("""
                    SELECT count(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE';
                """)
                table_count = cur.fetchone()[0]
                print(f"   Table Count: {table_count}")
                
                if table_count > 0:
                    print("✅ Schema appears initialized.")
                else:
                    print("⚠️  Warning: No tables found. Backend should initialize this on startup.")

    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_connection()
