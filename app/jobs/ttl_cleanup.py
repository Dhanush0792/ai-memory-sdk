"""
TTL (Time-To-Live) cleanup job for expired memories.
Runs as background task to mark expired memories as inactive.
"""

import asyncio
from datetime import datetime
from typing import List, Dict
from app.database import db
from app.audit import log_action


class TTLCleanupJob:
    """
    Background job to cleanup expired memories.
    
    Responsibilities:
    - Find memories past expiration
    - Mark as inactive
    - Audit log each expiration
    """
    
    def __init__(self, interval_seconds: int = 3600):
        """
        Initialize TTL cleanup job.
        
        Args:
            interval_seconds: How often to run cleanup (default: 1 hour)
        """
        self.interval_seconds = interval_seconds
        self.is_running = False
    
    async def run_forever(self):
        """Run cleanup job continuously."""
        self.is_running = True
        print(f"TTL cleanup job started (interval: {self.interval_seconds}s)")
        
        while self.is_running:
            try:
                expired_count = await self.cleanup_expired_memories()
                if expired_count > 0:
                    print(f"TTL cleanup: Expired {expired_count} memories")
            except Exception as e:
                print(f"TTL cleanup error: {e}", flush=True)
            
            await asyncio.sleep(self.interval_seconds)
    
    async def cleanup_expired_memories(self) -> int:
        """
        Find and mark expired memories as inactive.
        
        Returns:
            Number of memories expired
        """
        expired_memories = []
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Find expired memories
                cur.execute("""
                    SELECT 
                        id,
                        tenant_id,
                        user_id,
                        subject,
                        predicate,
                        expires_at
                    FROM memories
                    WHERE is_active = true
                      AND expires_at IS NOT NULL
                      AND expires_at <= CURRENT_TIMESTAMP
                    LIMIT 1000
                """)
                
                rows = cur.fetchall()
                
                if not rows:
                    return 0
                
                expired_memories = [
                    {
                        'id': row[0],
                        'tenant_id': row[1],
                        'user_id': row[2],
                        'subject': row[3],
                        'predicate': row[4],
                        'expires_at': row[5]
                    }
                    for row in rows
                ]
                
                # Mark as inactive
                memory_ids = [m['id'] for m in expired_memories]
                cur.execute("""
                    UPDATE memories
                    SET is_active = false
                    WHERE id = ANY(%s)
                """, (memory_ids,))
                
                conn.commit()
        
        # Audit log each expiration
        for memory in expired_memories:
            try:
                log_action(
                    tenant_id=memory['tenant_id'],
                    action_type="EXPIRE",
                    api_key="system",
                    success=True,
                    user_id=memory['user_id'],
                    memory_id=memory['id'],
                    metadata={
                        "subject": memory['subject'],
                        "predicate": memory['predicate'],
                        "expired_at": memory['expires_at'].isoformat() if memory['expires_at'] else None,
                        "reason": "ttl_expired"
                    }
                )
            except Exception as e:
                print(f"Failed to log expiration for {memory['id']}: {e}")
        
        return len(expired_memories)
    
    def stop(self):
        """Stop the cleanup job."""
        self.is_running = False
        print("TTL cleanup job stopped")


# Global TTL cleanup job instance
ttl_cleanup_job = TTLCleanupJob(interval_seconds=3600)  # Run hourly
