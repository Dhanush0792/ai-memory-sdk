"""Database Layer for Memory Storage"""

import psycopg
import os
import json
import socket
from urllib.parse import urlparse
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
            raise ValueError(
                "DATABASE_URL environment variable not set. "
                "Please set DATABASE_URL=postgresql://user:password@host:port/database"
            )
        # Initialize encryption service
        try:
            self.encryption = EncryptionService()
        except ValueError:
            # Allow startup without encryption for key generation
            self.encryption = None
            
    def _resolve_to_ipv4(self, conn_string: str) -> Optional[str]:
        """Resolve hostname to IPv4 to avoid IPv6 issues on some platforms"""
        try:
            hostname = None
            port = 5432
            
            # Robust parsing of hostname from connection string
            # Handle standard URI format: postgresql://user:pass@host:port/db
            if "://" in conn_string:
                try:
                    # Use specialized parsing if available, otherwise simple urlparse
                    result = urlparse(conn_string)
                    hostname = result.hostname
                    if result.port:
                        port = result.port
                except Exception:
                    pass
            
            # Fallback manual parsing if urlparse failed or yielded nothing (e.g. complex passwords)
            if not hostname and "@" in conn_string:
                # Assuming format ...@hostname:port/....
                # Split by @, take the last part
                after_at = conn_string.rsplit("@", 1)[1]
                # Split by / to remove dbname
                host_port = after_at.split("/")[0]
                # Split by ? to remove params
                host_port = host_port.split("?")[0]
                
                if ":" in host_port:
                    hostname = host_port.split(":")[0]
                else:
                    hostname = host_port

            if hostname:
                print(f"🔍 Attempting to resolve IPv4 for hostname: {hostname}")
                # Use getaddrinfo with AF_UNSPEC to catch ANY record, then filter for AF_INET
                addrs = socket.getaddrinfo(hostname, port, 0, socket.SOCK_STREAM)
                
                for family, type, proto, canonname, sockaddr in addrs:
                    if family == socket.AF_INET:
                        ip = sockaddr[0]
                        print(f"✅ Resolved {hostname} to IPv4: {ip}")
                        return ip
                        
                print(f"⚠️ Could not find IPv4 address for {hostname} (Found only IPv6?)")
            
            return None
        except Exception as e:
            # Silently fail and let psycopg handle it naturally if extraction fails
            print(f"⚠️ DNS Resolution Warning: {e}")
            return None
    
    def _get_conn(self):
        """Get database connection from pool"""
        try:
            # Force IPv4 if possible to avoid "Network is unreachable" (IPv6) errors
            host_ip = self._resolve_to_ipv4(self.conn_string)
            if host_ip:
                return psycopg.connect(self.conn_string, hostaddr=host_ip, prepare_threshold=None)
            return psycopg.connect(self.conn_string, prepare_threshold=None)
        except psycopg.OperationalError as e:
            raise ConnectionError(f"Failed to connect to database: {e}") from e
    
    def init_schema(self):
        """Initialize database schema with automatic migrations"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Debugging: Check current usage schema
                cur.execute("SELECT current_schema()")
                current_schema = cur.fetchone()[0]
                print(f"🔍 Database Current Schema: {current_schema}")

                # Check if memories table exists in public schema
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name='memories' AND table_schema='public'
                """)
                
                table_exists = cur.fetchone() is not None
                
                if table_exists:
                    # Table exists - check for missing columns and migrate
                    print("🔄 Checking database schema for migrations (public.memories)...")
                    
                    # Get all existing columns in public schema
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='memories' AND table_schema='public'
                    """)
                    existing_columns = {row[0] for row in cur.fetchall()}
                    print(f"📊 Found existing columns: {existing_columns}")
                    
                    migrations_needed = []
                    
                    # Check for missing columns
                    if 'owner_id' not in existing_columns:
                        migrations_needed.append('owner_id')
                    if 'is_deleted' not in existing_columns:
                        migrations_needed.append('is_deleted')
                    if 'expires_at' not in existing_columns:
                        migrations_needed.append('expires_at')
                    if 'ttl_seconds' not in existing_columns:
                        migrations_needed.append('ttl_seconds')
                    if 'ingestion_mode' not in existing_columns:
                        migrations_needed.append('ingestion_mode')
                    
                    if 'memory_type' not in existing_columns:
                        migrations_needed.append('memory_type')
                    if 'key' not in existing_columns:
                        migrations_needed.append('key')
                    if 'value' not in existing_columns:
                        migrations_needed.append('value')
                    if 'confidence' not in existing_columns:
                        migrations_needed.append('confidence')
                    if 'importance' not in existing_columns:
                        migrations_needed.append('importance')
                    if 'metadata' not in existing_columns:
                        migrations_needed.append('metadata')
                    
                    if migrations_needed:
                        print(f"📝 Migrating columns: {', '.join(migrations_needed)}")
                        
                        # Add owner_id column
                        if 'owner_id' in migrations_needed:
                            print("  → Adding owner_id column...")
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ADD COLUMN IF NOT EXISTS owner_id TEXT
                            """)
                            cur.execute("""
                                UPDATE public.memories 
                                SET owner_id = user_id 
                                WHERE owner_id IS NULL
                            """)
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ALTER COLUMN owner_id SET NOT NULL
                            """)
                            cur.execute("""
                                CREATE INDEX IF NOT EXISTS idx_owner_id ON public.memories(owner_id)
                            """)
                        
                        # Add memory_type column (CRITICAL FIX)
                        if 'memory_type' in migrations_needed:
                            print("  → Adding memory_type column...")
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ADD COLUMN IF NOT EXISTS memory_type TEXT DEFAULT 'system'
                            """)
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ADD CONSTRAINT check_memory_type 
                                CHECK (memory_type IN ('fact', 'preference', 'event', 'system'))
                            """)
                            cur.execute("""
                                UPDATE public.memories 
                                SET memory_type = 'system' 
                                WHERE memory_type IS NULL
                            """)
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ALTER COLUMN memory_type SET NOT NULL
                            """)
                            cur.execute("""
                                CREATE INDEX IF NOT EXISTS idx_type ON public.memories(memory_type)
                            """)

                        # Add key/value/metadata/confidence/importance
                        if 'key' in migrations_needed:
                             print("  → Adding key column...")
                             cur.execute("ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS key TEXT")
                        
                        if 'value' in migrations_needed:
                             print("  → Adding value column...")
                             cur.execute("ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS value JSONB")

                        if 'metadata' in migrations_needed:
                             print("  → Adding metadata column...")
                             cur.execute("ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'")

                        if 'confidence' in migrations_needed:
                             print("  → Adding confidence column...")
                             cur.execute("ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS confidence REAL DEFAULT 1.0")

                        if 'importance' in migrations_needed:
                             print("  → Adding importance column...")
                             cur.execute("ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS importance INTEGER")

                        # Add is_deleted column
                        if 'is_deleted' in migrations_needed:
                            print("  → Adding is_deleted column...")
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE
                            """)
                            cur.execute("""
                                UPDATE public.memories 
                                SET is_deleted = FALSE 
                                WHERE is_deleted IS NULL
                            """)
                            cur.execute("""
                                CREATE INDEX IF NOT EXISTS idx_is_deleted ON public.memories(is_deleted)
                            """)
                        
                        # Add expires_at column
                        if 'expires_at' in migrations_needed:
                            print("  → Adding expires_at column...")
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP
                            """)
                            cur.execute("""
                                CREATE INDEX IF NOT EXISTS idx_expires_at ON public.memories(expires_at)
                            """)
                        
                        # Add ttl_seconds column
                        if 'ttl_seconds' in migrations_needed:
                            print("  → Adding ttl_seconds column...")
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ADD COLUMN IF NOT EXISTS ttl_seconds INTEGER
                            """)
                        
                        # Add ingestion_mode column
                        if 'ingestion_mode' in migrations_needed:
                            print("  → Adding ingestion_mode column...")
                            cur.execute("""
                                ALTER TABLE public.memories 
                                ADD COLUMN IF NOT EXISTS ingestion_mode TEXT DEFAULT 'explicit'
                            """)
                            cur.execute("""
                                UPDATE public.memories 
                                SET ingestion_mode = 'explicit' 
                                WHERE ingestion_mode IS NULL
                            """)
                        
                        conn.commit()
                        print("✅ Migration completed successfully!")
                    else:
                        print("✅ Database schema is up to date")

                # Check api_keys table for migrations
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name='api_keys' AND table_schema='public'
                """)
                if cur.fetchone():
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='api_keys' AND table_schema='public'
                    """)
                    ak_cols = {row[0] for row in cur.fetchall()}
                    if 'owner_id' not in ak_cols:
                         print("  → Adding owner_id to api_keys")
                         cur.execute("ALTER TABLE public.api_keys ADD COLUMN IF NOT EXISTS owner_id TEXT")
                
                # Now create/update tables with full schema
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.memories (
                        id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        memory_type TEXT NOT NULL CHECK (memory_type IN ('fact', 'preference', 'event', 'system')),
                        key TEXT,
                        value JSONB,
                        confidence REAL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
                        importance INTEGER CHECK (importance BETWEEN 1 AND 5),
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP,
                        ttl_seconds INTEGER,
                        is_deleted BOOLEAN DEFAULT FALSE,
                        ingestion_mode TEXT DEFAULT 'explicit' CHECK (ingestion_mode IN ('explicit', 'rules'))
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_owner_id ON public.memories(owner_id);
                    CREATE INDEX IF NOT EXISTS idx_user_id ON public.memories(user_id);
                    CREATE INDEX IF NOT EXISTS idx_type ON public.memories(memory_type);
                    CREATE INDEX IF NOT EXISTS idx_is_deleted ON public.memories(is_deleted);
                    CREATE INDEX IF NOT EXISTS idx_expires_at ON public.memories(expires_at);
                    
                    CREATE TABLE IF NOT EXISTS public.audit_logs (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource_id TEXT,
                        timestamp TIMESTAMP DEFAULT NOW(),
                        metadata JSONB DEFAULT '{}'
                    );
                    
                    CREATE TABLE IF NOT EXISTS public.api_keys (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        key_hash TEXT NOT NULL UNIQUE,
                        owner_id TEXT NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        revoked_at TIMESTAMP,
                        rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
                        metadata JSONB DEFAULT '{}',
                        last_used_at TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_key_hash ON public.api_keys(key_hash);
                    CREATE INDEX IF NOT EXISTS idx_api_keys_owner_id ON public.api_keys(owner_id);
                    CREATE INDEX IF NOT EXISTS idx_is_active ON public.api_keys(is_active);
                    
                    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
                    
                    CREATE TABLE IF NOT EXISTS public.users (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255),
                        password_hash TEXT NOT NULL,
                        role VARCHAR(50) DEFAULT 'developer',
                        is_active BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
    
    def add_memory(
        self,
        owner_id: str,
        user_id: str,
        content: str,
        memory_type: Literal["fact", "preference", "event", "system"],
        key: Optional[str] = None,
        value: Optional[any] = None,
        confidence: float = 1.0,
        importance: Optional[int] = None,
        metadata: dict = None,
        ttl_seconds: Optional[int] = None,
        ingestion_mode: Literal["explicit", "rules"] = "explicit",
        expires_at: Optional[datetime] = None
    ) -> dict:
        """Add a new memory with Memory Contract v1 fields"""
        memory_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        updated_at = created_at
        
        # Validate memory_type
        valid_types = ["fact", "preference", "event", "system"]
        if memory_type not in valid_types:
            raise ValueError(f"Invalid memory_type. Must be one of: {', '.join(valid_types)}")
        
        # Validate ingestion_mode
        valid_modes = ["explicit", "rules"]
        if ingestion_mode not in valid_modes:
            raise ValueError(f"Invalid ingestion_mode. Must be one of: {', '.join(valid_modes)}")
        
        # Validate confidence
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        
        # Validate importance
        if importance is not None and not (1 <= importance <= 5):
            raise ValueError("importance must be between 1 and 5")
        
        # Calculate expires_at from ttl_seconds if provided
        if ttl_seconds is not None and expires_at is None:
            from datetime import timedelta
            expires_at = created_at + timedelta(seconds=ttl_seconds)
        
        # Encrypt content before storage
        encrypted_content = self.encryption.encrypt(content) if self.encryption else content
        
        # Validate and serialize metadata
        try:
            metadata_json = json.dumps(metadata or {})
        except (TypeError, ValueError) as e:
            raise ValueError(f"Metadata not JSON-serializable: {e}")
        
        # Serialize value as JSON
        value_json = json.dumps(value) if value is not None else None
        
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO memories (
                        id, owner_id, user_id, content, memory_type, key, value,
                        confidence, importance, metadata, created_at, updated_at,
                        expires_at, ttl_seconds, is_deleted, ingestion_mode
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    memory_id,
                    owner_id,
                    user_id,
                    encrypted_content,
                    memory_type,
                    key,
                    value_json,
                    confidence,
                    importance,
                    metadata_json,
                    created_at,
                    updated_at,
                    expires_at,
                    ttl_seconds,
                    False,  # is_deleted
                    ingestion_mode
                ))
                
                # Audit log
                cur.execute("""
                    INSERT INTO audit_logs (id, user_id, action, resource_id, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    owner_id,
                    "memory.create",
                    memory_id,
                    json.dumps({"type": memory_type, "ingestion_mode": ingestion_mode})
                ))
                
                conn.commit()
        
        return {
            "id": memory_id,
            "owner_id": owner_id,
            "user_id": user_id,
            "content": content,
            "type": memory_type,
            "key": key,
            "value": value,
            "confidence": confidence,
            "importance": importance,
            "metadata": metadata or {},
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "ttl_seconds": ttl_seconds,
            "is_deleted": False,
            "ingestion_mode": ingestion_mode
        }
    
    def get_memories(
        self,
        owner_id: str,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """Get memories for a user (Memory Contract v1)"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        id, owner_id, user_id, content, memory_type, key, value,
                        confidence, importance, metadata, created_at, updated_at,
                        expires_at, ttl_seconds, is_deleted, ingestion_mode
                    FROM memories
                    WHERE owner_id = %s AND user_id = %s AND is_deleted = FALSE
                    AND (expires_at IS NULL OR expires_at > NOW())
                """
                params = [owner_id, user_id]
                
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
            decrypted_content = self.encryption.decrypt(row[3]) if self.encryption else row[3]
            
            # Value is already parsed by psycopg from JSONB
            value = row[6]  # No need for json.loads() - psycopg handles JSONB
            
            memories.append({
                "id": row[0],
                "owner_id": row[1],
                "user_id": row[2],
                "content": decrypted_content,
                "type": row[4],
                "key": row[5],
                "value": value,
                "confidence": row[7],
                "importance": row[8],
                "metadata": row[9],
                "created_at": row[10].isoformat(),
                "updated_at": row[11].isoformat(),
                "expires_at": row[12].isoformat() if row[12] else None,
                "ttl_seconds": row[13],
                "is_deleted": row[14],
                "ingestion_mode": row[15]
            })
        
        return memories
    
    def soft_delete_memory(self, memory_id: str, owner_id: str, user_id: str) -> bool:
        """Soft delete a memory (Memory Contract v1)"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE memories 
                    SET is_deleted = TRUE, updated_at = NOW()
                    WHERE id = %s AND owner_id = %s AND user_id = %s
                    RETURNING id
                """, (memory_id, owner_id, user_id))
                
                result = cur.fetchone()
                
                if result:
                    # Audit log
                    cur.execute("""
                        INSERT INTO audit_logs (id, user_id, action, resource_id)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        str(uuid.uuid4()),
                        owner_id,
                        "memory.soft_delete",
                        memory_id
                    ))
                
                conn.commit()
                return result is not None
    
    def delete_memory(self, memory_id: str, owner_id: str, user_id: str) -> bool:
        """Hard delete a memory (only if owned by owner)"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Delete only if owned by owner and user
                cur.execute("""
                    DELETE FROM memories 
                    WHERE id = %s AND owner_id = %s AND user_id = %s
                    RETURNING id
                """, (memory_id, owner_id, user_id))
                
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
    
    def delete_user_data(self, owner_id: str, user_id: str) -> int:
        """Hard delete all user data (GDPR)"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM memories WHERE owner_id = %s AND user_id = %s
                    RETURNING id
                """, (owner_id, user_id))
                
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
    
    def delete_by_type(self, owner_id: str, user_id: str, memory_type: str) -> int:
        """Delete all memories of a specific type"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM memories WHERE owner_id = %s AND user_id = %s AND memory_type = %s
                    RETURNING id
                """, (owner_id, user_id, memory_type))
                
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
    
    def delete_by_key(self, owner_id: str, user_id: str, key: str) -> int:
        """Delete memories by metadata key"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM memories 
                    WHERE owner_id = %s AND user_id = %s AND metadata ? %s
                    RETURNING id
                """, (owner_id, user_id, key))
                
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
    
    def get_memory_stats(self, owner_id: str, user_id: str) -> dict:
        """Get comprehensive memory statistics for a user (Memory Contract v1)"""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Total count (active only)
                cur.execute("""
                    SELECT COUNT(*) FROM memories 
                    WHERE owner_id = %s AND user_id = %s AND is_deleted = FALSE
                    AND (expires_at IS NULL OR expires_at > NOW())
                """, (owner_id, user_id))
                total = cur.fetchone()[0]
                
                # Soft-deleted count
                cur.execute("""
                    SELECT COUNT(*) FROM memories 
                    WHERE owner_id = %s AND user_id = %s AND is_deleted = TRUE
                """, (owner_id, user_id))
                deleted_count = cur.fetchone()[0]
                
                # Expired count
                cur.execute("""
                    SELECT COUNT(*) FROM memories 
                    WHERE owner_id = %s AND user_id = %s AND is_deleted = FALSE
                    AND expires_at IS NOT NULL AND expires_at <= NOW()
                """, (owner_id, user_id))
                expired_count = cur.fetchone()[0]
                
                # Count by type (active only)
                cur.execute("""
                    SELECT memory_type, COUNT(*) 
                    FROM memories 
                    WHERE owner_id = %s AND user_id = %s AND is_deleted = FALSE
                    AND (expires_at IS NULL OR expires_at > NOW())
                    GROUP BY memory_type
                """, (owner_id, user_id))
                by_type = {row[0]: row[1] for row in cur.fetchall()}
                
                # Count by importance (active only)
                cur.execute("""
                    SELECT importance, COUNT(*) 
                    FROM memories 
                    WHERE owner_id = %s AND user_id = %s AND is_deleted = FALSE
                    AND (expires_at IS NULL OR expires_at > NOW())
                    AND importance IS NOT NULL
                    GROUP BY importance
                """, (owner_id, user_id))
                by_importance = {row[0]: row[1] for row in cur.fetchall()}
                
                # Date range (active only)
                cur.execute("""
                    SELECT MIN(created_at), MAX(created_at)
                    FROM memories
                    WHERE owner_id = %s AND user_id = %s AND is_deleted = FALSE
                    AND (expires_at IS NULL OR expires_at > NOW())
                """, (owner_id, user_id))
                date_row = cur.fetchone()
                
                return {
                    "total": total,
                    "deleted": deleted_count,
                    "expired": expired_count,
                    "by_type": by_type,
                    "by_importance": by_importance,
                    "oldest": date_row[0].isoformat() if date_row[0] else None,
                    "newest": date_row[1].isoformat() if date_row[1] else None
                }
