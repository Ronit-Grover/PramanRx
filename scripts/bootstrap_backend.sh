#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PRAMANRX_PYTHON:-python3}
KB_SOURCE=${PRAMANRX_KB_SOURCE:-"$PROJECT_DIR/data/source/kb"}
SYNTHEA_ZIP=${PRAMANRX_SYNTHEA_ZIP:-"$PROJECT_DIR/data/source/synthea_sample_data_csv_apr2020.zip"}

if [ ! -d "$KB_SOURCE" ]; then
    echo "Knowledge source directory not found: $KB_SOURCE" >&2
    echo "Set PRAMANRX_KB_SOURCE to the verified source package." >&2
    exit 1
fi

if [ ! -f "$SYNTHEA_ZIP" ]; then
    echo "Synthea ZIP not found: $SYNTHEA_ZIP" >&2
    echo "Set PRAMANRX_SYNTHEA_ZIP to the downloaded Synthea CSV archive." >&2
    exit 1
fi

cd "$PROJECT_DIR"
"$PYTHON_BIN" scripts/compile_kb.py --source-root "$KB_SOURCE"
"$PYTHON_BIN" scripts/import_synthea.py --zip "$SYNTHEA_ZIP"
