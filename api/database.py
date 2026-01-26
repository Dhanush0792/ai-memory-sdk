"""Database Layer for Memory Storage"""

import psycopg
import os
import json
from typing import Optional, Literal
from datetime import datetime
import uuid
from .encryption import EncryptionService

class Database:
    """PostgreSQL database interface"""
    
    _pool = None  # Class-level connection pool
    
    def __init__(self):
        """Initialize database connection"""
        self.conn_string = os.getenv("DATABASE_URL")
        if not self.conn_string:
            self.conn_string = "postgresql://postgres:postgres@localhost:5432/memory_db"
        # Initialize encryption service
        try:
            self.encryption = EncryptionService()
        except ValueError:
            # Allow startup without encryption for key generation
            self.encryption = None
    
    def _get_conn(self):
        """Get database connection from pool"""
        try:
            return psycopg.connect(self.conn_string)
        except psycopg.OperationalError as e:
            raise ConnectionError(f"Failed to connect to database: {e}") from e
    
    def init_schema(self):
        """Initialize database schema"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_user_id ON memories(user_id);
                    CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type);
                    
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource_id TEXT,
                        timestamp TIMESTAMP DEFAULT NOW(),
                        metadata JSONB DEFAULT '{}'
                    );
                """)
                conn.commit()
    
    def add_memory(
        self,
        user_id: str,
        content: str,
        memory_type: Literal["fact", "preference", "event"],
        metadata: dict = None,
        expires_at: Optional[datetime] = None
    ) -> dict:
        """Add a new memory"""
        memory_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Encrypt content before storage
        encrypted_content = self.encryption.encrypt(content) if self.encryption else content
        
        # Validate metadata is JSON-serializable
        try:
            metadata_json = json.dumps(metadata or {})
        except (TypeError, ValueError) as e:
            raise ValueError(f"Metadata not JSON-serializable: {e}")
        
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO memories (id, user_id, content, memory_type, metadata, created_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    memory_id,
                    user_id,
                    encrypted_content,
                    memory_type,
                    metadata_json,
                    created_at,
                    expires_at
                ))
                
                # Audit log
                cur.execute("""
                    INSERT INTO audit_logs (id, user_id, action, resource_id, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    user_id,
                    "memory.create",
                    memory_id,
                    json.dumps({"type": memory_type})
                ))
                
                conn.commit()
        
        return {
            "id": memory_id,
            "user_id": user_id,
            "content": content,
            "type": memory_type,
            "metadata": metadata or {},
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None
        }
    
    def get_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """Get memories for a user"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT id, user_id, content, memory_type, metadata, created_at, expires_at
                    FROM memories
                    WHERE user_id = %s
                """
                params = [user_id]
                
                if memory_type:
                    query += " AND memory_type = %s"
                    params.append(memory_type)
                
                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
        
        memories = []
        for row in rows:
            # Decrypt content on read
            decrypted_content = self.encryption.decrypt(row[2]) if self.encryption else row[2]
            
            memories.append({
                "id": row[0],
                "user_id": row[1],
                "content": decrypted_content,
                "type": row[3],
                "metadata": row[4],
                "created_at": row[5].isoformat(),
                "expires_at": row[6].isoformat() if row[6] else None
            })
        
        return memories
    
    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Hard delete a memory (only if owned by user)"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Delete only if owned by user
                cur.execute("""
                    DELETE FROM memories 
                    WHERE id = %s AND user_id = %s
                    RETURNING user_id
                """, (memory_id, user_id))
                
                result = cur.fetchone()
                
                if result:
                    # Audit log
                    cur.execute("""
                        INSERT INTO audit_logs (id, user_id, action, resource_id)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        str(uuid.uuid4()),
                        result[0],
                        "memory.delete",
                        memory_id
                    ))
                
                conn.commit()
                return result is not None
    
    def delete_user_data(self, user_id: str) -> int:
        """Hard delete all user data (GDPR)"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM memories WHERE user_id = %s
                    RETURNING id
                """, (user_id,))
                
                count = len(cur.fetchall())
                
                # Audit log
                cur.execute("""
                    INSERT INTO audit_logs (id, user_id, action, metadata)
                    VALUES (%s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    user_id,
                    "user.gdpr_delete",
                    json.dumps({"deleted_count": count})
                ))
                
                conn.commit()
                return count
    
    def delete_by_type(self, user_id: str, memory_type: str) -> int:
        """Delete all memories of a specific type"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM memories WHERE user_id = %s AND memory_type = %s
                    RETURNING id
                """, (user_id, memory_type))
                
                count = len(cur.fetchall())
                
                # Audit log
                cur.execute("""
                    INSERT INTO audit_logs (id, user_id, action, metadata)
                    VALUES (%s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    user_id,
                    "memory.delete_by_type",
                    json.dumps({"type": memory_type, "count": count})
                ))
                
                conn.commit()
                return count
    
    def delete_by_key(self, user_id: str, key: str) -> int:
        """Delete memories by metadata key"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM memories 
                    WHERE user_id = %s AND metadata ? %s
                    RETURNING id
                """, (user_id, key))
                
                count = len(cur.fetchall())
                
                # Audit log
                cur.execute("""
                    INSERT INTO audit_logs (id, user_id, action, metadata)
                    VALUES (%s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    user_id,
                    "memory.delete_by_key",
                    json.dumps({"key": key, "count": count})
                ))
                
                conn.commit()
                return count
    
    def get_memory_stats(self, user_id: str) -> dict:
        """Get comprehensive memory statistics for a user"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Total count
                cur.execute("""
                    SELECT COUNT(*) FROM memories WHERE user_id = %s
                """, (user_id,))
                total = cur.fetchone()[0]
                
                # Count by type
                cur.execute("""
                    SELECT memory_type, COUNT(*) 
                    FROM memories 
                    WHERE user_id = %s 
                    GROUP BY memory_type
                """, (user_id,))
                by_type = {row[0]: row[1] for row in cur.fetchall()}
                
                # Date range
                cur.execute("""
                    SELECT MIN(created_at), MAX(created_at)
                    FROM memories
                    WHERE user_id = %s
                """, (user_id,))
                date_row = cur.fetchone()
                
                return {
                    "total": total,
                    "by_type": by_type,
                    "oldest": date_row[0].isoformat() if date_row[0] else None,
                    "newest": date_row[1].isoformat() if date_row[1] else None
                }
