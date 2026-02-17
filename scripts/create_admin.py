import os
import asyncio
import asyncpg
import bcrypt
from dotenv import load_dotenv

load_dotenv()

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def create_admin():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in .env")
        return

    print(f"Connecting to database...")
    if "@" in database_url:
        print(f"Target: {database_url.split('@')[1].split(':')[0]} (check your DATABASE_URL)")
    else:
        print(f"Target: {database_url} (check your DATABASE_URL)")
    
    try:
        # Disable statement cache for PgBouncer transaction mode
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        # --- Schema Migration: Ensure 'role' column exists ---
        print("Checking schema...")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'developer'")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
        
        # --- Create Admin ---
        email = "dhanushsiddilingam@gmail.com"
        password = "Dhanush@2727"
        hashed_password = get_password_hash(password)
        
        # Check if user exists
        user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
        
        if user:
            print(f"User {email} already exists. Updating to admin...")
            await conn.execute("""
                UPDATE users 
                SET password_hash = $1, role = 'admin', is_active = TRUE 
                WHERE email = $2
            """, hashed_password, email)
        else:
            print(f"Creating new admin user {email}...")
            await conn.execute("""
                INSERT INTO users (email, password_hash, role, is_active)
                VALUES ($1, $2, 'admin', TRUE)
            """, email, hashed_password)
            
        print("Admin user created/updated successfully!")
        await conn.close()
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(create_admin())
