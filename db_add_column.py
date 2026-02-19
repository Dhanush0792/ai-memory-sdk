from app.database import db

def add_column():
    db.initialize()
    with db.get_cursor() as cur:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name TEXT;")
        print("Column 'full_name' added successfully")

if __name__ == "__main__":
    add_column()
