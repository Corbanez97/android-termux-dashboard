#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PROJECT_DIR="/data/data/com.termux/files/home/projects/android-termux-dashboard"
ECOSYSTEM_FILE="$PROJECT_DIR/ecosystem.config.cjs"
LOG_FILE="$PROJECT_DIR/data/service-watch.log"

mkdir -p "$PROJECT_DIR/data"
touch "$LOG_FILE"

log() {
    printf '[%s] %s\n' "$(date -Iseconds)" "$1" | tee -a "$LOG_FILE"
}

termux-wake-lock >/dev/null 2>&1 || true

if ! pm2 ping >/dev/null 2>&1; then
    log "PM2 daemon was unavailable. Attempting resurrect."
    pm2 resurrect >/dev/null 2>&1 || true
fi

log "Ensuring dashboard-api and wol-api are running from ecosystem config."
pm2 startOrReload "$ECOSYSTEM_FILE" --update-env >/dev/null

log "Saving PM2 process list for boot restore."
pm2 save >/dev/null
