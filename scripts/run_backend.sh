#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PRAMANRX_PYTHON:-"$PROJECT_DIR/backend/.venv/bin/python"}
HOST=${PRAMANRX_HOST:-127.0.0.1}
PORT=${PRAMANRX_PORT:-8000}

cd "$PROJECT_DIR"
exec "$PYTHON_BIN" -m uvicorn backend.app.main:app --host "$HOST" --port "$PORT"
