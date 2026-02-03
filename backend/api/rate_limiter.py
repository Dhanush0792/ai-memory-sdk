"""Rate Limiting Middleware"""

import os
import logging
from collections import defaultdict
from time import time
from fastapi import HTTPException, Request
from typing import Dict, List

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm
    
    Tracks requests per API key and enforces limits.
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        max_auth_failures: int = 10
    ):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            max_auth_failures: Max auth failures per window
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_auth_failures = max_auth_failures
        
        # Track requests: key -> [timestamp, timestamp, ...]
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.auth_failures: Dict[str, List[float]] = defaultdict(list)
    
    def _clean_old_requests(self, key: str, now: float) -> None:
        """Remove requests outside the current window"""
        cutoff = now - self.window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
        self.auth_failures[key] = [t for t in self.auth_failures[key] if t > cutoff]
    
    def check_rate_limit(self, key: str) -> None:
        """
        Check if request is within rate limit
        
        Args:
            key: Identifier for rate limiting (e.g., API key or IP)
        
        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        now = time()
        self._clean_old_requests(key, now)
        
        # Check if limit exceeded
        if len(self.requests[key]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for key: {key[:8]}...")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s"
            )
        
        # Record this request
        self.requests[key].append(now)
    
    def record_auth_failure(self, key: str) -> None:
        """
        Record authentication failure
        
        Args:
            key: Identifier (e.g., IP address)
        
        Raises:
            HTTPException: 429 if too many auth failures
        """
        now = time()
        self._clean_old_requests(key, now)
        
        self.auth_failures[key].append(now)
        
        if len(self.auth_failures[key]) >= self.max_auth_failures:
            logger.warning(f"Too many auth failures for: {key[:8]}...")
            raise HTTPException(
                status_code=429,
                detail="Too many authentication failures. Please try again later."
            )


# Global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
    max_auth_failures=int(os.getenv("RATE_LIMIT_AUTH_FAILURES", "10"))
)


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting
    
    Extracts API key from Authorization header and enforces limits.
    """
    # Extract API key for rate limiting
    auth_header = request.headers.get("authorization", "")
    
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:]
        # Use first 16 chars as identifier (don't store full key)
        key_id = api_key[:16] if len(api_key) >= 16 else api_key
    else:
        # Use IP address if no API key
        key_id = request.client.host if request.client else "unknown"
    
    try:
        # Check rate limit
        rate_limiter.check_rate_limit(key_id)
        
        # Process request
        response = await call_next(request)
        
        # Record auth failures
        if response.status_code in (401, 403):
            rate_limiter.record_auth_failure(key_id)
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiter error: {e}")
        # Don't block requests if rate limiter fails
        return await call_next(request)
