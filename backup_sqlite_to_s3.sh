#!/bin/bash

set -e

PROJECT_DIR="/home/ubuntu/oceanclouds-crm"
ENV_FILE="$PROJECT_DIR/.env"

DB_PATH="$PROJECT_DIR/db.sqlite3"
BACKUP_DIR="/home/ubuntu/backups/sqlite"

DATE_TIME=$(TZ="Asia/Kolkata" date +"%Y-%m-%d_%H-%M-%S")
BACKUP_NAME="db_backup_$DATE_TIME.sqlite3"
COMPRESSED_NAME="$BACKUP_NAME.gz"

LOG_FILE="/home/ubuntu/backups/sqlite/backup.log"
LOCK_FILE="/tmp/oceanclouds_sqlite_backup.lock"


# Prevent two backup jobs from running at the same time
exec 200>"$LOCK_FILE"
flock -n 200 || {
    echo "[$DATE_TIME] Backup already running. Exiting." >> "$LOG_FILE"
    exit 1
}

echo "[$DATE_TIME] Backup started" >> "$LOG_FILE"

# Load .env variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Check backup enabled
if [ "$DB_BACKUP" != "True" ] && [ "$DB_BACKUP" != "true" ]; then
    echo "[$DATE_TIME] DB_BACKUP is not True. Skipping backup." >> "$LOG_FILE"
    exit 0
fi

# Check DB exists
if [ ! -f "$DB_PATH" ]; then
    echo "[$DATE_TIME] ERROR: SQLite DB not found at $DB_PATH" >> "$LOG_FILE"
    exit 1
fi

# Check bucket variable
if [ -z "$S3_BACKUP_BUCKET" ]; then
    echo "[$DATE_TIME] ERROR: S3_BACKUP_BUCKET not set in .env" >> "$LOG_FILE"
    exit 1
fi

# Create safe SQLite backup
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/$BACKUP_NAME'"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_NAME"

# Upload to S3
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_SESSION_TOKEN
unset AWS_PROFILE
unset AWS_DEFAULT_PROFILE

aws s3 cp "$BACKUP_DIR/$COMPRESSED_NAME" \
    "s3://$S3_BACKUP_BUCKET/sqlite-backups/$COMPRESSED_NAME" \
    --region "${AWS_REGION:-ap-south-1}"

# Remove local backup files older than 14 days
find "$BACKUP_DIR" -name "*.gz" -type f -mtime +14 -delete

echo "[$DATE_TIME] Backup completed and uploaded to S3: sqlite-backups/$COMPRESSED_NAME" >> "$LOG_FILE"
