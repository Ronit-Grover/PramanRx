from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .crypto import sign_text, verify_text
from .database import Database


GENESIS_HASH = "0" * 64


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def append_evaluation(
    db: Database, request: dict[str, Any], result: dict[str, Any], private_key: Path
) -> None:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        previous = connection.execute(
            "SELECT record_hash FROM ("
            "SELECT created_at, record_hash FROM evaluations UNION ALL "
            "SELECT created_at, record_hash FROM audit_actions"
            ") ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["record_hash"] if previous else GENESIS_HASH
        payload = {"kind": "evaluation", "previous_hash": previous_hash, "request": request, "result": result}
        record_hash = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
        signature = sign_text(record_hash, private_key)
        connection.execute(
            "INSERT INTO evaluations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (result["evaluation_id"], result["patient_id"], result["created_at"],
             canonical_json(request), canonical_json(result), record_hash, previous_hash, signature),
        )


def append_action(
    db: Database, evaluation_id: str, actor: str, action: str, reason: str, private_key: Path
) -> dict[str, Any]:
    created_at = datetime.now(UTC).isoformat()
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if not connection.execute("SELECT 1 FROM evaluations WHERE id=?", (evaluation_id,)).fetchone():
            raise KeyError(evaluation_id)
        previous = connection.execute(
            "SELECT record_hash FROM ("
            "SELECT created_at, record_hash FROM evaluations UNION ALL "
            "SELECT created_at, record_hash FROM audit_actions"
            ") ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["record_hash"] if previous else GENESIS_HASH
        action_id = str(uuid.uuid4())
        body = {"id": action_id, "evaluation_id": evaluation_id, "created_at": created_at,
                "actor": actor, "action": action, "reason": reason}
        payload = {"kind": "action", "previous_hash": previous_hash, "body": body}
        record_hash = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
        signature = sign_text(record_hash, private_key)
        connection.execute(
            "INSERT INTO audit_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (action_id, evaluation_id, created_at, actor, action, reason,
             record_hash, previous_hash, signature),
        )
    return {**body, "record_hash": record_hash}


def verify_chain(db: Database, public_key: Path) -> dict[str, Any]:
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT 'evaluation' kind, created_at, record_hash, previous_hash, signature, "
            "request_json payload_a, result_json payload_b, NULL evaluation_id, NULL actor, NULL action, NULL reason "
            "FROM evaluations UNION ALL "
            "SELECT 'action', created_at, record_hash, previous_hash, signature, NULL, NULL, "
            "evaluation_id, actor, action, reason FROM audit_actions ORDER BY created_at, record_hash"
        ).fetchall()
    expected_previous = GENESIS_HASH
    errors: list[str] = []
    for index, row in enumerate(rows):
        if row["previous_hash"] != expected_previous:
            errors.append(f"record {index}: previous hash mismatch")
        if row["kind"] == "evaluation":
            payload = {"kind": "evaluation", "previous_hash": row["previous_hash"],
                       "request": json.loads(row["payload_a"]), "result": json.loads(row["payload_b"])}
        else:
            body = {"id": _action_id_by_hash(db, row["record_hash"]),
                    "evaluation_id": row["evaluation_id"], "created_at": row["created_at"],
                    "actor": row["actor"], "action": row["action"], "reason": row["reason"]}
            payload = {"kind": "action", "previous_hash": row["previous_hash"], "body": body}
        calculated = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
        if calculated != row["record_hash"]:
            errors.append(f"record {index}: content hash mismatch")
        if not verify_text(row["record_hash"], row["signature"], public_key):
            errors.append(f"record {index}: signature invalid")
        expected_previous = row["record_hash"]
    return {"valid": not errors, "records": len(rows), "head_hash": expected_previous, "errors": errors}


def _action_id_by_hash(db: Database, record_hash: str) -> str:
    with db.connect() as connection:
        row = connection.execute("SELECT id FROM audit_actions WHERE record_hash=?", (record_hash,)).fetchone()
    return row["id"]
