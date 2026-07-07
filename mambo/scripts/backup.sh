#!/usr/bin/env bash
# Daily database backup — run via cron: 0 3 * * * /app/scripts/backup.sh
# Uploads a compressed pg_dump to a configurable remote (S3, rsync target, etc.).
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/mambo}"
REMOTE="${REMOTE:-}"  # e.g. s3://my-bucket/mambo-backups/ or user@host:/backups/
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATABASE_URL="${DATABASE_URL:?set DATABASE_URL}"
TIMESTAMP=$(date +%Y-%m-%dT%H%M%S)
mkdir -p "$BACKUP_DIR"

DUMP_FILE="${BACKUP_DIR}/mambo-${TIMESTAMP}.sql.gz"
pg_dump "$DATABASE_URL" | gzip > "$DUMP_FILE"

# Upload if remote configured
if [ -n "$REMOTE" ]; then
    if [[ "$REMOTE" == s3://* ]]; then
        aws s3 cp "$DUMP_FILE" "$REMOTE$(basename "$DUMP_FILE")" --sse AES256
    else
        rsync -az "$DUMP_FILE" "$REMOTE$(basename "$DUMP_FILE")"
    fi
fi

# Cleanup old backups
find "$BACKUP_DIR" -name "mambo-*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "[backup] $(date) — saved ${DUMP_FILE} ($(du -h "$DUMP_FILE" | cut -f1))"
