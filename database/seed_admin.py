import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db
from app.auth.utils import get_password_hash

def seed_admin():
    # Admin Credentials from Environment
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
    
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("❌ Error: ADMIN_EMAIL and ADMIN_PASSWORD environment variables must be set.")
        sys.exit(1)
    
    print(f"Seeding admin user: {ADMIN_EMAIL}")
    
    with db.get_cursor() as cur:
        # Check if admin already exists
        cur.execute("SELECT id FROM users WHERE email = %s", (ADMIN_EMAIL,))
        if cur.fetchone():
            print("✅ Admin user already exists. Skipping.")
            return

        # Hash password
        hashed_password = get_password_hash(ADMIN_PASSWORD)
        
        # Insert admin user
        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name, role, is_active)
            VALUES (%s, %s, %s, 'admin', true)
            RETURNING id
            """,
            (ADMIN_EMAIL, hashed_password, "System Admin")
        )
        user_id = cur.fetchone()["id"]
        print(f"✅ Admin user created successfully with ID: {user_id}")

if __name__ == "__main__":
    try:
        seed_admin()
    except Exception as e:
        print(f"❌ Failed to seed admin: {e}")
        sys.exit(1)
