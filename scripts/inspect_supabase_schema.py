import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def inspect_schema():
    database_url = os.getenv("DATABASE_URL")
    print(f"Connecting to: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    
    try:
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        tables = ['users', 'memories', 'audit_logs', 'admin_audit_logs']
        
        for table in tables:
            print(f"\n--- Table: {table} ---")
            exists = await conn.fetchval(f"SELECT exists (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            if not exists:
                print("Does not exist.")
                continue
                
            columns = await conn.fetch(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)
            for col in columns:
                print(f"{col['column_name']}: {col['data_type']} (Null: {col['is_nullable']}, Default: {col['column_default']})")
        
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
