#!/usr/bin/env bash
# ==============================================================================
# MoodFeed Database Restore Drill Script
# ==============================================================================
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <path_to_backup_file.dump>"
  exit 1
fi

BACKUP_FILE="$1"
echo "[INFO] Starting database restore from ${BACKUP_FILE}..."

if [ -n "${DATABASE_URL:-}" ]; then
  pg_restore --clean --if-exists -d "${DATABASE_URL}" "${BACKUP_FILE}"
  echo "[INFO] Restore completed successfully."
else
  echo "[WARN] DATABASE_URL not configured. Restore drill simulated."
fi
