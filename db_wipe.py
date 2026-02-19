from app.database import db

def wipe_users():
    db.initialize()
    with db.get_cursor() as cur:
        cur.execute("DELETE FROM users")
        print("Users deleted successfully")

if __name__ == "__main__":
    wipe_users()
