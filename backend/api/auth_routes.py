
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
from datetime import datetime

from .database import Database
from .security.password import hash_password, verify_password
from .security.jwt_handler import create_access_token

router = APIRouter()
db = Database()

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/signup", response_model=Token)
async def signup(user_data: UserSignup):
    """Register a new user"""
    # Check if user exists
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create user
            hashed_password = hash_password(user_data.password)
            user_id = str(uuid.uuid4())
            
            cur.execute("""
                INSERT INTO users (id, email, name, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id, email, name
            """, (user_id, user_data.email, user_data.name, hashed_password))
            
            new_user = cur.fetchone()
            conn.commit()
            
            # Create access token
            access_token = create_access_token(
                user_id=str(new_user[0]),
                email=new_user[1],
                name=new_user[2]
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": str(new_user[0]),
                    "email": new_user[1],
                    "name": new_user[2]
                }
            }

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login user and return JWT"""
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, email, name, password_hash 
                FROM users 
                WHERE email = %s
            """, (user_data.email,))
            
            user = cur.fetchone()
            
            if not user or not verify_password(user_data.password, user[3]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Create access token
            access_token = create_access_token(
                user_id=str(user[0]),
                email=user[1],
                name=user[2]
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user[0]),
                    "email": user[1],
                    "name": user[2]
                }
            }
