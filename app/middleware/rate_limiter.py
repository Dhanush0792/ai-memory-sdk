"""
Rate limiting middleware for V1.1.
Simple in-memory rate limiter (does not persist across restarts).
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from app.config import settings


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    
    WARNING: This does NOT persist across container restarts.
    For production, consider Redis-based rate limiting.
    """
    
    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        
        # Store: {api_key: [(timestamp1, timestamp2, ...)]}
        self.request_history: Dict[str, list] = defaultdict(list)
    
    def check_rate_limit(self, api_key: str) -> Tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Args:
            api_key: API key to check
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Get request history for this API key
        history = self.request_history[api_key]
        
        # Remove old requests outside the window
        history[:] = [ts for ts in history if ts > window_start]
        
        # Check if within limit
        if len(history) >= self.max_requests:
            return False, 0
        
        # Add current request
        history.append(current_time)
        
        remaining = self.max_requests - len(history)
        return True, remaining
    
    def cleanup_old_entries(self):
        """
        Cleanup old entries to prevent memory leak.
        Called periodically.
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Remove API keys with no recent requests
        keys_to_remove = []
        for api_key, history in self.request_history.items():
            history[:] = [ts for ts in history if ts > window_start]
            if not history:
                keys_to_remove.append(api_key)
        
        for key in keys_to_remove:
            del self.request_history[key]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=60
)


async def rate_limit_middleware(request, api_key: str) -> None:
    """
    Check rate limit for the given API key.
    
    Args:
        request: FastAPI request object (can be None if called directly)
        api_key: API key or user ID from authentication
        
    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    is_allowed, remaining = rate_limiter.check_rate_limit(api_key)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {settings.rate_limit_requests} requests per minute.",
            headers={"Retry-After": "60"}
        )
    
    # Add rate limit headers to response (will be added by route)
    if request is not None and hasattr(request, 'state'):
        request.state.rate_limit_remaining = remaining
