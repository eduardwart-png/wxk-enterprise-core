"""
Enterprise Core — Feature Flags (Master-Prompt §42, Continuation-Order §5).

Tenant-spezifische Ueberschreibung > globaler Default. Rollout-Prozent
deterministisch aus tenant_id gehasht (kein Zufall -- gleicher Tenant
bekommt bei jedem Aufruf dasselbe Ergebnis, wichtig fuer Tests und
Nachvollziehbarkeit).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from db import get_connection


def set_flag(db_path: Path, flag_key: str, enabled: bool, tenant_id: str | None = None,
             rollout_prozent: int = 100, beschreibung: str = "") -> None:
    con = get_connection(db_path)
    con.execute(
        "INSERT INTO feature_flags (flag_key, tenant_id, enabled, rollout_prozent, beschreibung, updated_at) "
        "VALUES (?, ?, ?, ?, ?, datetime('now')) "
        "ON CONFLICT(flag_key, tenant_id) DO UPDATE SET "
        "enabled=excluded.enabled, rollout_prozent=excluded.rollout_prozent, "
        "beschreibung=excluded.beschreibung, updated_at=datetime('now')",
        (flag_key, tenant_id, int(enabled), rollout_prozent, beschreibung),
    )
    con.commit()
    con.close()


def is_enabled(db_path: Path, flag_key: str, tenant_id: str) -> bool:
    """Deny-by-default: kein Eintrag = aus. Tenant-spezifischer Eintrag hat
    Vorrang vor globalem Default (tenant_id IS NULL)."""
    con = get_connection(db_path)
    row = con.execute(
        "SELECT enabled, rollout_prozent FROM feature_flags "
        "WHERE flag_key = ? AND tenant_id = ?", (flag_key, tenant_id),
    ).fetchone()
    if row is None:
        row = con.execute(
            "SELECT enabled, rollout_prozent FROM feature_flags "
            "WHERE flag_key = ? AND tenant_id IS NULL", (flag_key,),
        ).fetchone()
    con.close()
    if row is None:
        return False
    enabled, rollout_prozent = row
    if not enabled:
        return False
    if rollout_prozent >= 100:
        return True
    if rollout_prozent <= 0:
        return False
    # Deterministischer Hash statt Zufall: gleicher Tenant + Flag -> immer
    # dasselbe Ergebnis, testbar und nachvollziehbar.
    h = int(hashlib.sha256(f"{flag_key}:{tenant_id}".encode()).hexdigest(), 16)
    return (h % 100) < rollout_prozent
