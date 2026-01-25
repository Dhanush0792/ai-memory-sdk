"""
Automated Backup Script
Run this script daily via cron/Task Scheduler
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.backup_manager import BackupManager
from datetime import datetime


def run_automated_backup():
    """
    Run automated backup with retention policy.
    
    This script:
    1. Creates a new backup
    2. Cleans up old backups
    3. Logs the result
    """
    print("=" * 80)
    print(f"  🤖 Automated Backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    try:
        # Initialize backup manager
        manager = BackupManager(
            use_s3=os.getenv('USE_S3_BACKUPS', 'false').lower() == 'true'
        )
        
        # Create backup
        print("📦 Creating backup...")
        metadata = manager.create_backup(compress=True)
        
        print(f"✅ Backup created successfully!")
        print(f"   Name: {metadata['name']}")
        print(f"   Size: {metadata['size_mb']:.2f} MB")
        print()
        
        # Cleanup old backups
        print("🧹 Cleaning up old backups...")
        deleted = manager.cleanup_old_backups(
            keep_days=7,      # Keep all backups from last 7 days
            keep_weekly=4,    # Keep 4 weekly backups
            keep_monthly=12   # Keep 12 monthly backups
        )
        print()
        
        # List current backups
        backups = manager.list_backups()
        print(f"📊 Current backups: {len(backups)}")
        total_size = sum(b['size_mb'] for b in backups)
        print(f"   Total size: {total_size:.2f} MB")
        print()
        
        print("=" * 80)
        print("  ✅ AUTOMATED BACKUP COMPLETE")
        print("=" * 80)
        print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 80)
        print("  ❌ AUTOMATED BACKUP FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_automated_backup()
    sys.exit(0 if success else 1)
