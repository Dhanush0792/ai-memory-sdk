"""Rate Limiting Middleware

Per-API-key rate limiting using token bucket algorithm.
Enforces rate limits specified in the api_keys table.

Headers:
- X-RateLimit-Limit: Max requests per minute
- X-RateLimit-Remaining: Tokens remaining
- X-RateLimit-Reset: Unix timestamp of next refill
- Retry-After: Seconds to wait (on 429)
"""

import os
import logging
from collections import defaultdict
from time import time
from fastapi import HTTPException, Request, Response
from typing import Dict

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum tokens (requests per minute)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time()
    
    def refill(self):
        """Refill tokens based on time elapsed"""
        now = time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens
        
        Args:
            tokens: Number of tokens to consume
        
        Returns:
            True if successful, False if insufficient tokens
        """
        self.refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def get_remaining(self) -> int:
        """Get remaining tokens"""
        self.refill()
        return int(self.tokens)
    
    def get_reset_time(self) -> float:
        """Get Unix timestamp when bucket will be full"""
        self.refill()
        
        if self.tokens >= self.capacity:
            return time()
        
        tokens_needed = self.capacity - self.tokens
        seconds_until_full = tokens_needed / self.refill_rate
        
        return time() + seconds_until_full


class RateLimiter:
    """
    Per-API-key rate limiter using token bucket algorithm
    """
    
    def __init__(self):
        """Initialize rate limiter"""
        # Track buckets per key_id
        self.buckets: Dict[str, TokenBucket] = {}
        self.auth_failures: Dict[str, list] = defaultdict(list)
        self.max_auth_failures = int(os.getenv("RATE_LIMIT_AUTH_FAILURES", "10"))
    
    def get_bucket(self, key_id: str, rate_limit_per_minute: int) -> TokenBucket:
        """
        Get or create token bucket for a key
        
        Args:
            key_id: API key identifier
            rate_limit_per_minute: Rate limit for this key
        
        Returns:
            TokenBucket instance
        """
        if key_id not in self.buckets:
            # Create new bucket
            # refill_rate = requests per minute / 60 seconds
            refill_rate = rate_limit_per_minute / 60.0
            self.buckets[key_id] = TokenBucket(
                capacity=rate_limit_per_minute,
                refill_rate=refill_rate
            )
        
        return self.buckets[key_id]
    
    def check_rate_limit(
        self,
        key_id: str,
        rate_limit_per_minute: int
    ) -> tuple[bool, int, float]:
        """
        Check if request is within rate limit
        
        Args:
            key_id: API key identifier
            rate_limit_per_minute: Rate limit for this key
        
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        bucket = self.get_bucket(key_id, rate_limit_per_minute)
        
        allowed = bucket.consume(1)
        remaining = bucket.get_remaining()
        reset_time = bucket.get_reset_time()
        
        return (allowed, remaining, reset_time)
    
    def record_auth_failure(self, ip: str) -> None:
        """
        Record authentication failure by IP
        
        Args:
            ip: IP address
        
        Raises:
            HTTPException: 429 if too many auth failures
        """
        now = time()
        
        # Clean old failures (60 second window)
        cutoff = now - 60
        self.auth_failures[ip] = [t for t in self.auth_failures[ip] if t > cutoff]
        
        # Record this failure
        self.auth_failures[ip].append(now)
        
        if len(self.auth_failures[ip]) >= self.max_auth_failures:
            logger.warning(f"Too many auth failures from IP: {ip}")
            raise HTTPException(
                status_code=429,
                detail="Too many authentication failures. Please try again later.",
                headers={"Retry-After": "60"}
            )


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for per-key rate limiting
    
    Enforces rate limits based on API key context.
    Adds rate limit headers to all responses.
    """
    # Skip rate limiting for health and root endpoints
    if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    # Process request to populate API key context
    response = await call_next(request)
    
    # Check if authenticated
    if hasattr(request.state, "api_key_context"):
        context = request.state.api_key_context
        
        # Check rate limit
        allowed, remaining, reset_time = rate_limiter.check_rate_limit(
            key_id=context.key_id,
            rate_limit_per_minute=context.rate_limit_per_minute
        )
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(context.rate_limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        if not allowed:
            # Rate limit exceeded
            retry_after = int(reset_time - time())
            logger.warning(f"Rate limit exceeded for key: {context.key_id[:8]}...")
            
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(context.rate_limit_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                    "Retry-After": str(max(1, retry_after))
                }
            )
    
    # Record auth failures by IP
    if response.status_code == 401:
        ip = request.client.host if request.client else "unknown"
        try:
            rate_limiter.record_auth_failure(ip)
        except HTTPException:
            # Auth failure rate limit exceeded
            raise
    
    return response
