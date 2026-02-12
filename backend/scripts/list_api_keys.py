#!/usr/bin/env python3
"""
CLI Script to List API Keys for an Owner

Usage:
    python scripts/list_api_keys.py <owner_id>

Example:
    python scripts/list_api_keys.py customer_123
"""

import sys
import os
import argparse
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from api.key_manager import KeyManager


def main():
    parser = argparse.ArgumentParser(
        description='List all API keys for an owner'
    )
    parser.add_argument(
        'owner_id',
        help='Owner identifier (customer/app ID)'
    )
    
    args = parser.parse_args()
    
    try:
        key_manager = KeyManager()
        keys = key_manager.list_keys(args.owner_id)
        
        if not keys:
            print(f"\nNo API keys found for owner: {args.owner_id}\n")
            return
        
        print(f"\n{'='*80}")
        print(f"API KEYS FOR OWNER: {args.owner_id}")
        print(f"{'='*80}\n")
        
        for i, key in enumerate(keys, 1):
            status = "✓ ACTIVE" if key['is_active'] else "✗ REVOKED"
            
            print(f"Key #{i}")
            print(f"  Key ID:       {key['key_id']}")
            print(f"  Status:       {status}")
            print(f"  Rate Limit:   {key['rate_limit_per_minute']} requests/minute")
            print(f"  Created:      {key['created_at']}")
            
            if key['last_used_at']:
                print(f"  Last Used:    {key['last_used_at']}")
            else:
                print(f"  Last Used:    Never")
            
            if key['revoked_at']:
                print(f"  Revoked:      {key['revoked_at']}")
            
            if key['metadata']:
                print(f"  Metadata:     {json.dumps(key['metadata'])}")
            
            print()
        
        print(f"{'='*80}")
        print(f"Total: {len(keys)} key(s)")
        print(f"{'='*80}\n")
        
    except ConnectionError as e:
        print(f"Database Error: {e}", file=sys.stderr)
        print("\nMake sure DATABASE_URL is set in .env", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
