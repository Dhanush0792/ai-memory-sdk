"""SDK Exception Classes"""

class MemorySDKError(Exception):
    """Base exception for all SDK errors"""
    pass

class MemoryAuthError(MemorySDKError):
    """Authentication or authorization failed"""
    pass

class MemoryNotFoundError(MemorySDKError):
    """Requested resource not found"""
    pass

class MemoryValidationError(MemorySDKError):
    """Invalid input or validation failed"""
    pass

class MemoryAPIError(MemorySDKError):
    """Server or API error"""
    pass
