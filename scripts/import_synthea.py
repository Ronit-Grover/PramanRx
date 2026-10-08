#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import Database  # noqa: E402


def csv_rows(archive: zipfile.ZipFile, filename: str):
    with archive.open(f"csv/{filename}") as raw:
        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
            yield from csv.DictReader(text)


def import_synthea(zip_path: Path, db: Database, limit: int | None = None) -> dict[str, int]:
    db.initialize()
    counts = {"patients": 0, "allergies": 0, "conditions": 0, "medications": 0, "observations": 0}
    selected: set[str] = set()
    with zipfile.ZipFile(zip_path) as archive, db.connect() as connection:
        connection.execute("PRAGMA synchronous=NORMAL")
        for row in csv_rows(archive, "patients.csv"):
            if limit is not None and counts["patients"] >= limit:
                break
            patient_id = row["Id"]
            selected.add(patient_id)
            address = {"line": [row["ADDRESS"]], "city": row["CITY"], "state": row["STATE"],
                       "postalCode": row["ZIP"], "district": row["COUNTY"], "country": "US"}
            connection.execute(
                "INSERT OR REPLACE INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'synthea')",
                (patient_id, row["BIRTHDATE"], row["DEATHDATE"] or None, row["FIRST"], row["LAST"],
                 row["GENDER"], row["RACE"], row["ETHNICITY"], json.dumps(address, separators=(",", ":"))),
            )
            counts["patients"] += 1

        table_specs = (
            ("allergies.csv", "allergies", ("PATIENT", "CODE", "DESCRIPTION", "START", "STOP")),
            ("conditions.csv", "conditions", ("PATIENT", "CODE", "DESCRIPTION", "START", "STOP")),
            ("medications.csv", "medications", ("PATIENT", "CODE", "DESCRIPTION", "START", "STOP", "REASONDESCRIPTION")),
        )
        for filename, table, fields in table_specs:
            connection.execute(f"DELETE FROM {table} WHERE patient_id IN (SELECT id FROM patients WHERE source='synthea')")
            placeholders = ",".join("?" for _ in fields)
            columns = "patient_id, code, description, start_date, stop_date"
            if table == "medications":
                columns += ", reason"
            for row in csv_rows(archive, filename):
                if row["PATIENT"] not in selected:
                    continue
                connection.execute(
                    f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                    tuple(row[field] or None for field in fields),
                )
                counts[table] += 1

        connection.execute("DELETE FROM observations WHERE patient_id IN (SELECT id FROM patients WHERE source='synthea')")
        for row in csv_rows(archive, "observations.csv"):
            if row["PATIENT"] not in selected:
                continue
            connection.execute(
                "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(patient_id, code) DO UPDATE SET description=excluded.description, "
                "observed_at=excluded.observed_at, value=excluded.value, units=excluded.units, "
                "value_type=excluded.value_type WHERE excluded.observed_at > observations.observed_at",
                (row["PATIENT"], row["CODE"], row["DESCRIPTION"], row["DATE"],
                 row["VALUE"] or None, row["UNITS"] or None, row["TYPE"] or None),
            )
            counts["observations"] += 1
        connection.execute("INSERT OR REPLACE INTO metadata VALUES ('synthea_source', ?)", (str(zip_path),))
        connection.execute("INSERT OR REPLACE INTO metadata VALUES ('synthea_counts', ?)", (json.dumps(counts),))
    return counts


def seed_demo_patients(db: Database) -> None:
    fixtures = [
        ("demo-warfarin", "1970-01-01", "Avery", "Warfarin", "F"),
        ("demo-simvastatin", "1961-02-02", "Morgan", "Statin", "M"),
        ("demo-pregnancy", "1994-03-03", "Taylor", "Pregnancy", "F"),
        ("demo-renal", "1955-04-04", "Jordan", "Renal", "M"),
        ("demo-allergy", "1988-05-05", "Casey", "Allergy", "F"),
        ("demo-clear", "1985-06-06", "Riley", "Clear", "M"),
    ]
    with db.connect() as connection:
        for patient_id, birth, first, last, gender in fixtures:
            connection.execute(
                "INSERT OR REPLACE INTO patients VALUES (?, ?, NULL, ?, ?, ?, 'synthetic', 'synthetic', '{}', 'pramanrx-demo')",
                (patient_id, birth, first, last, gender),
            )
        for table in ("allergies", "conditions", "medications", "observations"):
            connection.execute(f"DELETE FROM {table} WHERE patient_id LIKE 'demo-%'")
        connection.execute(
            "INSERT INTO medications(patient_id,code,description,start_date) VALUES (?,?,?,?)",
            ("demo-warfarin", "855332", "warfarin sodium 5 MG Oral Tablet", "2025-01-01"),
        )
        connection.execute(
            "INSERT INTO medications(patient_id,code,description,start_date) VALUES (?,?,?,?)",
            ("demo-simvastatin", "312961", "simvastatin 20 MG Oral Tablet", "2025-01-01"),
        )
        connection.execute(
            "INSERT INTO conditions(patient_id,code,description,start_date) VALUES (?,?,?,?)",
            ("demo-pregnancy", "77386006", "Pregnancy", "2026-01-01"),
        )
        connection.execute(
            "INSERT INTO conditions(patient_id,code,description,start_date) VALUES (?,?,?,?)",
            ("demo-renal", "709044004", "Chronic kidney disease stage 4", "2024-01-01"),
        )
        connection.execute(
            "INSERT INTO observations VALUES (?,?,?,?,?,?,?)",
            ("demo-renal", "33914-3", "Estimated glomerular filtration rate", "2026-01-01", "22", "mL/min", "numeric"),
        )
        connection.execute(
            "INSERT INTO allergies(patient_id,code,description,start_date) VALUES (?,?,?,?)",
            ("demo-allergy", "91936005", "Penicillin allergy", "2000-01-01"),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream Synthea CSV ZIP into PramanRx SQLite")
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "data/runtime/pramanrx.sqlite3")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip-demo-fixtures", action="store_true")
    args = parser.parse_args()
    db = Database(args.database)
    counts = import_synthea(args.zip, db, args.limit)
    if not args.skip_demo_fixtures:
        seed_demo_patients(db)
    print(json.dumps({"database": str(args.database), "imported": counts, "demo_fixtures": not args.skip_demo_fixtures}, indent=2))


if __name__ == "__main__":
    main()
