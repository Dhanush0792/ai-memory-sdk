from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Initialize Argon2 hasher
ph = PasswordHasher()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (supports both Argon2 and Bcrypt)."""
    try:
        if hashed_password.startswith("$argon2"):
            try:
                ph.verify(hashed_password, plain_password)
                return True
            except VerifyMismatchError:
                return False
        elif hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            # Direct bcrypt verification to avoid passlib bugs
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        return False
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hash a password using Argon2 (default for Phase 2)."""
    return ph.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    # Phase 1: JWT Correctness (exp, iat)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret, 
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt
