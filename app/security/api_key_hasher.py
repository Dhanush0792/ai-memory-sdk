"""
Secure API key hashing using Argon2id.
Replaces SHA-256 with salted, configurable work factor hashing.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from app.observability import logger


class APIKeyHasher:
    """
    Secure API key hasher using Argon2id.
    
    Features:
    - Salted hashing (automatic)
    - Configurable work factor
    - Rainbow table resistant
    - Timing attack resistant
    """
    
    def __init__(
        self,
        time_cost: int = 2,
        memory_cost: int = 65536,  # 64 MB
        parallelism: int = 1
    ):
        """
        Initialize Argon2 hasher.
        
        Args:
            time_cost: Number of iterations
            memory_cost: Memory usage in KiB
            parallelism: Number of parallel threads
        """
        self.hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=32,
            salt_len=16
        )
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Hash API key using Argon2id.
        
        Args:
            api_key: Raw API key
            
        Returns:
            Argon2 hash string (includes salt)
        """
        try:
            hash_str = self.hasher.hash(api_key)
            logger.debug("api_key_hashed")
            return hash_str
        except Exception as e:
            logger.error("api_key_hash_failed", error=str(e))
            raise
    
    def verify_api_key(self, api_key: str, hash_str: str) -> bool:
        """
        Verify API key against hash.
        
        Args:
            api_key: Raw API key to verify
            hash_str: Stored Argon2 hash
            
        Returns:
            True if key matches hash
        """
        try:
            self.hasher.verify(hash_str, api_key)
            
            # Check if rehashing needed (parameters changed)
            if self.hasher.check_needs_rehash(hash_str):
                logger.info("api_key_needs_rehash")
            
            return True
        except VerifyMismatchError:
            logger.warning("api_key_verification_failed")
            return False
        except InvalidHash:
            logger.error("invalid_api_key_hash")
            return False
        except Exception as e:
            logger.error("api_key_verify_error", error=str(e))
            return False
    
    def needs_rehash(self, hash_str: str) -> bool:
        """
        Check if hash needs to be regenerated with new parameters.
        
        Args:
            hash_str: Stored Argon2 hash
            
        Returns:
            True if rehash recommended
        """
        try:
            return self.hasher.check_needs_rehash(hash_str)
        except Exception:
            return True


# Global hasher instance
api_key_hasher = APIKeyHasher(
    time_cost=2,      # 2 iterations (production: 3-4)
    memory_cost=65536, # 64 MB (production: 102400 = 100 MB)
    parallelism=1      # Single thread
)


def hash_api_key(api_key: str) -> str:
    """Hash API key using Argon2id."""
    return api_key_hasher.hash_api_key(api_key)


def verify_api_key(api_key: str, hash_str: str) -> bool:
    """Verify API key against Argon2 hash."""
    return api_key_hasher.verify_api_key(api_key, hash_str)
