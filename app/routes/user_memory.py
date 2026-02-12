"""
User memory management endpoints for transparency and control.
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import settings
from app.observability import logger
from app.database import db


router = APIRouter(prefix="/api/v1/user", tags=["user-memory"])


class MemoryItem(BaseModel):
    """Memory item model."""
    id: str
    subject: str
    predicate: str
    object: str
    confidence: float
    version: int
    scope: str
    is_active: bool
    created_at: str
    updated_at: str


class MemoryListResponse(BaseModel):
    """Memory list response."""
    user_id: str
    tenant_id: str
    total_count: int
    active_count: int
    memories: List[MemoryItem]


class MemoryDeleteResponse(BaseModel):
    """Memory delete response."""
    memory_id: str
    deleted: bool
    message: str


class VersionHistoryItem(BaseModel):
    """Version history item."""
    version: int
    object: str
    confidence: float
    is_active: bool
    created_at: str
    updated_at: str


class VersionHistoryResponse(BaseModel):
    """Version history response."""
    subject: str
    predicate: str
    total_versions: int
    versions: List[VersionHistoryItem]


@router.get("/memories", response_model=MemoryListResponse)
async def list_memories(
    x_tenant_id: str = Header(...),
    x_user_id: str = Header(...),
    scope: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List all memories for current user.
    
    Args:
        scope: Filter by scope (user/team/organization/global)
        limit: Maximum number of memories to return
        offset: Pagination offset
    """
    logger.info(
        "list_memories_request",
        user_id=x_user_id,
        tenant_id=x_tenant_id,
        scope=scope,
        limit=limit,
        offset=offset
    )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Build query
                query = """
                    SELECT 
                        id, subject, predicate, object, confidence,
                        version, scope, is_active, created_at, updated_at
                    FROM memories
                    WHERE tenant_id = %s AND user_id = %s
                """
                params = [x_tenant_id, x_user_id]
                
                if scope:
                    query += " AND scope = %s"
                    params.append(scope)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                # Get total count
                count_query = """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE is_active = true) as active
                    FROM memories
                    WHERE tenant_id = %s AND user_id = %s
                """
                count_params = [x_tenant_id, x_user_id]
                
                if scope:
                    count_query += " AND scope = %s"
                    count_params.append(scope)
                
                cur.execute(count_query, count_params)
                counts = cur.fetchone()
                
                memories = [
                    MemoryItem(
                        id=str(row[0]),
                        subject=row[1],
                        predicate=row[2],
                        object=row[3],
                        confidence=float(row[4]),
                        version=row[5],
                        scope=row[6],
                        is_active=row[7],
                        created_at=row[8].isoformat(),
                        updated_at=row[9].isoformat()
                    )
                    for row in rows
                ]
                
                logger.info(
                    "list_memories_success",
                    user_id=x_user_id,
                    count=len(memories)
                )
                
                return MemoryListResponse(
                    user_id=x_user_id,
                    tenant_id=x_tenant_id,
                    total_count=counts[0],
                    active_count=counts[1],
                    memories=memories
                )
                
    except Exception as e:
        logger.error(
            "list_memories_failed",
            user_id=x_user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memories/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(
    memory_id: str,
    x_tenant_id: str = Header(...),
    x_user_id: str = Header(...)
):
    """
    Soft delete a memory (mark as inactive).
    
    Creates audit log entry.
    """
    logger.info(
        "delete_memory_request",
        user_id=x_user_id,
        tenant_id=x_tenant_id,
        memory_id=memory_id
    )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Verify ownership
                cur.execute(
                    """
                    SELECT id, subject, predicate, object 
                    FROM memories 
                    WHERE id = %s AND tenant_id = %s AND user_id = %s
                    """,
                    (memory_id, x_tenant_id, x_user_id)
                )
                
                memory = cur.fetchone()
                if not memory:
                    raise HTTPException(
                        status_code=404,
                        detail="Memory not found or access denied"
                    )
                
                # Soft delete
                cur.execute(
                    """
                    UPDATE memories 
                    SET is_active = false, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (memory_id,)
                )
                
                # Create audit log
                cur.execute(
                    """
                    INSERT INTO audit_logs 
                    (tenant_id, user_id, action, resource_type, resource_id, details)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        x_tenant_id,
                        x_user_id,
                        "delete_memory",
                        "memory",
                        memory_id,
                        f"User deleted memory: {memory[1]} {memory[2]} {memory[3]}"
                    )
                )
                
                conn.commit()
                
                logger.info(
                    "delete_memory_success",
                    user_id=x_user_id,
                    memory_id=memory_id
                )
                
                return MemoryDeleteResponse(
                    memory_id=memory_id,
                    deleted=True,
                    message="Memory deleted successfully"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "delete_memory_failed",
            user_id=x_user_id,
            memory_id=memory_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/{subject}/{predicate}/history", response_model=VersionHistoryResponse)
async def get_version_history(
    subject: str,
    predicate: str,
    x_tenant_id: str = Header(...),
    x_user_id: str = Header(...)
):
    """
    Get version history for a specific subject+predicate.
    
    Shows all versions (active and inactive).
    """
    logger.info(
        "version_history_request",
        user_id=x_user_id,
        subject=subject,
        predicate=predicate
    )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT version, object, confidence, is_active, created_at, updated_at
                    FROM memories
                    WHERE tenant_id = %s AND user_id = %s 
                      AND subject = %s AND predicate = %s
                    ORDER BY version DESC
                    """,
                    (x_tenant_id, x_user_id, subject, predicate)
                )
                
                rows = cur.fetchall()
                
                if not rows:
                    raise HTTPException(
                        status_code=404,
                        detail="No version history found"
                    )
                
                versions = [
                    VersionHistoryItem(
                        version=row[0],
                        object=row[1],
                        confidence=float(row[2]),
                        is_active=row[3],
                        created_at=row[4].isoformat(),
                        updated_at=row[5].isoformat()
                    )
                    for row in rows
                ]
                
                logger.info(
                    "version_history_success",
                    user_id=x_user_id,
                    subject=subject,
                    predicate=predicate,
                    version_count=len(versions)
                )
                
                return VersionHistoryResponse(
                    subject=subject,
                    predicate=predicate,
                    total_versions=len(versions),
                    versions=versions
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "version_history_failed",
            user_id=x_user_id,
            subject=subject,
            predicate=predicate,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
