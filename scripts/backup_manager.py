"""
Automated Backup Manager
Comprehensive backup solution for TruthKeeper with S3 support
"""

import os
import sys
import subprocess
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BackupManager:
    """
    Manage database backups with multiple storage options.
    
    Features:
    - Local backups
    - S3 backups (optional)
    - Automatic compression
    - Retention policies
    - Backup verification
    - Restore functionality
    """
    
    def __init__(
        self,
        backup_dir: Optional[str] = None,
        use_s3: bool = False,
        s3_bucket: Optional[str] = None
    ):
        """
        Initialize backup manager.
        
        Args:
            backup_dir: Local backup directory (default: ./backups)
            use_s3: Whether to use S3 for backups
            s3_bucket: S3 bucket name
        """
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not set in environment")
        
        # Local backup directory
        self.backup_dir = Path(backup_dir or project_root / "backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # S3 configuration
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket or os.getenv('BACKUP_S3_BUCKET')
        
        if self.use_s3:
            try:
                import boto3
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_REGION', 'us-east-1')
                )
            except ImportError:
                print("⚠️  boto3 not installed. Install with: pip install boto3")
                self.use_s3 = False
    
    def create_backup(
        self,
        backup_name: Optional[str] = None,
        compress: bool = True
    ) -> Dict[str, any]:
        """
        Create a database backup.
        
        Args:
            backup_name: Custom backup name (default: timestamp)
            compress: Whether to compress the backup
            
        Returns:
            Backup metadata dict
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = backup_name or f"backup_{timestamp}"
        
        # File paths
        sql_file = self.backup_dir / f"{backup_name}.sql"
        compressed_file = self.backup_dir / f"{backup_name}.sql.gz"
        
        print(f"📦 Creating backup: {backup_name}")
        print(f"   Database: {self.db_url.split('@')[1] if '@' in self.db_url else 'local'}")
        
        try:
            # Create backup using pg_dump
            print("   Running pg_dump...")
            
            # Set environment variable for pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_url.split(':')[2].split('@')[0] if ':' in self.db_url else ''
            
            result = subprocess.run(
                [
                    'pg_dump',
                    '--dbname=' + self.db_url,
                    '--file=' + str(sql_file),
                    '--no-owner',
                    '--no-acl',
                    '--clean',
                    '--if-exists'
                ],
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Get file size
            size_mb = sql_file.stat().st_size / (1024 * 1024)
            print(f"   ✅ Backup created: {size_mb:.2f} MB")
            
            # Compress if requested
            if compress:
                print("   Compressing...")
                with open(sql_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed file
                sql_file.unlink()
                
                compressed_size_mb = compressed_file.stat().st_size / (1024 * 1024)
                compression_ratio = (1 - compressed_size_mb / size_mb) * 100
                print(f"   ✅ Compressed: {compressed_size_mb:.2f} MB ({compression_ratio:.1f}% reduction)")
                
                final_file = compressed_file
            else:
                final_file = sql_file
            
            # Upload to S3 if enabled
            s3_key = None
            if self.use_s3 and self.s3_bucket:
                print("   Uploading to S3...")
                s3_key = f"backups/{final_file.name}"
                
                self.s3_client.upload_file(
                    str(final_file),
                    self.s3_bucket,
                    s3_key
                )
                print(f"   ✅ Uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            
            # Create metadata
            metadata = {
                'name': backup_name,
                'timestamp': timestamp,
                'file': str(final_file),
                'size_mb': final_file.stat().st_size / (1024 * 1024),
                'compressed': compress,
                's3_key': s3_key,
                's3_bucket': self.s3_bucket if s3_key else None,
                'created_at': datetime.now().isoformat()
            }
            
            # Save metadata
            metadata_file = self.backup_dir / f"{backup_name}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print()
            print("✅ Backup complete!")
            print(f"   File: {final_file}")
            print(f"   Size: {metadata['size_mb']:.2f} MB")
            if s3_key:
                print(f"   S3: s3://{self.s3_bucket}/{s3_key}")
            print()
            
            return metadata
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            # Clean up partial files
            if sql_file.exists():
                sql_file.unlink()
            if compressed_file.exists():
                compressed_file.unlink()
            raise
    
    def list_backups(self, include_s3: bool = False) -> List[Dict]:
        """
        List all available backups.
        
        Args:
            include_s3: Whether to include S3 backups
            
        Returns:
            List of backup metadata dicts
        """
        backups = []
        
        # Local backups
        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    metadata['location'] = 'local'
                    backups.append(metadata)
            except:
                pass
        
        # S3 backups
        if include_s3 and self.use_s3 and self.s3_bucket:
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix='backups/'
                )
                
                for obj in response.get('Contents', []):
                    backups.append({
                        'name': obj['Key'].split('/')[-1],
                        'size_mb': obj['Size'] / (1024 * 1024),
                        's3_key': obj['Key'],
                        's3_bucket': self.s3_bucket,
                        'created_at': obj['LastModified'].isoformat(),
                        'location': 's3'
                    })
            except:
                pass
        
        # Sort by creation time
        backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return backups
    
    def restore_backup(
        self,
        backup_name: str,
        confirm: bool = False
    ) -> bool:
        """
        Restore from a backup.
        
        Args:
            backup_name: Name of backup to restore
            confirm: Must be True to proceed (safety check)
            
        Returns:
            True if successful
        """
        if not confirm:
            print("⚠️  WARNING: This will overwrite the current database!")
            print("   Set confirm=True to proceed")
            return False
        
        print(f"🔄 Restoring backup: {backup_name}")
        
        # Find backup file
        sql_file = self.backup_dir / f"{backup_name}.sql"
        gz_file = self.backup_dir / f"{backup_name}.sql.gz"
        
        if gz_file.exists():
            print("   Decompressing...")
            with gzip.open(gz_file, 'rb') as f_in:
                with open(sql_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        elif not sql_file.exists():
            # Try to download from S3
            if self.use_s3 and self.s3_bucket:
                print("   Downloading from S3...")
                s3_key = f"backups/{backup_name}.sql.gz"
                
                self.s3_client.download_file(
                    self.s3_bucket,
                    s3_key,
                    str(gz_file)
                )
                
                # Decompress
                with gzip.open(gz_file, 'rb') as f_in:
                    with open(sql_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                raise FileNotFoundError(f"Backup not found: {backup_name}")
        
        try:
            print("   Restoring database...")
            
            result = subprocess.run(
                [
                    'psql',
                    self.db_url,
                    '-f', str(sql_file)
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Restore failed: {result.stderr}")
            
            print()
            print("✅ Restore complete!")
            print()
            
            # Clean up decompressed file
            if gz_file.exists() and sql_file.exists():
                sql_file.unlink()
            
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            raise
    
    def cleanup_old_backups(
        self,
        keep_days: int = 30,
        keep_weekly: int = 12,
        keep_monthly: int = 12
    ) -> int:
        """
        Clean up old backups based on retention policy.
        
        Args:
            keep_days: Keep all backups from last N days
            keep_weekly: Keep N weekly backups
            keep_monthly: Keep N monthly backups
            
        Returns:
            Number of backups deleted
        """
        print(f"🧹 Cleaning up old backups...")
        print(f"   Policy: {keep_days} days, {keep_weekly} weeks, {keep_monthly} months")
        
        backups = self.list_backups()
        now = datetime.now()
        deleted = 0
        
        # Categorize backups
        daily = []
        weekly = []
        monthly = []
        
        for backup in backups:
            created = datetime.fromisoformat(backup['created_at'])
            age_days = (now - created).days
            
            if age_days <= keep_days:
                daily.append(backup)
            elif age_days <= keep_days + (keep_weekly * 7):
                weekly.append(backup)
            else:
                monthly.append(backup)
        
        # Keep only specified number of weekly/monthly
        to_delete = weekly[keep_weekly:] + monthly[keep_monthly:]
        
        for backup in to_delete:
            try:
                # Delete local file
                if backup.get('file'):
                    Path(backup['file']).unlink(missing_ok=True)
                
                # Delete metadata
                metadata_file = self.backup_dir / f"{backup['name']}.json"
                metadata_file.unlink(missing_ok=True)
                
                # Delete from S3
                if backup.get('s3_key') and self.use_s3:
                    self.s3_client.delete_object(
                        Bucket=backup['s3_bucket'],
                        Key=backup['s3_key']
                    )
                
                deleted += 1
                print(f"   Deleted: {backup['name']}")
                
            except Exception as e:
                print(f"   Failed to delete {backup['name']}: {e}")
        
        print(f"✅ Cleanup complete: {deleted} backups deleted")
        return deleted
    
    def verify_backup(self, backup_name: str) -> bool:
        """
        Verify a backup file is valid.
        
        Args:
            backup_name: Name of backup to verify
            
        Returns:
            True if valid
        """
        print(f"🔍 Verifying backup: {backup_name}")
        
        # Find backup file
        gz_file = self.backup_dir / f"{backup_name}.sql.gz"
        sql_file = self.backup_dir / f"{backup_name}.sql"
        
        if gz_file.exists():
            try:
                # Try to decompress
                with gzip.open(gz_file, 'rb') as f:
                    f.read(1024)  # Read first 1KB
                print("✅ Backup file is valid")
                return True
            except:
                print("❌ Backup file is corrupted")
                return False
        elif sql_file.exists():
            print("✅ Backup file exists")
            return True
        else:
            print("❌ Backup file not found")
            return False


def main():
    """Interactive backup management"""
    print("=" * 80)
    print("  💾 TruthKeeper Backup Manager")
    print("=" * 80)
    print()
    
    manager = BackupManager()
    
    print("Options:")
    print("  1. Create backup")
    print("  2. List backups")
    print("  3. Restore backup")
    print("  4. Cleanup old backups")
    print("  5. Verify backup")
    print()
    
    choice = input("Choose option (1-5): ").strip()
    
    if choice == "1":
        metadata = manager.create_backup()
        print(f"Backup created: {metadata['name']}")
    
    elif choice == "2":
        backups = manager.list_backups()
        print(f"\nFound {len(backups)} backups:")
        for b in backups:
            print(f"  - {b['name']} ({b['size_mb']:.2f} MB) - {b.get('created_at', 'unknown')}")
    
    elif choice == "3":
        backups = manager.list_backups()
        if not backups:
            print("No backups found!")
            return
        
        print("\nAvailable backups:")
        for i, b in enumerate(backups, 1):
            print(f"  {i}. {b['name']}")
        
        idx = int(input("\nChoose backup number: ")) - 1
        backup_name = backups[idx]['name'].replace('.sql.gz', '').replace('.sql', '')
        
        confirm = input(f"\n⚠️  This will overwrite the current database! Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            manager.restore_backup(backup_name, confirm=True)
    
    elif choice == "4":
        manager.cleanup_old_backups()
    
    elif choice == "5":
        backup_name = input("Backup name: ").strip()
        manager.verify_backup(backup_name)


if __name__ == "__main__":
    main()
