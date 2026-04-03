#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/app}"
UPLOAD_DIR="${UPLOAD_DIR:-$APP_DIR/uploads}"
OUTPUT_DIR="${OUTPUT_DIR:-$APP_DIR/outputs}"
LOG_DIR="${LOG_DIR:-$APP_DIR/logs}"
CLEANUP_LOG="${CLEANUP_LOG:-$LOG_DIR/cleanup.log}"

mkdir -p "$LOG_DIR"

ts() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  printf '%s [cleanup] %s\n' "$(ts)" "$1" >> "$CLEANUP_LOG"
}

clean_dir_keep_gitkeep() {
  target="$1"
  [ -d "$target" ] || return 0
  find "$target" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
}

log "start"
clean_dir_keep_gitkeep "$UPLOAD_DIR"
clean_dir_keep_gitkeep "$OUTPUT_DIR"
find "$LOG_DIR" -mindepth 1 ! -name '.gitkeep' ! -name 'cleanup.log' -exec rm -rf {} +
find "$APP_DIR" -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -prune -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.tmp' -o -name '*.swp' \) -delete 2>/dev/null || true
log "done"
