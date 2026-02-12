"""
Policy Engine for Enterprise Memory Infrastructure.
Enforces tenant-specific policies for quotas, TTL, quality, and predicates.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta
from app.database import db


class PolicyViolation(Exception):
    """Raised when a policy is violated."""
    pass


@dataclass
class TenantPolicy:
    """Tenant-specific policy configuration."""
    tenant_id: str
    max_memories_per_user: int
    max_memories_per_tenant: int
    memory_ttl_days: Optional[int]
    auto_expire_enabled: bool
    min_confidence_threshold: float
    allowed_predicates: Optional[List[str]]
    rate_limit_per_minute: int
    tier: str


class PolicyEngine:
    """
    Centralized policy enforcement engine.
    
    Responsibilities:
    - Load and cache tenant policies
    - Enforce quota limits
    - Calculate TTL
    - Validate confidence thresholds
    - Validate predicate whitelists
    """
    
    def __init__(self):
        self._policy_cache = {}
    
    def get_policy(self, tenant_id: str) -> TenantPolicy:
        """
        Fetch tenant policy from database with caching.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            TenantPolicy object
            
        Raises:
            PolicyViolation: If tenant has no policy configured
        """
        # Check cache first
        if tenant_id in self._policy_cache:
            return self._policy_cache[tenant_id]
        
        # Fetch from database
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        tenant_id,
                        max_memories_per_user,
                        max_memories_per_tenant,
                        memory_ttl_days,
                        auto_expire_enabled,
                        min_confidence_threshold,
                        allowed_predicates,
                        rate_limit_per_minute,
                        tier
                    FROM tenant_policies
                    WHERE tenant_id = %s
                """, (tenant_id,))
                
                row = cur.fetchone()
                
                if not row:
                    # Create default policy for new tenant
                    return self._create_default_policy(tenant_id)
                
                policy = TenantPolicy(
                    tenant_id=row[0],
                    max_memories_per_user=row[1],
                    max_memories_per_tenant=row[2],
                    memory_ttl_days=row[3],
                    auto_expire_enabled=row[4],
                    min_confidence_threshold=row[5],
                    allowed_predicates=row[6],
                    rate_limit_per_minute=row[7],
                    tier=row[8]
                )
                
                # Cache policy
                self._policy_cache[tenant_id] = policy
                return policy
    
    def _create_default_policy(self, tenant_id: str) -> TenantPolicy:
        """Create and insert default policy for new tenant."""
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tenant_policies (
                        tenant_id,
                        tier,
                        max_memories_per_user,
                        max_memories_per_tenant,
                        memory_ttl_days,
                        auto_expire_enabled,
                        min_confidence_threshold,
                        rate_limit_per_minute
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id) DO NOTHING
                    RETURNING 
                        tenant_id,
                        max_memories_per_user,
                        max_memories_per_tenant,
                        memory_ttl_days,
                        auto_expire_enabled,
                        min_confidence_threshold,
                        allowed_predicates,
                        rate_limit_per_minute,
                        tier
                """, (tenant_id, 'standard', 10000, 100000, 365, True, 0.5, 100))
                
                row = cur.fetchone()
                conn.commit()
                
                if row:
                    policy = TenantPolicy(
                        tenant_id=row[0],
                        max_memories_per_user=row[1],
                        max_memories_per_tenant=row[2],
                        memory_ttl_days=row[3],
                        auto_expire_enabled=row[4],
                        min_confidence_threshold=row[5],
                        allowed_predicates=row[6],
                        rate_limit_per_minute=row[7],
                        tier=row[8]
                    )
                    self._policy_cache[tenant_id] = policy
                    return policy
                
                # Fallback to in-memory default
                return TenantPolicy(
                    tenant_id=tenant_id,
                    max_memories_per_user=10000,
                    max_memories_per_tenant=100000,
                    memory_ttl_days=365,
                    auto_expire_enabled=True,
                    min_confidence_threshold=0.5,
                    allowed_predicates=None,
                    rate_limit_per_minute=100,
                    tier='standard'
                )
    
    def enforce_user_quota(self, tenant_id: str, user_id: str) -> None:
        """
        Enforce per-user memory quota.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            
        Raises:
            PolicyViolation: If user quota exceeded
        """
        policy = self.get_policy(tenant_id)
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM memories
                    WHERE tenant_id = %s
                      AND user_id = %s
                      AND is_active = true
                """, (tenant_id, user_id))
                
                count = cur.fetchone()[0]
                
                if count >= policy.max_memories_per_user:
                    raise PolicyViolation(
                        f"User quota exceeded: {count}/{policy.max_memories_per_user} memories. "
                        f"Upgrade to {policy.tier} tier or delete old memories."
                    )
    
    def enforce_tenant_quota(self, tenant_id: str) -> None:
        """
        Enforce per-tenant memory quota.
        
        Args:
            tenant_id: Tenant identifier
            
        Raises:
            PolicyViolation: If tenant quota exceeded
        """
        policy = self.get_policy(tenant_id)
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM memories
                    WHERE tenant_id = %s
                      AND is_active = true
                """, (tenant_id,))
                
                count = cur.fetchone()[0]
                
                if count >= policy.max_memories_per_tenant:
                    raise PolicyViolation(
                        f"Tenant quota exceeded: {count}/{policy.max_memories_per_tenant} memories. "
                        f"Contact support to upgrade your plan."
                    )
    
    def enforce_confidence_threshold(self, tenant_id: str, confidence: float) -> None:
        """
        Enforce minimum confidence threshold.
        
        Args:
            tenant_id: Tenant identifier
            confidence: Confidence score to validate
            
        Raises:
            PolicyViolation: If confidence below threshold
        """
        policy = self.get_policy(tenant_id)
        
        if confidence < policy.min_confidence_threshold:
            raise PolicyViolation(
                f"Confidence {confidence:.2f} below minimum threshold "
                f"{policy.min_confidence_threshold:.2f} for {policy.tier} tier"
            )
    
    def enforce_predicate_whitelist(self, tenant_id: str, predicate: str) -> None:
        """
        Enforce predicate whitelist if configured.
        
        Args:
            tenant_id: Tenant identifier
            predicate: Predicate to validate
            
        Raises:
            PolicyViolation: If predicate not in whitelist
        """
        policy = self.get_policy(tenant_id)
        
        # If no whitelist configured, allow all predicates
        if policy.allowed_predicates is None:
            return
        
        if predicate not in policy.allowed_predicates:
            raise PolicyViolation(
                f"Predicate '{predicate}' not in allowed list: {policy.allowed_predicates}"
            )
    
    def calculate_expiry(self, tenant_id: str) -> Optional[datetime]:
        """
        Calculate expiry timestamp based on tenant policy.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Expiry datetime or None if no expiry
        """
        policy = self.get_policy(tenant_id)
        
        if not policy.auto_expire_enabled or policy.memory_ttl_days is None:
            return None
        
        return datetime.utcnow() + timedelta(days=policy.memory_ttl_days)
    
    def invalidate_cache(self, tenant_id: str) -> None:
        """
        Invalidate cached policy for tenant.
        
        Args:
            tenant_id: Tenant identifier
        """
        if tenant_id in self._policy_cache:
            del self._policy_cache[tenant_id]
    
    def get_rate_limit(self, tenant_id: str) -> int:
        """
        Get rate limit for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Rate limit (requests per minute)
        """
        policy = self.get_policy(tenant_id)
        return policy.rate_limit_per_minute


# Global policy engine instance
policy_engine = PolicyEngine()
