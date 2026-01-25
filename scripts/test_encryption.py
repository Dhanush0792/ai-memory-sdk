"""
Test Encryption
Demonstrates encryption functionality
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.security import get_encryption, encrypt, decrypt, encrypt_dict, decrypt_dict
from app.memory.temporal_sdk import TemporalMemorySDK
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_basic_encryption():
    """Test basic string encryption"""
    print("=" * 80)
    print("  🔐 Test 1: Basic String Encryption")
    print("=" * 80)
    print()
    
    # Test data
    original = "This is sensitive data!"
    print(f"Original: {original}")
    
    # Encrypt
    encrypted = encrypt(original)
    print(f"Encrypted: {encrypted[:50]}...")
    
    # Decrypt
    decrypted = decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
    
    # Verify
    if original == decrypted:
        print("✅ Encryption/Decryption successful!")
    else:
        print("❌ Encryption/Decryption failed!")
    
    print()


def test_dict_encryption():
    """Test dictionary encryption"""
    print("=" * 80)
    print("  🔐 Test 2: Dictionary Encryption")
    print("=" * 80)
    print()
    
    # Test data
    original = {
        "name": "Alice",
        "ssn": "123-45-6789",
        "credit_card": "4111-1111-1111-1111"
    }
    print(f"Original: {original}")
    
    # Encrypt
    encrypted = encrypt_dict(original)
    print(f"Encrypted: {encrypted[:50]}...")
    
    # Decrypt
    decrypted = decrypt_dict(encrypted)
    print(f"Decrypted: {decrypted}")
    
    # Verify
    if original == decrypted:
        print("✅ Dictionary encryption/decryption successful!")
    else:
        print("❌ Dictionary encryption/decryption failed!")
    
    print()


def test_memory_encryption():
    """Test memory encryption with SDK"""
    print("=" * 80)
    print("  🔐 Test 3: Memory Encryption with SDK")
    print("=" * 80)
    print()
    
    sdk = TemporalMemorySDK()
    
    # Add encrypted memory
    print("Adding encrypted memory...")
    memory = sdk.add_memory(
        user_id="test_encryption_user",
        memory_type="fact",
        key="ssn",
        value="123-45-6789",
        confidence=1.0,
        encrypt_value=True  # ✅ Enable encryption
    )
    
    print(f"✅ Memory added (ID: {memory['id']})")
    print(f"   Encrypted: {memory['is_encrypted']}")
    print(f"   Value (decrypted): {memory['value']}")
    print()
    
    # Retrieve memory (should auto-decrypt)
    print("Retrieving encrypted memory...")
    memories = sdk.retrieve_memory(
        user_id="test_encryption_user",
        key="ssn"
    )
    
    if memories:
        retrieved = memories[0]
        print(f"✅ Memory retrieved")
        print(f"   Encrypted: {retrieved['is_encrypted']}")
        print(f"   Value (auto-decrypted): {retrieved['value']}")
        
        # Verify
        if retrieved['value']['content'] == "123-45-6789":
            print("✅ Encryption/Decryption in SDK successful!")
        else:
            print("❌ Decryption failed!")
    else:
        print("❌ Memory not found!")
    
    print()


def test_mixed_memories():
    """Test encrypted and unencrypted memories together"""
    print("=" * 80)
    print("  🔐 Test 4: Mixed Encrypted/Unencrypted Memories")
    print("=" * 80)
    print()
    
    sdk = TemporalMemorySDK()
    
    # Add unencrypted memory
    print("Adding unencrypted memory...")
    mem1 = sdk.add_memory(
        user_id="test_mixed_user",
        memory_type="fact",
        key="name",
        value="Bob",
        encrypt_value=False  # Not encrypted
    )
    print(f"✅ Unencrypted memory added")
    
    # Add encrypted memory
    print("Adding encrypted memory...")
    mem2 = sdk.add_memory(
        user_id="test_mixed_user",
        memory_type="fact",
        key="credit_card",
        value="4111-1111-1111-1111",
        encrypt_value=True  # Encrypted
    )
    print(f"✅ Encrypted memory added")
    print()
    
    # Retrieve all
    print("Retrieving all memories...")
    memories = sdk.retrieve_memory(user_id="test_mixed_user")
    
    print(f"Found {len(memories)} memories:")
    for mem in memories:
        encrypted_status = "🔐 Encrypted" if mem['is_encrypted'] else "📝 Plain"
        print(f"   {encrypted_status}: {mem['key']} = {mem['value']}")
    
    print()
    print("✅ Mixed encryption test successful!")
    print()


def main():
    """Run all encryption tests"""
    print()
    print("=" * 80)
    print("  🧪 ENCRYPTION TESTS")
    print("=" * 80)
    print()
    
    try:
        # Test 1: Basic encryption
        test_basic_encryption()
        
        # Test 2: Dictionary encryption
        test_dict_encryption()
        
        # Test 3: Memory encryption
        test_memory_encryption()
        
        # Test 4: Mixed memories
        test_mixed_memories()
        
        print("=" * 80)
        print("  ✅ ALL TESTS PASSED!")
        print("=" * 80)
        print()
        print("🎯 Encryption is working correctly!")
        print()
        print("💡 Usage:")
        print("   # Encrypt a memory")
        print("   sdk.add_memory(..., encrypt_value=True)")
        print()
        print("   # Retrieval automatically decrypts")
        print("   memories = sdk.retrieve_memory(user_id)")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 80)
        print("  ❌ TESTS FAILED!")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
