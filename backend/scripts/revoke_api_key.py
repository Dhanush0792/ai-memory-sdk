#!/usr/bin/env python3
"""
CLI Script to Revoke API Keys

Usage:
    python scripts/revoke_api_key.py <key_id>

Example:
    python scripts/revoke_api_key.py 550e8400-e29b-41d4-a716-446655440000
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from api.key_manager import KeyManager


def main():
    parser = argparse.ArgumentParser(
        description='Revoke an API key'
    )
    parser.add_argument(
        'key_id',
        help='UUID of the API key to revoke'
    )
    
    args = parser.parse_args()
    
    try:
        key_manager = KeyManager()
        success = key_manager.revoke_key(args.key_id)
        
        if success:
            print(f"\n✓ API key {args.key_id} has been revoked successfully")
            print("  The key is now inactive and cannot be used for authentication\n")
        else:
            print(f"\n✗ API key {args.key_id} not found or already revoked\n", file=sys.stderr)
            sys.exit(1)
        
    except ConnectionError as e:
        print(f"Database Error: {e}", file=sys.stderr)
        print("\nMake sure DATABASE_URL is set in .env", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
