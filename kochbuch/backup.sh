#!/bin/bash

# Configuration
DB_PATH="/home/moebius/Geheimlabor/kochbuch/db/RezeptDB.db"
BACKUP_DIR="/home/moebius/Geheimlabor/kochbuch/db/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
BACKUP_FILE="$BACKUP_DIR/RezeptDB_$TIMESTAMP.db"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Perform a safe online backup
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Optional: Remove backups older than 30 days to save space
find "$BACKUP_DIR" -name "RezeptDB_*.db" -mtime +30 -delete

