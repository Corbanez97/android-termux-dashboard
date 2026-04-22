#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REMOTE_HOST="${REMOTE_HOST:-android-termux}"
REMOTE_DIR="${REMOTE_DIR:-projects/android-termux-dashboard}"
REMOTE_STAGE="${REMOTE_DIR}.incoming"

echo "Deploying $PROJECT_ROOT to $REMOTE_HOST:$REMOTE_DIR"

tar \
  --exclude=".git" \
  --exclude=".venv" \
  --exclude="data" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  --exclude="*.pyo" \
  -C "$PROJECT_ROOT" \
  -cf - . | ssh "$REMOTE_HOST" "
    set -euo pipefail
    mkdir -p \"$REMOTE_STAGE\" \"$REMOTE_DIR\"
    find \"$REMOTE_STAGE\" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    tar -xf - -C \"$REMOTE_STAGE\"

    rm -rf \
      \"$REMOTE_DIR/app.py\" \
      \"$REMOTE_DIR/README.md\" \
      \"$REMOTE_DIR/requirements.txt\" \
      \"$REMOTE_DIR/ecosystem.config.cjs\" \
      \"$REMOTE_DIR/dashboard\" \
      \"$REMOTE_DIR/scripts\"

    cp -a \"$REMOTE_STAGE\"/. \"$REMOTE_DIR\"/

    cd \"$REMOTE_DIR\"
    chmod +x scripts/*.sh

    if [ ! -d .venv ]; then
      python -m venv .venv
    fi

    .venv/bin/pip install -r requirements.txt
    ./scripts/ensure-services.sh
  "

echo "Deployment complete."
