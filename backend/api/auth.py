"""Authentication and Authorization Layer

This module handles API key authentication for the AI Memory SDK.
All /api/v1/* endpoints require a valid API key.

Security:
- API keys are validated against the database
- Keys are hashed using SHA-256 before lookup
- Timing-safe comparisons prevent timing attacks
- Failed auth attempts use constant error messages
- API keys are never logged or returned in responses
"""

import os
import hmac
import hashlib
import secrets
import logging
from fastapi import Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class APIKeyContext:
    """Context attached to authenticated requests"""
    def __init__(self, key_id: str, owner_id: str, rate_limit_per_minute: int, metadata: dict):
        self.key_id = key_id
        self.owner_id = owner_id
        self.rate_limit_per_minute = rate_limit_per_minute
        self.metadata = metadata






# Define security schemes for Swagger UI
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
http_bearer_scheme = HTTPBearer(auto_error=False)

async def get_api_key_context(
    request: Request,
    x_api_key: Optional[str] = Security(api_key_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(http_bearer_scheme)
) -> APIKeyContext:
    """
    Validate API key and return authentication context
    
    Supports:
    - X-API-Key header (Preferred)
    - Authorization: Bearer <key>
    
    This is the primary authentication mechanism for all /api/v1/* endpoints.
    """
    
    api_key = None
    
    # 1. Try X-API-Key first (Swagger default)
    if x_api_key:
        api_key = x_api_key
        
    # 2. Try Bearer token
    elif bearer and bearer.credentials:
        api_key = bearer.credentials
        
    # 3. Check for raw Authorization header (fallback for non-compliant clients)
    elif "authorization" in request.headers:
        auth_header = request.headers["authorization"]
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
    
    # No key found
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Provide X-API-Key or Bearer token"
        )

    
    # Validate API key format (aimsk_live_*)
    if api_key.startswith("aimsk_live_"):
        # New API key system
        from .key_manager import KeyManager
        
        key_manager = KeyManager()
        key_context = key_manager.validate_key(api_key)
        
        if not key_context:
            # Invalid or revoked key
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        # Attach context to request state
        context = APIKeyContext(
            key_id=key_context["key_id"],
            owner_id=key_context["owner_id"],
            rate_limit_per_minute=key_context["rate_limit_per_minute"],
            metadata=key_context["metadata"]
        )
        
        request.state.api_key_context = context
        
        # Log successful auth (owner_id only, never the key)
        logger.info(f"Authenticated: owner_id={context.owner_id[:8]}...")
        
        return context
    
    else:
        # Legacy authentication (backward compatibility)
        logger.warning("Legacy API key format detected - please migrate to new key system")
        
        # Get expected hash from environment
        expected_hash = os.getenv("API_KEY_HASH")
        
        # Fallback to plain key comparison
        if not expected_hash:
            expected_key = os.getenv("API_KEY", "dev-key-12345")
            if not hmac.compare_digest(api_key, expected_key):
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
        else:
            # Use constant-time comparison with hashed key
            if not verify_api_key_constant_time(api_key, expected_hash):
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
        
        # For legacy keys, we still need X-User-ID header
        x_user_id = request.headers.get("X-User-ID")
        
        if not x_user_id or not x_user_id.strip():
            raise HTTPException(
                status_code=401,
                detail="Missing X-User-ID header (required for legacy keys)"
            )
        
        # Validate user ID format
        user_id = x_user_id.strip()
        if len(user_id) > 255:
            raise HTTPException(
                status_code=422,
                detail="X-User-ID too long (max 255 chars)"
            )
        
        # Create legacy context
        context = APIKeyContext(
            key_id="legacy",
            owner_id=user_id,
            rate_limit_per_minute=60,  # Default rate limit
            metadata={"legacy": True}
        )
        
        request.state.api_key_context = context
        
        logger.info(f"Authenticated (legacy): user_id={user_id[:8]}...")
        
        return context


def get_authenticated_user(request: Request) -> str:
    """
    Get authenticated user ID from request context
    
    This is a compatibility wrapper that extracts owner_id from the API key context.
    
    Args:
        request: FastAPI request object
    
    Returns:
        owner_id from API key context
    
    Raises:
        HTTPException: 401 if not authenticated
    """
    if not hasattr(request.state, "api_key_context"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    return request.state.api_key_context.owner_id


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key (legacy function)
    
    Returns:
        32-character hex string
    """
    return secrets.token_hex(32)
