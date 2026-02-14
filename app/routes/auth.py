from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from app.database import db
from app.auth.utils import get_password_hash, verify_password, create_access_token
from app.config import settings
from app.observability import logger

router = APIRouter(tags=["Authentication"])

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/auth/login", response_model=Token)
def login(user: UserLogin):
    """Authenticate user and return access token."""
    with db.get_cursor() as cur:
        # Fetch user with role and active status
        cur.execute(
            "SELECT id, password_hash, role, is_active FROM users WHERE email = %s", 
            (user.email,)
        )
        db_user = cur.fetchone()
        
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        # Log failure with generic message to avoid enumeration
        logger.warning("user_login_failed", email=user.email) 
        # Add artificial delay to prevent timing attacks (optional but good practice)
        # time.sleep(0.1) 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not db_user["is_active"]:
        logger.warning("user_login_inactive", email=user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
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
    return {"access_token": access_token, "token_type": "bearer"}
