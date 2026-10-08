#!/usr/bin/env python3
"""Clear prototype audit records while retaining imported synthetic patient data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import Database  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "data/runtime/pramanrx.sqlite3")
    args = parser.parse_args()
    with Database(args.database).connect() as connection:
        action_count = connection.execute("SELECT count(*) FROM audit_actions").fetchone()[0]
        evaluation_count = connection.execute("SELECT count(*) FROM evaluations").fetchone()[0]
        connection.execute("DELETE FROM audit_actions")
        connection.execute("DELETE FROM evaluations")
    print(f"Cleared {evaluation_count} evaluations and {action_count} actions")


if __name__ == "__main__":
    main()
