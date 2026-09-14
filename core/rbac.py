"""
Enterprise Core — RBAC + Audit (Master-Spec §43 RBAC, §45 Audit Trail).
"""
from __future__ import annotations

from pathlib import Path

from db import get_connection


class PermissionError_(Exception):
    """Eigener Name statt Ueberschreiben von builtins.PermissionError."""


ROLLEN_RANG = {"VIEWER": 0, "REVIEWER": 1, "ADMIN": 2, "OWNER": 3}


def require_role(session_ctx: dict, mindest_rolle: str) -> None:
    """Wirft PermissionError_, wenn keine der Nutzerrollen den geforderten
    Mindestrang erreicht. Deny-by-default: unbekannte Rolle = kein Zugriff."""
    nutzer_rollen = session_ctx.get("roles", [])
    mindest_rang = ROLLEN_RANG.get(mindest_rolle)
    if mindest_rang is None:
        raise PermissionError_(f"Unbekannte Rolle in Pruefung: {mindest_rolle}")
    hoechster_rang = max((ROLLEN_RANG.get(r, -1) for r in nutzer_rollen), default=-1)
    if hoechster_rang < mindest_rang:
        raise PermissionError_(
            f"Zugriff verweigert: benoetigt mindestens {mindest_rolle}, "
            f"Nutzer hat {nutzer_rollen or ['KEINE ROLLE']}"
        )


def log_audit(db_path: Path, tenant_id: str, actor: str, action: str,
              entity: str | None = None, vorher: str | None = None,
              nachher: str | None = None, quelle: str = "system") -> None:
    con = get_connection(db_path)
    con.execute(
        "INSERT INTO audit_log (tenant_id, actor, action, entity, vorher, nachher, quelle) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (tenant_id, actor, action, entity, vorher, nachher, quelle),
    )
    con.commit()
    con.close()


def get_audit_trail(db_path: Path, tenant_id: str, limit: int = 100) -> list[dict]:
    con = get_connection(db_path)
    rows = con.execute(
        "SELECT audit_id, actor, action, entity, vorher, nachher, quelle, timestamp "
        "FROM audit_log WHERE tenant_id = ? ORDER BY audit_id DESC LIMIT ?",
        (tenant_id, limit),
    ).fetchall()
    con.close()
    cols = ["audit_id", "actor", "action", "entity", "vorher", "nachher", "quelle", "timestamp"]
    return [dict(zip(cols, r)) for r in rows]
