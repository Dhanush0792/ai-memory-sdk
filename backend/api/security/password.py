
import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    params = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), params).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
