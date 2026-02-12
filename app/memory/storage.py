"""
Enhanced memory storage with Phase 2 features:
- Policy enforcement
- RBAC integration
- Scoped memory
- TTL calculation
- Observability metrics
"""

import time
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from psycopg.errors import UniqueViolation, LockNotAvailable

from app.database import db
from app.models import ExtractedTriple, MemoryObject
from app.policy import policy_engine, PolicyViolation
from app.rbac import rbac_engine, PermissionDenied
from app.observability import logger, memory_ingest_total, update_memory_count


def store_memory(
    tenant_id: str,
    user_id: str,
    triple: ExtractedTriple,
    source: str = "conversation",
    scope: str = "user"
) -> MemoryObject:
    """
    Store memory with Phase 2 enhancements.
    
    Phase 2 Additions:
    - Policy enforcement (quotas, confidence, predicates)
    - Scope assignment
    - TTL calculation
    - Metrics recording
    
    Args:
        tenant_id: Tenant identifier
        user_id: User identifier
        triple: Extracted triple
        source: Memory source
        scope: Memory scope (user/team/organization/global)
        
    Returns:
        Stored MemoryObject
        
    Raises:
        PolicyViolation: If policy violated
        PermissionDenied: If user lacks permission
    """
    # Phase 2: Enforce policies
    policy_engine.enforce_user_quota(tenant_id, user_id)
    policy_engine.enforce_tenant_quota(tenant_id)
    policy_engine.enforce_confidence_threshold(tenant_id, triple.confidence)
    policy_engine.enforce_predicate_whitelist(tenant_id, triple.predicate)
    
    # Phase 2: Calculate expiry
    expires_at = policy_engine.calculate_expiry(tenant_id)
    
    # Retry logic for concurrency (V1.1)
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    # V1.1: Lock existing active memory for update
                    cur.execute("""
                        SELECT id, version
                        FROM memories
                        WHERE tenant_id = %s AND user_id = %s 
                          AND subject = %s AND predicate = %s 
                          AND is_active = true
                        FOR UPDATE NOWAIT
                    """, (tenant_id, user_id, triple.subject, triple.predicate))
                    
                    existing = cur.fetchone()
                    
                    if existing:
                        # Deactivate old version
                        cur.execute("""
                            UPDATE memories
                            SET is_active = false
                            WHERE id = %s
                        """, (existing[0],))
                        
                        new_version = existing[1] + 1
                    else:
                        new_version = 1
                    
                    # Insert new version with Phase 2 fields
                    cur.execute("""
                        INSERT INTO memories (
                            tenant_id, user_id, subject, predicate, object,
                            confidence, source, version, scope, expires_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at
                    """, (
                        tenant_id, user_id, triple.subject, triple.predicate, triple.object,
                        triple.confidence, source, new_version, scope, expires_at
                    ))
                    
                    result = cur.fetchone()
                    conn.commit()
                    
                    # Phase 2: Record metrics
                    memory_ingest_total.labels(tenant_id=tenant_id, status="success").inc()
                    
                    # Phase 2: Log structured
                    logger.info("memory_stored",
                                tenant_id=tenant_id,
                                user_id=user_id,
                                memory_id=str(result[0]),
                                scope=scope,
                                version=new_version,
                                expires_at=expires_at.isoformat() if expires_at else None)
                    
                    return MemoryObject(
                        id=result[0],
                        tenant_id=tenant_id,
                        user_id=user_id,
                        subject=triple.subject,
                        predicate=triple.predicate,
                        object=triple.object,
                        confidence=triple.confidence,
                        source=source,
                        version=new_version,
                        created_at=result[1]
                    )
                    
        except LockNotAvailable:
            if attempt < max_retries - 1:
                logger.warning("lock_contention", attempt=attempt, tenant_id=tenant_id)
                time.sleep(retry_delay * (2 ** attempt))
                continue
            else:
                memory_ingest_total.labels(tenant_id=tenant_id, status="lock_timeout").inc()
                raise RuntimeError("Failed to acquire lock after retries")
        
        except Exception as e:
            memory_ingest_total.labels(tenant_id=tenant_id, status="error").inc()
            logger.error("memory_store_failed", error=str(e), tenant_id=tenant_id)
            raise


def get_memories(
    tenant_id: str,
    user_id: str,
    scope: Optional[str] = None
) -> List[MemoryObject]:
    """
    Retrieve memories with scope filtering.
    
    Phase 2: Respects scope hierarchy.
    
    Args:
        tenant_id: Tenant identifier
        user_id: User identifier
        scope: Optional scope filter
        
    Returns:
        List of active memories
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            if scope:
                cur.execute("""
                    SELECT id, tenant_id, user_id, subject, predicate, object,
                           confidence, source, version, created_at
                    FROM memories
                    WHERE tenant_id = %s
                      AND user_id = %s
                      AND is_active = true
                      AND scope = %s
                      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY created_at DESC
                """, (tenant_id, user_id, scope))
            else:
                cur.execute("""
                    SELECT id, tenant_id, user_id, subject, predicate, object,
                           confidence, source, version, created_at
                    FROM memories
                    WHERE tenant_id = %s
                      AND user_id = %s
                      AND is_active = true
                      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY created_at DESC
                """, (tenant_id, user_id))
            
            rows = cur.fetchall()
            
            return [
                MemoryObject(
                    id=row[0],
                    tenant_id=row[1],
                    user_id=row[2],
                    subject=row[3],
                    predicate=row[4],
                    object=row[5],
                    confidence=row[6],
                    source=row[7],
                    version=row[8],
                    created_at=row[9]
                )
                for row in rows
            ]


def store_memories_batch(
    tenant_id: str,
    user_id: str,
    triples: List[ExtractedTriple],
    source: str = "conversation",
    scope: str = "user"
) -> List[MemoryObject]:
    """
    Store multiple memories in batch.
    
    Args:
        tenant_id: Tenant identifier
        user_id: User identifier
        triples: List of extracted triples
        source: Memory source
        scope: Memory scope
        
    Returns:
        List of stored MemoryObjects
    """
    stored_memories = []
    
    for triple in triples:
        try:
            memory = store_memory(
                tenant_id=tenant_id,
                user_id=user_id,
                triple=triple,
                source=source,
                scope=scope
            )
            stored_memories.append(memory)
        except Exception as e:
            logger.error("batch_store_failed",
                        tenant_id=tenant_id,
                        user_id=user_id,
                        triple=triple.dict(),
                        error=str(e))
            # Continue with next triple
            continue
    
    return stored_memories


class StorageError(Exception):
    """Storage operation error."""
    pass


def get_memory_by_id(memory_id: UUID) -> Optional[MemoryObject]:
    """
    Retrieve a single memory by ID.
    
    Args:
        memory_id: Memory UUID
        
    Returns:
        MemoryObject if found, None otherwise
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, tenant_id, user_id, subject, predicate, object,
                           confidence, source, version, created_at
                    FROM memories
                    WHERE id = %s
                      AND is_active = true
                """, (memory_id,))
                
                row = cur.fetchone()
                
                if not row:
                    return None
                
                return MemoryObject(
                    id=row[0],
                    tenant_id=row[1],
                    user_id=row[2],
                    subject=row[3],
                    predicate=row[4],
                    object=row[5],
                    confidence=row[6],
                    source=row[7],
                    version=row[8],
                    created_at=row[9]
                )
    except Exception as e:
        logger.error("get_memory_by_id_failed", memory_id=str(memory_id), error=str(e))
        raise StorageError(f"Failed to retrieve memory: {str(e)}")


def delete_memory(memory_id: UUID) -> bool:
    """
    Soft delete a memory by ID.
    
    Args:
        memory_id: Memory UUID
        
    Returns:
        True if deleted, False if not found
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE memories
                    SET is_active = false
                    WHERE id = %s
                      AND is_active = true
                """, (memory_id,))
                
                deleted_count = cur.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info("memory_deleted", memory_id=str(memory_id))
                    return True
                else:
                    logger.warning("memory_not_found", memory_id=str(memory_id))
                    return False
    except Exception as e:
        logger.error("delete_memory_failed", memory_id=str(memory_id), error=str(e))
        raise StorageError(f"Failed to delete memory: {str(e)}")


def delete_user_memories(tenant_id: str, user_id: str) -> int:
    """
    Delete all memories for a user.
    
    Args:
        tenant_id: Tenant identifier
        user_id: User identifier
        
    Returns:
        Number of memories deleted
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE memories
                SET is_active = false
                WHERE tenant_id = %s
                  AND user_id = %s
                  AND is_active = true
            """, (tenant_id, user_id))
            
            deleted_count = cur.rowcount
            conn.commit()
            
            logger.info("memories_deleted",
                        tenant_id=tenant_id,
                        user_id=user_id,
                        count=deleted_count)
            
            return deleted_count
