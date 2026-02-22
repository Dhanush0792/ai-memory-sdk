import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def update_schema():
    database_url = os.getenv("DATABASE_URL")
    print(f"Connecting to: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    
    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        # 1. Ensure 'memories' has 'tenant_id'
        print("Checking 'memories' table columns...")
        await conn.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255) DEFAULT 'default'")
        
        # 2. Ensure 'admin_audit_logs' exists
        print("Checking 'admin_audit_logs' table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                admin_id UUID NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                target_user_id UUID,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            )
        """)
        
        # 3. Ensure 'audit_logs' has consistent schema
        print("Ensuring 'audit_logs' consistsency...")
        await conn.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255)")
        await conn.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_id VARCHAR(255)")
        
        print("Schema updated successfully!")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(update_schema())
