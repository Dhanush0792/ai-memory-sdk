"""
Secure AI Memory SDK
Enterprise-grade memory for LLM applications
"""

__version__ = "1.0.0"
__author__ = "AI Memory Team"
__license__ = "MIT"

from sdk import MemorySDK
from sdk.exceptions import (
    MemoryAuthError,
    MemoryNotFoundError,
    MemoryValidationError,
    MemoryAPIError
)

__all__ = [
    "MemorySDK",
    "MemoryAuthError",
    "MemoryNotFoundError",
    "MemoryValidationError",
    "MemoryAPIError"
]
