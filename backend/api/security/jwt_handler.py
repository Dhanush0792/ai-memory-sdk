
import os
import time
from typing import Dict, Optional
from jose import jwt, JWTError

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

def create_access_token(user_id: str, email: str, name: str) -> str:
    """Create a new access token."""
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is not set")
        
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": time.time() + (ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode a token."""
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is not set")
        
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload["exp"] < time.time():
            return None
        return payload
    except JWTError:
        return None
