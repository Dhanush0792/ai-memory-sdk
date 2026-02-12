#!/usr/bin/env python3
"""
CLI Script to Generate API Keys

Usage:
    python scripts/generate_api_key.py <owner_id> [--rate-limit RATE] [--metadata JSON]

Examples:
    python scripts/generate_api_key.py customer_123
    python scripts/generate_api_key.py customer_456 --rate-limit 120
    python scripts/generate_api_key.py customer_789 --rate-limit 300 --metadata '{"plan": "pro"}'
"""

import sys
import os
import json
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from api.key_manager import KeyManager


def main():
    parser = argparse.ArgumentParser(
        description='Generate a new API key for the AI Memory SDK'
    )
    parser.add_argument(
        'owner_id',
        help='Owner identifier (customer/app ID)'
    )
    parser.add_argument(
        '--rate-limit',
        type=int,
        default=60,
        help='Rate limit per minute (default: 60)'
    )
    parser.add_argument(
        '--metadata',
        type=str,
        default='{}',
        help='JSON metadata (e.g., \'{"plan": "pro"}\')'
    )
    
    args = parser.parse_args()
    
    # Parse metadata
    try:
        metadata = json.loads(args.metadata)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in metadata: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate rate limit
    if args.rate_limit < 1 or args.rate_limit > 10000:
        print("Error: Rate limit must be between 1 and 10000", file=sys.stderr)
        sys.exit(1)
    
    # Create key
    try:
        key_manager = KeyManager()
        result = key_manager.create_api_key(
            owner_id=args.owner_id,
            rate_limit_per_minute=args.rate_limit,
            metadata=metadata
        )
        
        print("\n" + "="*60)
        print("API KEY GENERATED SUCCESSFULLY")
        print("="*60)
        print(f"\nAPI Key (SAVE THIS - IT WILL NOT BE SHOWN AGAIN):")
        print(f"  {result['api_key']}")
        print(f"\nKey ID:")
        print(f"  {result['key_id']}")
        print(f"\nOwner ID:")
        print(f"  {result['owner_id']}")
        print(f"\nRate Limit:")
        print(f"  {result['rate_limit_per_minute']} requests/minute")
        print(f"\nCreated At:")
        print(f"  {result['created_at']}")
        
        if metadata:
            print(f"\nMetadata:")
            print(f"  {json.dumps(metadata, indent=2)}")
        
        print("\n" + "="*60)
        print("SECURITY WARNING")
        print("="*60)
        print("- Store this API key securely")
        print("- Never commit it to version control")
        print("- Never expose it in frontend code")
        print("- This is the ONLY time you will see the plaintext key")
        print("="*60 + "\n")
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
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
