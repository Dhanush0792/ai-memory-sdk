#!/bin/bash
# ============================================================================
# PostgreSQL Backup Script for Memory Infrastructure Phase 2
# ============================================================================
# Creates compressed backups with timestamp
# Uploads to S3 (optional)
# Retains last 30 days of backups
# ============================================================================

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/memory_db_$TIMESTAMP.sql.gz"

# Database connection (from environment or Docker)
DB_CONTAINER="${DB_CONTAINER:-memory-db}"
DB_USER="${DB_USER:-memoryuser}"
DB_NAME="${DB_NAME:-memorydb}"

# S3 configuration (optional)
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-memory-backups}"

# ============================================================================
# Create backup directory
# ============================================================================
mkdir -p "$BACKUP_DIR"

echo "============================================================================"
echo "Memory Infrastructure Backup"
echo "============================================================================"
echo "Timestamp: $TIMESTAMP"
echo "Backup file: $BACKUP_FILE"
echo "============================================================================"

# ============================================================================
# Create backup
# ============================================================================
echo "Creating backup..."

if [ -n "$DB_CONTAINER" ]; then
    # Docker-based backup
    docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"
else
    # Direct backup
    pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"
fi

# Verify backup
if [ $? -eq 0 ] && [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Backup successful: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "✗ Backup failed"
    exit 1
fi

# ============================================================================
# Upload to S3 (optional)
# ============================================================================
if [ -n "$S3_BUCKET" ]; then
    echo "Uploading to S3..."
    aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/$S3_PREFIX/memory_db_$TIMESTAMP.sql.gz"
    
    if [ $? -eq 0 ]; then
        echo "✓ Uploaded to S3: s3://$S3_BUCKET/$S3_PREFIX/memory_db_$TIMESTAMP.sql.gz"
    else
        echo "⚠ S3 upload failed (backup still available locally)"
    fi
fi

# ============================================================================
# Cleanup old backups
# ============================================================================
echo "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "memory_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete

REMAINING_BACKUPS=$(find "$BACKUP_DIR" -name "memory_db_*.sql.gz" | wc -l)
echo "✓ Cleanup complete. Remaining backups: $REMAINING_BACKUPS"

echo "============================================================================"
echo "Backup complete"
echo "============================================================================"
