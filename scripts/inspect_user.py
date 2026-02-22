import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def inspect_user():
    database_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(database_url, statement_cache_size=0)
    
    email = "dhanushsiddilingam@gmail.com"
    row = await conn.fetchrow("SELECT id, email, password_hash, role, is_active FROM users WHERE email = $1", email)
    
    if row:
        print(f"User found: {row['email']}")
        print(f"Role: {row['role']}")
        print(f"Is Active: {row['is_active']}")
        print(f"Hash starts with: {row['password_hash'][:10]}...")
        print(f"Hash length: {len(row['password_hash'])}")
    else:
        print("User not found!")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(inspect_user())
