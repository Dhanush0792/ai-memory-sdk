from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from app.database import db
from app.auth.utils import get_password_hash, verify_password, create_access_token
from app.config import settings
from app.observability import logger
import time

# Simple in-memory rate limiter for login
LOGIN_RATE_LIMIT_WINDOW = 60  # seconds
LOGIN_RATE_LIMIT_MAX_REQUESTS = 5
_login_rate_limit_store = {}

def check_login_rate_limit(ip_address: str):
    """Enforce login rate limits per IP."""
    now = time.time()
    
    # Cleanup old entries
    if ip_address in _login_rate_limit_store:
        _login_rate_limit_store[ip_address] = [t for t in _login_rate_limit_store[ip_address] if t > now - LOGIN_RATE_LIMIT_WINDOW]
    
    current_requests = _login_rate_limit_store.get(ip_address, [])
    
    if len(current_requests) >= LOGIN_RATE_LIMIT_MAX_REQUESTS:
        logger.warning("login_rate_limit_exceeded", ip=ip_address)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
        
    current_requests.append(now)
    _login_rate_limit_store[ip_address] = current_requests

router = APIRouter(tags=["Authentication"])

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

@router.post("/auth/login", response_model=Token)
def login(user: UserLogin, request: Request):
    """Authenticate user and return access token."""
    check_login_rate_limit(request.client.host)
    with db.get_cursor() as cur:
        # Fetch user with role and active status
        cur.execute(
            "SELECT id, password_hash, role, is_active FROM users WHERE email = %s", 
            (user.email,)
        )
        db_user = cur.fetchone()
        
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        # Phase 5: Auth Failure Logging
        logger.warning(
            "auth_login_failed", 
            email=user.email, 
            ip=request.client.host,
            timestamp=time.time(),
            reason="invalid_credentials"
        )
        # Add artificial delay to prevent timing attacks
        time.sleep(0.5) 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not db_user["is_active"]:
        # Phase 3 & 5: Disabled User Invalidation & Logging
        logger.warning(
            "auth_login_disabled_user", 
            email=user.email,
            ip=request.client.host,
            timestamp=time.time()
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled. Please contact admin.",
        )

    # Update last_login_at
    with db.get_cursor() as cur:
        cur.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
            (db_user["id"],)
        )
    
    # Generate token with role
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(db_user["id"]),
            "role": db_user["role"]
        }, 
        expires_delta=access_token_expires
    )
    
    logger.info("user_login_success", email=user.email, role=db_user["role"])
    return {"access_token": access_token, "token_type": "bearer", "role": db_user["role"]}
