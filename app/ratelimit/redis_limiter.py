"""
Redis-based distributed rate limiter for horizontal scaling.
Replaces in-memory rate limiter with persistent, shared state.
"""

import time
from typing import Optional
import redis
from app.config import settings
from app.observability import logger


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis sliding window algorithm.
    
    Features:
    - Shared state across multiple instances
    - Persistent across restarts
    - Per-tenant and per-API-key limits
    - Sliding window for smooth rate limiting
    """
    
    def __init__(self, redis_url: str):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.default_limit = settings.rate_limit_requests
        self.window_seconds = 60  # 1 minute window
    
    def check_rate_limit(
        self,
        tenant_id: str,
        api_key_hash: str,
        limit: Optional[int] = None
    ) -> None:
        """
        Check if request is within rate limit using sliding window.
        
        Args:
            tenant_id: Tenant identifier
            api_key_hash: Hashed API key
            limit: Optional custom limit (uses default if None)
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        limit = limit or self.default_limit
        
        # Create unique key for this tenant+api_key
        key = f"ratelimit:{tenant_id}:{api_key_hash}"
        
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()
        
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiration to window size
        pipe.expire(key, self.window_seconds)
        
        results = pipe.execute()
        
        # Get count before adding current request
        current_count = results[1]
        
        if current_count >= limit:
            logger.warning(
                "rate_limit_exceeded",
                tenant_id=tenant_id,
                current_count=current_count,
                limit=limit
            )
            raise RateLimitExceeded(
                f"Rate limit exceeded: {current_count}/{limit} requests per minute"
            )
        
        logger.debug(
            "rate_limit_check",
            tenant_id=tenant_id,
            current_count=current_count + 1,
            limit=limit
        )
    
    def get_remaining(
        self,
        tenant_id: str,
        api_key_hash: str,
        limit: Optional[int] = None
    ) -> int:
        """
        Get remaining requests in current window.
        
        Args:
            tenant_id: Tenant identifier
            api_key_hash: Hashed API key
            limit: Optional custom limit
            
        Returns:
            Number of remaining requests
        """
        limit = limit or self.default_limit
        key = f"ratelimit:{tenant_id}:{api_key_hash}"
        
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Remove old entries and count
        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        results = pipe.execute()
        
        current_count = results[1]
        return max(0, limit - current_count)
    
    def reset(self, tenant_id: str, api_key_hash: str) -> None:
        """
        Reset rate limit for tenant+api_key.
        
        Args:
            tenant_id: Tenant identifier
            api_key_hash: Hashed API key
        """
        key = f"ratelimit:{tenant_id}:{api_key_hash}"
        self.redis_client.delete(key)
        logger.info("rate_limit_reset", tenant_id=tenant_id)
    
    def health_check(self) -> bool:
        """
        Check Redis connection health.
        
        Returns:
            True if Redis is accessible
        """
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False


# Global rate limiter instance
rate_limiter: Optional[RedisRateLimiter] = None


def initialize_rate_limiter():
    """Initialize global rate limiter."""
    global rate_limiter
    
    if settings.redis_url:
        rate_limiter = RedisRateLimiter(settings.redis_url)
        logger.info("redis_rate_limiter_initialized", url=settings.redis_url)
    else:
        logger.warning("redis_url_not_configured_rate_limiting_disabled")


def get_rate_limiter() -> Optional[RedisRateLimiter]:
    """Get global rate limiter instance."""
    return rate_limiter
