from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from app.database import db
from app.auth.dependencies import require_admin
from app.auth.utils import get_password_hash
from app.observability import logger

router = APIRouter(prefix="/admin", tags=["admin"])

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "user"

from uuid import UUID

class UserResponse(BaseModel):
    id: UUID
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
    
    try:
        with db.get_cursor() as cur:
            # Check existing
            cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
            if cur.fetchone():
                logger.warning("admin_create_user_duplicate", email=user.email)
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
                str(new_user["id"]), 
                json.dumps({"email": user.email, "role": user.role})
            ))
            
            logger.info("admin_create_user_success", admin=admin["id"], new_user=user.email)
            return new_user
    except Exception as e:
        logger.error("admin_create_user_failed", error=str(e), admin_id=admin.get("id"))
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Internal server error")

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


# ── Audit Log Viewer ──
@router.get("/audit-logs")
def get_audit_logs(
    request: Request,
    action_type: str = None,
    limit: int = 50,
    skip: int = 0,
    admin: dict = Depends(require_admin)
):
    """Get admin audit logs with optional filtering."""
    check_admin_rate_limit(request)
    
    with db.get_cursor() as cur:
        query = """
            SELECT a.id, a.admin_id, a.action_type, a.target_user_id,
                   a.timestamp, a.metadata,
                   u1.email as admin_email,
                   u2.email as target_email
            FROM admin_audit_logs a
            LEFT JOIN users u1 ON a.admin_id::text = u1.id::text
            LEFT JOIN users u2 ON a.target_user_id::text = u2.id::text
        """
        params = []
        
        if action_type:
            query += " WHERE a.action_type = %s"
            params.append(action_type)
        
        query += " ORDER BY a.timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, skip])
        
        cur.execute(query, tuple(params))
        logs = cur.fetchall()
        
        # Get total count
        count_query = "SELECT COUNT(*) as total FROM admin_audit_logs"
        if action_type:
            count_query += " WHERE action_type = %s"
            cur.execute(count_query, (action_type,))
        else:
            cur.execute(count_query)
        total = cur.fetchone()["total"]
    
    return {
        "logs": [
            {
                "id": str(log["id"]),
                "admin_email": log["admin_email"] or "Unknown",
                "action_type": log["action_type"],
                "target_email": log["target_email"] or "N/A",
                "timestamp": log["timestamp"].isoformat() if log["timestamp"] else None,
                "metadata": log["metadata"]
            }
            for log in logs
        ],
        "total": total
    }


# ── Enable User ──
@router.patch("/enable-user/{user_id}")
def enable_user(
    user_id: str,
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Re-enable a disabled user account (Admin only)."""
    check_admin_rate_limit(request)
    
    with db.get_cursor() as cur:
        cur.execute("""
            UPDATE users SET is_active = true
            WHERE id = %s
            RETURNING id, email
        """, (user_id,))
        
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Audit Log
        cur.execute("""
            INSERT INTO admin_audit_logs (admin_id, action_type, target_user_id, metadata)
            VALUES (%s, 'ENABLE_USER', %s, %s)
        """, (
            admin["id"],
            user_id,
            json.dumps({"email": result["email"]})
        ))
    
    logger.info("admin_enable_user", admin=admin["id"], target_user=user_id)
    return {"status": "success", "message": f"User {user_id} enabled"}


# ── System Health ──
@router.get("/system-health")
def get_system_health(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Extended system health check (Admin only)."""
    check_admin_rate_limit(request)
    
    health = {
        "database": "unknown",
        "tables": {},
        "status": "operational"
    }
    
    try:
        db_ok = db.health_check()
        health["database"] = "connected" if db_ok else "disconnected"
        
        if db_ok:
            with db.get_cursor() as cur:
                # Table row counts
                for table in ["users", "memories", "audit_logs", "admin_audit_logs"]:
                    try:
                        cur.execute(f"SELECT COUNT(*) as count FROM {table}")
                        health["tables"][table] = cur.fetchone()["count"]
                    except Exception:
                        health["tables"][table] = -1
                
                # Disabled users count
                cur.execute("SELECT COUNT(*) as count FROM users WHERE is_active = false")
                health["disabled_users"] = cur.fetchone()["count"]
                
                # Memories created today
                cur.execute("""
                    SELECT COUNT(*) as count FROM memories
                    WHERE created_at > CURRENT_DATE
                """)
                health["memories_today"] = cur.fetchone()["count"]
        
        if not db_ok:
            health["status"] = "degraded"
    except Exception as e:
        health["status"] = "error"
        health["error"] = str(e)
    
    return health


# ── User Search ──
@router.get("/users/search")
def search_users(
    q: str,
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Search users by email or name (Admin only)."""
    check_admin_rate_limit(request)
    
    if len(q) < 2:
        raise HTTPException(
            status_code=400,
            detail="Query must be at least 2 characters"
        )
    
    with db.get_cursor() as cur:
        cur.execute("""
            SELECT id, email, full_name, role, is_active, created_at, last_login_at
            FROM users
            WHERE email ILIKE %s OR full_name ILIKE %s
            ORDER BY created_at DESC
            LIMIT 20
        """, (f"%{q}%", f"%{q}%"))
        users = cur.fetchall()
    
    return users
