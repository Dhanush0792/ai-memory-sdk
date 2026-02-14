from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from app.database import db
from app.auth.utils import get_password_hash, verify_password, create_access_token
from app.config import settings
from app.observability import logger

router = APIRouter(tags=["Authentication"])

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/auth/signup", response_model=Token)
def signup(user: UserSignup):
    """Register a new user and return access token."""
    with db.get_cursor() as cur:
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password and insert user
        hashed_password = get_password_hash(user.password)
        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user.email, hashed_password, user.full_name)
        )
        user_id = cur.fetchone()["id"]
        
    # Generate token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user_id)}, expires_delta=access_token_expires
    )
    
    logger.info("user_signup_success", email=user.email)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login", response_model=Token)
def login(user: UserLogin):
    """Authenticate user and return access token."""
    with db.get_cursor() as cur:
        cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (user.email,))
        db_user = cur.fetchone()
        
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        logger.warning("user_login_failed", email=user.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(db_user["id"])}, expires_delta=access_token_expires
    )
    
    logger.info("user_login_success", email=user.email)
    return {"access_token": access_token, "token_type": "bearer"}
