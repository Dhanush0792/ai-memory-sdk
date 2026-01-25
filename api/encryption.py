"""Field-level encryption utility for memory content"""

import os
import base64
from cryptography.fernet import Fernet
from typing import Optional

class EncryptionService:
    """Handles encryption/decryption of sensitive memory data"""
    
    def __init__(self):
        """Initialize with key from environment"""
        key = os.getenv("ENCRYPTION_KEY")
        
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable required")
        
        try:
            # Fernet expects base64-encoded 32-byte key
            self.cipher = Fernet(key.encode())
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY format: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string, return base64-encoded ciphertext"""
        if not plaintext:
            return plaintext
        
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            # Fail closed - do not store plaintext
            raise RuntimeError(f"Encryption failed: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext, return plaintext"""
        if not ciphertext:
            return ciphertext
        
        try:
            # Try decryption first (encrypted data)
            encrypted_bytes = base64.b64decode(ciphertext.encode('utf-8'))
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception:
            # Log decryption failure WITHOUT exception details (may contain key material)
            import logging
            logging.warning("Decryption failed - possible key rotation or legacy plaintext data")
            # Gracefully handle legacy plaintext data
            return ciphertext
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key for ENCRYPTION_KEY"""
        return Fernet.generate_key().decode('utf-8')
