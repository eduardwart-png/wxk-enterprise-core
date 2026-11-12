"""
Enterprise Core — Feature Flags (Master-Prompt §42, Continuation-Order §5).

Tenant-spezifische Ueberschreibung > globaler Default. Rollout-Prozent
deterministisch aus tenant_id gehasht (kein Zufall -- gleicher Tenant
bekommt bei jedem Aufruf dasselbe Ergebnis, wichtig fuer Tests und
Nachvollziehbarkeit).
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from db import FLAG_WINNER_ORDER, get_connection


def set_flag(db_path: Path, flag_key: str, enabled: bool, tenant_id: str | None = None,
             rollout_prozent: int = 100, beschreibung: str = "") -> None:
    """Setzt ein Flag (tenant_id None = globaler Default). Aktualisiert per
    `tenant_id IS ?`, damit auch der globale Eintrag (NULL) getroffen wird;
    ON CONFLICT ueber den Primaerschluessel griff bei NULL nie (B3). In einer
    noch nicht migrierten DB werden dabei auch alle Doppelzeilen gleichgesetzt."""
    werte = (int(enabled), rollout_prozent, beschreibung, flag_key, tenant_id)
    update = ("UPDATE feature_flags SET enabled = ?, rollout_prozent = ?, beschreibung = ?, "
              "updated_at = datetime('now') WHERE flag_key = ? AND tenant_id IS ?")
    con = get_connection(db_path)
    try:
        if con.execute(update, werte).rowcount == 0:
            try:
                con.execute(
                    "INSERT INTO feature_flags (flag_key, tenant_id, enabled, rollout_prozent, "
                    "beschreibung, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                    (flag_key, tenant_id, int(enabled), rollout_prozent, beschreibung),
                )
            except sqlite3.IntegrityError:
                # Nur ein gleichzeitiger Erst-Eintrag (eindeutiger Index) wird
                # durch Aktualisieren aufgeloest. Trifft das UPDATE nichts, war
                # es ein anderer Fehler (Fremdschluessel, CHECK): weiterwerfen,
                # nichts committen.
                if con.execute(update, werte).rowcount == 0:
                    raise
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
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
            f"WHERE flag_key = ? AND tenant_id IS NULL ORDER BY {FLAG_WINNER_ORDER} LIMIT 1",
            (flag_key,),
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
