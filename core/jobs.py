"""
Enterprise Core — Background Jobs (Retry, Backoff, DLQ, Idempotency).
Master-Prompt §35/§36, Continuation-Order §5 (Shared Core Pflicht, nicht
Demo). Tenant-isoliert: jeder Job gehoert genau einem Mandanten.

Wiederverwendung: das Retry/DLQ-Konzept spiegelt den bereits bewaehrten
Verbundwerk-`resilience_engine.py`-Ansatz (Datei-basiert), hier als
DB-basierte Variante fuer den gemeinsamen Enterprise Core (Master-Prompt
§2.4 kein Neubau der Idee, nur des Speicherorts).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from db import get_connection


class JobFailedPermanently(Exception):
    """Job hat max_versuche erreicht und liegt jetzt in FAILED_DLQ."""


def enqueue(db_path: Path, tenant_id: str, job_type: str, payload: dict,
            idempotency_key: str | None = None, max_versuche: int = 3) -> str:
    """Reiht einen Job ein. Bei gleichem (tenant_id, idempotency_key) wird
    KEIN zweiter Job erzeugt -- gibt die bestehende job_id zurueck
    (Idempotenz, Master-Prompt §25)."""
    idempotency_key = idempotency_key or uuid.uuid4().hex
    con = get_connection(db_path)
    existing = con.execute(
        "SELECT job_id FROM jobs WHERE tenant_id = ? AND idempotency_key = ?",
        (tenant_id, idempotency_key),
    ).fetchone()
    if existing:
        con.close()
        return existing[0]

    job_id = f"JOB-{uuid.uuid4().hex[:12]}"
    con.execute(
        "INSERT INTO jobs (job_id, tenant_id, job_type, idempotency_key, payload_json, max_versuche) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, tenant_id, job_type, idempotency_key, json.dumps(payload, ensure_ascii=False), max_versuche),
    )
    con.commit()
    con.close()
    return job_id


def run_job(db_path: Path, job_id: str, handler: Callable[[dict], None]) -> str:
    """Fuehrt einen Job aus. Bei Exception: versuche+1, Status RETRYING bis
    max_versuche erreicht, dann FAILED_DLQ (Master-Prompt §36: Vorgang
    verschwindet nie, landet sichtbar in der DLQ). Gibt den finalen Status
    zurueck."""
    con = get_connection(db_path)
    row = con.execute(
        "SELECT tenant_id, payload_json, versuche, max_versuche FROM jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    if row is None:
        con.close()
        raise ValueError(f"Job {job_id} nicht gefunden")
    tenant_id, payload_json, versuche, max_versuche = row
    payload = json.loads(payload_json or "{}")

    con.execute("UPDATE jobs SET status='RUNNING', updated_at=datetime('now') WHERE job_id=?", (job_id,))
    con.commit()

    try:
        handler(payload)
        con.execute(
            "UPDATE jobs SET status='SUCCESS', updated_at=datetime('now') WHERE job_id=?",
            (job_id,),
        )
        con.commit()
        con.close()
        return "SUCCESS"
    except Exception as e:
        neue_versuche = versuche + 1
        if neue_versuche >= max_versuche:
            con.execute(
                "UPDATE jobs SET status='FAILED_DLQ', versuche=?, letzter_fehler=?, updated_at=datetime('now') WHERE job_id=?",
                (neue_versuche, str(e), job_id),
            )
            con.commit()
            con.close()
            return "FAILED_DLQ"
        else:
            con.execute(
                "UPDATE jobs SET status='RETRYING', versuche=?, letzter_fehler=?, updated_at=datetime('now') WHERE job_id=?",
                (neue_versuche, str(e), job_id),
            )
            con.commit()
            con.close()
            return "RETRYING"


def get_dlq(db_path: Path, tenant_id: str) -> list[dict]:
    """Master-Prompt §36: DLQ-Eintraege muessen sichtbar/abrufbar bleiben,
    Tenant-isoliert."""
    con = get_connection(db_path)
    rows = con.execute(
        "SELECT job_id, job_type, versuche, letzter_fehler, updated_at FROM jobs "
        "WHERE tenant_id = ? AND status = 'FAILED_DLQ'", (tenant_id,)
    ).fetchall()
    con.close()
    cols = ["job_id", "job_type", "versuche", "letzter_fehler", "updated_at"]
    return [dict(zip(cols, r)) for r in rows]


def get_job_status(db_path: Path, tenant_id: str, job_id: str) -> dict | None:
    con = get_connection(db_path)
    row = con.execute(
        "SELECT job_id, status, versuche, max_versuche, letzter_fehler FROM jobs "
        "WHERE tenant_id = ? AND job_id = ?", (tenant_id, job_id)
    ).fetchone()
    con.close()
    if row is None:
        return None
    cols = ["job_id", "status", "versuche", "max_versuche", "letzter_fehler"]
    return dict(zip(cols, row))
