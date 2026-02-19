from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from app.database import db
from app.auth.dependencies import require_admin
from app.auth.utils import get_password_hash
from app.observability import logger

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "user"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

class StatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_memories: int
    memory_count_per_user: List[dict]
    recent_logins_24h: int

import time
import json
from fastapi import Request

# Simple in-memory rate limiter
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10
_rate_limit_store = {}

def check_admin_rate_limit(request: Request):
    """Enforce admin rate limits."""
    client_ip = request.client.host
    now = time.time()
    
    # Cleanup old entries
    if client_ip in _rate_limit_store:
        _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if t > now - RATE_LIMIT_WINDOW]
    
    current_requests = _rate_limit_store.get(client_ip, [])
    
    if len(current_requests) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning("admin_rate_limit_exceeded", ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Admin rate limit exceeded"
        )
        
    current_requests.append(now)
    _rate_limit_store[client_ip] = current_requests

@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0, 
    limit: int = 50, 
    admin: dict = Depends(require_admin),
    request: Request = None 
):
    """List all users (Admin only)."""
    # Enforce rate limit
    if request:
        check_admin_rate_limit(request)
    
    with db.get_cursor() as cur:
        cur.execute("""
            SELECT id, email, full_name, role, is_active, created_at, last_login_at
            FROM users 
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, skip))
        users = cur.fetchall()
    return users

@router.post("/create-user", response_model=UserResponse)
def create_user(
    user: UserCreate, 
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Create a new user manually (Admin only)."""
    check_admin_rate_limit(request)
    
    with db.get_cursor() as cur:
        # Check existing
        cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = get_password_hash(user.password)
        
        cur.execute("""
            INSERT INTO users (email, password_hash, full_name, role, is_active)
            VALUES (%s, %s, %s, %s, true)
            RETURNING id, email, full_name, role, is_active, created_at, last_login_at
        """, (user.email, hashed_password, user.full_name, user.role))
        
        new_user = cur.fetchone()
        
        # Audit Log
        cur.execute("""
            INSERT INTO admin_audit_logs (admin_id, action_type, target_user_id, metadata)
            VALUES (%s, 'CREATE_USER', %s, %s)
        """, (
            admin["id"], 
            new_user["id"], 
            json.dumps({"email": user.email, "role": user.role})
        ))
        
        logger.info("admin_create_user", admin=admin["id"], new_user=user.email)
        return new_user

@router.patch("/disable-user/{user_id}")
def disable_user(
    user_id: str, 
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Disable a user account (Admin only)."""
    check_admin_rate_limit(request)
    
    with db.get_cursor() as cur:
        cur.execute("""
            UPDATE users SET is_active = false 
            WHERE id = %s 
            RETURNING id
        """, (user_id,))
        
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
            
        # Audit Log
        cur.execute("""
            INSERT INTO admin_audit_logs (admin_id, action_type, target_user_id)
            VALUES (%s, 'DISABLE_USER', %s)
        """, (admin["id"], user_id))
            
    logger.info("admin_disable_user", admin=admin["id"], target_user=user_id)
    return {"status": "success", "message": f"User {user_id} disabled"}

@router.get("/stats", response_model=StatsResponse)
def get_system_stats(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Get system-wide statistics (Admin only)."""
    check_admin_rate_limit(request)
    
    with db.get_cursor() as cur:
        # User stats
        cur.execute("SELECT COUNT(*) as total FROM users")
        total_users = cur.fetchone()["total"]
        
        cur.execute("SELECT COUNT(*) as active FROM users WHERE is_active = true")
        active_users = cur.fetchone()["active"]
        
        # Recent logins (last 24h)
        cur.execute("""
            SELECT COUNT(*) as recent 
            FROM users 
            WHERE last_login_at > NOW() - INTERVAL '24 hours'
        """)
        recent_logins = cur.fetchone()["recent"]
        
        # Memory stats
        cur.execute("SELECT COUNT(*) as total FROM memories")
        total_memories = cur.fetchone()["total"]
        
        # Per user breakdown (top 10)
        cur.execute("""
            SELECT user_id, COUNT(*) as count 
            FROM memories 
            GROUP BY user_id 
            ORDER BY count DESC 
            LIMIT 10
        """)
        memory_breakdown = cur.fetchall()
        
    return StatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_memories=total_memories,
        memory_count_per_user=[{"user_id": str(r["user_id"]), "count": r["count"]} for r in memory_breakdown],
        recent_logins_24h=recent_logins
    )
