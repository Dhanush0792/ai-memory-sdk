"""API Key Management

This module handles API key generation, hashing, storage, and revocation.
API keys are the primary authentication mechanism for the AI Memory SDK.

Security:
- Keys are never stored in plaintext
- Keys are hashed using SHA-256
- Keys are returned only once during creation
- Revocation is soft-delete (preserves audit trail)
"""

import secrets
import hashlib
import uuid
import json
from datetime import datetime
from typing import Optional
import psycopg
import os


class KeyManager:
    """Manages API key lifecycle"""
    
    def __init__(self):
        """Initialize key manager"""
        self.conn_string = os.getenv("DATABASE_URL")
        if not self.conn_string:
            raise ValueError(
                "DATABASE_URL environment variable not set. "
                "Please set DATABASE_URL=postgresql://user:password@host:port/database"
            )
    
    def _get_conn(self):
        """Get database connection"""
        try:
            return psycopg.connect(self.conn_string)
        except psycopg.OperationalError as e:
            raise ConnectionError(f"Failed to connect to database: {e}") from e
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a new API key in the format: aimsk_live_<32_char_random>
        
        Returns:
            Formatted API key string
        """
        # Generate 32 bytes of random data (64 hex characters)
        random_part = secrets.token_hex(32)
        return f"aimsk_live_{random_part}"
    
    @staticmethod
    def hash_key(api_key: str) -> str:
        """
        Hash an API key using SHA-256
        
        Args:
            api_key: Raw API key to hash
        
        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    
    def create_api_key(
        self,
        owner_id: str,
        rate_limit_per_minute: int = 60,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Create a new API key and store it in the database
        
        Args:
            owner_id: Identifier for the key owner (customer/app)
            rate_limit_per_minute: Rate limit for this key (default: 60)
            metadata: Optional metadata (plan, billing_id, etc.)
        
        Returns:
            Dict containing:
                - api_key: The plaintext key (ONLY TIME IT'S RETURNED)
                - key_id: UUID of the key record
                - owner_id: Owner identifier
                - rate_limit_per_minute: Rate limit
                - created_at: Creation timestamp
        
        Security:
            The plaintext key is returned ONLY ONCE. Store it securely.
            The database stores only the hash.
        """
        # Generate key
        api_key = self.generate_api_key()
        key_hash = self.hash_key(api_key)
        
        # Validate owner_id
        if not owner_id or not owner_id.strip():
            raise ValueError("owner_id cannot be empty")
        
        if len(owner_id) > 255:
            raise ValueError("owner_id too long (max 255 chars)")
        
        # Validate rate limit
        if rate_limit_per_minute < 1 or rate_limit_per_minute > 10000:
            raise ValueError("rate_limit_per_minute must be between 1 and 10000")
        
        # Prepare metadata
        metadata_json = json.dumps(metadata or {})
        
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Insert key
                cur.execute("""
                    INSERT INTO api_keys (key_hash, owner_id, rate_limit_per_minute, metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, created_at
                """, (key_hash, owner_id, rate_limit_per_minute, metadata_json))
                
                result = cur.fetchone()
                key_id = result[0]
                created_at = result[1]
                
                # Audit log
                cur.execute("""
                    INSERT INTO audit_logs (id, user_id, action, resource_id, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    owner_id,
                    "api_key.create",
                    str(key_id),
                    json.dumps({"rate_limit": rate_limit_per_minute})
                ))
                
                conn.commit()
        
        return {
            "api_key": api_key,  # ONLY TIME THIS IS RETURNED
            "key_id": str(key_id),
            "owner_id": owner_id,
            "rate_limit_per_minute": rate_limit_per_minute,
            "created_at": created_at.isoformat()
        }
    
    def validate_key(self, api_key: str) -> Optional[dict]:
        """
        Validate an API key and return its context
        
        Args:
            api_key: Raw API key from request
        
        Returns:
            Dict with key context if valid:
                - key_id: UUID of the key
                - owner_id: Owner identifier
                - rate_limit_per_minute: Rate limit
                - metadata: Key metadata
            None if invalid or revoked
        """
        key_hash = self.hash_key(api_key)
        
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, owner_id, rate_limit_per_minute, metadata, is_active, revoked_at
                    FROM api_keys
                    WHERE key_hash = %s
                """, (key_hash,))
                
                result = cur.fetchone()
                
                if not result:
                    return None
                
                key_id, owner_id, rate_limit, metadata, is_active, revoked_at = result
                
                # Check if active and not revoked
                if not is_active or revoked_at is not None:
                    return None
                
                # Update last_used_at asynchronously (don't block request)
                cur.execute("""
                    UPDATE api_keys
                    SET last_used_at = NOW()
                    WHERE id = %s
                """, (key_id,))
                conn.commit()
                
                return {
                    "key_id": str(key_id),
                    "owner_id": owner_id,
                    "rate_limit_per_minute": rate_limit,
                    "metadata": metadata
                }
    
    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key (soft delete)
        
        Args:
            key_id: UUID of the key to revoke
        
        Returns:
            True if revoked, False if not found
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE api_keys
                    SET is_active = false, revoked_at = NOW()
                    WHERE id = %s AND is_active = true
                    RETURNING owner_id
                """, (key_id,))
                
                result = cur.fetchone()
                
                if result:
                    owner_id = result[0]
                    
                    # Audit log
                    cur.execute("""
                        INSERT INTO audit_logs (id, user_id, action, resource_id)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        str(uuid.uuid4()),
                        owner_id,
                        "api_key.revoke",
                        key_id
                    ))
                    
                    conn.commit()
                    return True
                
                return False
    
    def list_keys(self, owner_id: str) -> list:
        """
        List all API keys for an owner (internal use only)
        
        Args:
            owner_id: Owner identifier
        
        Returns:
            List of key metadata (NO PLAINTEXT KEYS)
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, owner_id, is_active, created_at, revoked_at, 
                           rate_limit_per_minute, last_used_at, metadata
                    FROM api_keys
                    WHERE owner_id = %s
                    ORDER BY created_at DESC
                """, (owner_id,))
                
                keys = []
                for row in cur.fetchall():
                    keys.append({
                        "key_id": str(row[0]),
                        "owner_id": row[1],
                        "is_active": row[2],
                        "created_at": row[3].isoformat(),
                        "revoked_at": row[4].isoformat() if row[4] else None,
                        "rate_limit_per_minute": row[5],
                        "last_used_at": row[6].isoformat() if row[6] else None,
                        "metadata": row[7]
                    })
                
                return keys
