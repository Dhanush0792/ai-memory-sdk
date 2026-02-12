#!/bin/bash
# ============================================================================
# PostgreSQL Restore Script for Memory Infrastructure Phase 2
# ============================================================================
# Restores database from backup file
# Stops application during restore
# ============================================================================

set -e

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: ./restore_postgres.sh <backup_file>"
    echo ""
    echo "Example:"
    echo "  ./restore_postgres.sh /backups/memory_db_20260211_120000.sql.gz"
    echo ""
    echo "Available backups:"
    find /backups -name "memory_db_*.sql.gz" -type f | sort -r | head -10
    exit 1
fi

BACKUP_FILE="$1"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "✗ Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Configuration
DB_CONTAINER="${DB_CONTAINER:-memory-db}"
DB_USER="${DB_USER:-memoryuser}"
DB_NAME="${DB_NAME:-memorydb}"
APP_CONTAINER="${APP_CONTAINER:-memory-app}"

echo "============================================================================"
echo "Memory Infrastructure Restore"
echo "============================================================================"
echo "Backup file: $BACKUP_FILE"
echo "Database: $DB_NAME"
echo "============================================================================"
echo ""
echo "⚠ WARNING: This will OVERWRITE the current database!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# ============================================================================
# Stop application
# ============================================================================
echo "Stopping application..."
if docker ps | grep -q "$APP_CONTAINER"; then
    docker stop "$APP_CONTAINER"
    echo "✓ Application stopped"
else
    echo "⚠ Application not running"
fi

# ============================================================================
# Drop and recreate database
# ============================================================================
echo "Dropping existing database..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"
echo "✓ Database recreated"

# ============================================================================
# Restore backup
# ============================================================================
echo "Restoring backup..."
gunzip < "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" "$DB_NAME"

if [ $? -eq 0 ]; then
    echo "✓ Restore successful"
else
    echo "✗ Restore failed"
    exit 1
fi

# ============================================================================
# Restart application
# ============================================================================
echo "Starting application..."
docker start "$APP_CONTAINER"
echo "✓ Application started"

echo "============================================================================"
echo "Restore complete"
echo "============================================================================"
