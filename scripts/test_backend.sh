#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PRAMANRX_PYTHON:-"$PROJECT_DIR/backend/.venv/bin/python"}

cd "$PROJECT_DIR"
exec "$PYTHON_BIN" -m pytest -q backend/tests
