"""
Audit logging utility for V1.1.
Tracks all operations with hashed API keys.
"""

import hashlib
import json
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.database import db


def hash_api_key(api_key: str) -> str:
    """
    Hash API key using SHA-256.
    
    Args:
        api_key: Raw API key
        
    Returns:
        Hexadecimal hash string (64 characters)
    """
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def log_action(
    tenant_id: str,
    action_type: str,
    api_key: str,
    success: bool,
    user_id: Optional[str] = None,
    memory_id: Optional[UUID] = None,
    metadata: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> None:
    """
    Log an action to the audit_logs table.
    
    CRITICAL: Never log raw conversation_text in metadata.
    
    Args:
        tenant_id: Tenant identifier
        action_type: One of INGEST, UPDATE, DELETE, RETRIEVE, HEALTH
        api_key: Raw API key (will be hashed before storing)
        success: Whether operation succeeded
        user_id: User identifier (optional)
        memory_id: Memory UUID (optional)
        metadata: Additional context (optional, no sensitive data)
        error_message: Error details if success=False
    """
    try:
        # Hash API key before storing
        api_key_hash = hash_api_key(api_key)
        
        # Sanitize metadata - ensure no conversation_text
        safe_metadata = None
        if metadata:
            # Create copy and remove any sensitive fields
            safe_metadata = {k: v for k, v in metadata.items() 
                           if k not in ['conversation_text', 'api_key', 'password']}
            
            # Convert to JSON string for JSONB storage
            if safe_metadata:
                safe_metadata = json.dumps(safe_metadata)
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        INSERT INTO audit_logs (
                            tenant_id, user_id, action_type, memory_id,
                            api_key_hash, metadata, success, error_message
                        )
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    """, (
                        tenant_id,
                        user_id,
                        action_type,
                        memory_id,
                        api_key_hash,
                        safe_metadata,
                        success,
                        error_message
                    ))
                    conn.commit()
                except Exception:
                    # Rollback to prevent leaving connection in aborted state
                    conn.rollback()
                    raise
            
    except Exception as e:
        # Audit logging should never break the main operation
        # Log to stderr but don't raise
        print(f"WARNING: Audit log failed: {e}", flush=True)


def get_audit_logs(
    tenant_id: str,
    limit: int = 100,
    action_type: Optional[str] = None
) -> list:
    """
    Retrieve audit logs for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        limit: Maximum number of logs to return
        action_type: Filter by action type (optional)
        
    Returns:
        List of audit log records
    """
    try:
        with db.get_cursor() as cur:
            if action_type:
                cur.execute("""
                    SELECT *
                    FROM audit_logs
                    WHERE tenant_id = %s AND action_type = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (tenant_id, action_type, limit))
            else:
                cur.execute("""
                    SELECT *
                    FROM audit_logs
                    WHERE tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (tenant_id, limit))
            
            return cur.fetchall()
            
    except Exception as e:
        print(f"ERROR: Failed to retrieve audit logs: {e}", flush=True)
        return []
