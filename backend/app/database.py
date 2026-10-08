from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS patients (
  id TEXT PRIMARY KEY,
  birth_date TEXT NOT NULL,
  death_date TEXT,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  gender TEXT NOT NULL,
  race TEXT,
  ethnicity TEXT,
  address_json TEXT NOT NULL DEFAULT '{}',
  source TEXT NOT NULL DEFAULT 'synthea'
);
CREATE TABLE IF NOT EXISTS allergies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  code TEXT,
  description TEXT NOT NULL,
  start_date TEXT,
  stop_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_allergies_patient ON allergies(patient_id);
CREATE TABLE IF NOT EXISTS conditions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  code TEXT,
  description TEXT NOT NULL,
  start_date TEXT,
  stop_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_conditions_patient ON conditions(patient_id);
CREATE TABLE IF NOT EXISTS medications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  code TEXT,
  description TEXT NOT NULL,
  start_date TEXT,
  stop_date TEXT,
  reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_medications_patient ON medications(patient_id);
CREATE TABLE IF NOT EXISTS observations (
  patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  description TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  value TEXT,
  units TEXT,
  value_type TEXT,
  PRIMARY KEY(patient_id, code)
);
CREATE TABLE IF NOT EXISTS evaluations (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES patients(id),
  created_at TEXT NOT NULL,
  request_json TEXT NOT NULL,
  result_json TEXT NOT NULL,
  record_hash TEXT NOT NULL UNIQUE,
  previous_hash TEXT NOT NULL,
  signature TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evaluations_patient ON evaluations(patient_id, created_at);
CREATE TABLE IF NOT EXISTS audit_actions (
  id TEXT PRIMARY KEY,
  evaluation_id TEXT NOT NULL REFERENCES evaluations(id),
  created_at TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  reason TEXT NOT NULL,
  record_hash TEXT NOT NULL UNIQUE,
  previous_hash TEXT NOT NULL,
  signature TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def patient_exists(self, patient_id: str) -> bool:
        with self.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM patients WHERE id=?", (patient_id,)
            ).fetchone() is not None

    def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM patients WHERE id=?", (patient_id,)
            ).fetchone()
        if not row:
            return None
        patient = dict(row)
        patient["address"] = json.loads(patient.pop("address_json"))
        return patient

    def list_patients(self, limit: int, offset: int, query: str | None) -> list[dict[str, Any]]:
        sql = "SELECT id, first_name, last_name, birth_date, gender, source FROM patients"
        args: list[Any] = []
        if query:
            sql += " WHERE lower(first_name || ' ' || last_name || ' ' || id) LIKE ?"
            args.append(f"%{query.lower()}%")
        sql += " ORDER BY last_name, first_name LIMIT ? OFFSET ?"
        args.extend((limit, offset))
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, args).fetchall()]

    def create_patient(self, data: dict[str, Any]) -> dict[str, Any]:
        patient_id = f"local-{uuid.uuid4()}"
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO patients (id,birth_date,first_name,last_name,gender,race,ethnicity,address_json,source) "
                "VALUES (?,?,?,?,?,?,?,'{}','user_created_synthetic')",
                (patient_id, data["birth_date"], data["first_name"], data["last_name"],
                 data["gender"], data.get("race"), data.get("ethnicity")),
            )
        return self.get_patient(patient_id) or {}

    def patient_context(self, patient_id: str) -> dict[str, Any] | None:
        patient = self.get_patient(patient_id)
        if not patient:
            return None
        with self.connect() as connection:
            for table in ("allergies", "conditions", "medications", "observations"):
                order = "observed_at DESC" if table == "observations" else "start_date DESC"
                rows = connection.execute(
                    f"SELECT * FROM {table} WHERE patient_id=? ORDER BY {order}",
                    (patient_id,),
                ).fetchall()
                patient[table] = [dict(row) for row in rows]
        return patient

    def get_evaluation(self, evaluation_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM evaluations WHERE id=?", (evaluation_id,)
            ).fetchone()
        return json.loads(row["result_json"]) if row else None

    def audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT 'evaluation' kind,id,created_at,patient_id subject,record_hash,previous_hash "
                "FROM evaluations UNION ALL "
                "SELECT 'action',id,created_at,evaluation_id,record_hash,previous_hash FROM audit_actions "
                "ORDER BY created_at DESC LIMIT ?", (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def evaluation_timeline(self, evaluation_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            evaluation = connection.execute(
                "SELECT id,created_at,record_hash,previous_hash,result_json FROM evaluations WHERE id=?",
                (evaluation_id,),
            ).fetchone()
            actions = connection.execute(
                "SELECT id,created_at,actor,action,reason,record_hash,previous_hash "
                "FROM audit_actions WHERE evaluation_id=? ORDER BY created_at", (evaluation_id,),
            ).fetchall()
        if not evaluation:
            return []
        result = json.loads(evaluation["result_json"])
        return [{"kind": "evaluation", "id": evaluation["id"], "created_at": evaluation["created_at"],
                 "record_hash": evaluation["record_hash"], "previous_hash": evaluation["previous_hash"],
                 "verdict": result.get("verdict")}, *[{"kind": "action", **dict(row)} for row in actions]]
