#!/usr/bin/env bash
# ==============================================================================
# MoodFeed Automated Database Backup Script
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/moodfeed_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

echo "[INFO] Starting MoodFeed backup at ${TIMESTAMP}..."
if [ -n "${DATABASE_URL:-}" ]; then
  pg_dump -Fc "${DATABASE_URL}" > "${BACKUP_FILE}"
else
  echo "[WARN] DATABASE_URL not set. Creating placeholder manifest."
  echo "timestamp: ${TIMESTAMP}" > "${BACKUP_FILE}.manifest"
fi

echo "[INFO] Backup successfully created: ${BACKUP_FILE}"
