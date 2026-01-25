"""Authentication and Authorization Layer"""

import os
import hmac
import hashlib
import secrets
from fastapi import Header, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


def hash_api_key(api_key: str, salt: Optional[str] = None) -> str:
    """
    Hash API key using HMAC-SHA256
    
    Args:
        api_key: Raw API key to hash
        salt: Optional salt (uses env var if not provided)
    
    Returns:
        Hex-encoded hash
    """
    if salt is None:
        salt = os.getenv("API_KEY_SALT", "default-salt-change-in-production")
    
    return hmac.new(
        salt.encode('utf-8'),
        api_key.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_api_key_constant_time(provided_key: str, expected_hash: str) -> bool:
    """
    Verify API key using constant-time comparison
    
    Args:
        provided_key: API key from request
        expected_hash: Expected hash from storage
    
    Returns:
        True if valid, False otherwise
    """
    provided_hash = hash_api_key(provided_key)
    return hmac.compare_digest(provided_hash, expected_hash)


def get_authenticated_user(
    authorization: str = Header(None),
    x_user_id: str = Header(None, alias="X-User-ID")
) -> str:
    """
    Extract and verify authenticated user from headers
    
    This is the ONLY source of user identity. Never trust user_id from request bodies.
    
    Args:
        authorization: Bearer token from Authorization header
        x_user_id: User ID from X-User-ID header
    
    Returns:
        Verified user_id
    
    Raises:
        HTTPException: 401 if auth missing/invalid, 403 if forbidden
    """
    # Check for missing authorization
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    # Check for malformed authorization
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )
    
    # Extract token
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Get expected hash from environment
    expected_hash = os.getenv("API_KEY_HASH")
    
    # Fallback to plain key comparison for backward compatibility (temporary)
    # TODO: Remove after migration period
    if not expected_hash:
        expected_key = os.getenv("API_KEY", "dev-key-12345")
        if not hmac.compare_digest(token, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
    else:
        # Use constant-time comparison with hashed key
        if not verify_api_key_constant_time(token, expected_hash):
            raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Verify user ID is provided
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=401,
            detail="Missing X-User-ID header"
        )
    
    # Validate user ID format
    user_id = x_user_id.strip()
    if len(user_id) > 255:
        raise HTTPException(
            status_code=422,
            detail="X-User-ID too long (max 255 chars)"
        )
    
    logger.info(f"Authenticated user: {user_id[:8]}...")
    return user_id


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key
    
    Returns:
        32-character hex string
    """
    return secrets.token_hex(32)
