"""
Enterprise Core — RBAC + Audit (Master-Spec §43 RBAC, §45 Audit Trail).
"""
from __future__ import annotations

from pathlib import Path

from db import get_connection, normalize_role


class PermissionError_(Exception):
    """Eigener Name statt Ueberschreiben von builtins.PermissionError."""


# ADR-001 Entscheidung 1: Platform- und Tenant-Ebene sind ZWEI getrennte
# Autoritaetsebenen. Es gibt bewusst KEINEN gemeinsamen globalen Rang-Wert,
# der beide zusammenwirft -- ein hoher Platform-Rang verleiht KEINE
# Tenant-Rechte im fremden Mandanten und umgekehrt (kein impliziter
# Rang-Durchgriff). Die Trennung wird ueber den `scope`-Parameter von
# require_role erzwungen: geprueft wird immer nur gegen die Rang-Tabelle
# der jeweiligen Ebene.
PLATFORM_RANG = {
    "PLATFORM_AUDITOR": 0,
    "PLATFORM_SUPPORT": 1,
    "PLATFORM_ADMIN": 2,
    "PLATFORM_ROOT": 3,
}

TENANT_RANG = {
    "TENANT_VIEWER": 0,
    "TENANT_SALES": 1,
    "TENANT_FINANCE": 1,
    "TENANT_OPERATOR": 1,
    "TENANT_REVIEWER": 2,
    "TENANT_ADMIN": 3,
    "TENANT_OWNER": 4,
}

_RANG_TABELLEN = {"platform": PLATFORM_RANG, "tenant": TENANT_RANG}


def require_role(session_ctx: dict, mindest_rolle: str, scope: str = "tenant") -> None:
    """Wirft PermissionError_, wenn keine der Nutzerrollen den geforderten
    Mindestrang INNERHALB der angegebenen Ebene (`scope`) erreicht.

    scope='tenant' (Default) prueft ausschliesslich gegen TENANT_RANG,
    scope='platform' ausschliesslich gegen PLATFORM_RANG. Rollen der jeweils
    anderen Ebene zaehlen NICHT mit (Rang -1) -- so kann ein PLATFORM_AUDITOR
    nicht automatisch Tenant-Rechte erben und ein TENANT_OWNER keine
    Platform-Rechte (ADR-001).

    Deny-by-default: unbekannte Rolle = kein Zugriff. Legacy-Rollennamen
    (OWNER/ADMIN/REVIEWER/VIEWER) werden transparent normalisiert, damit
    Alt-Aufrufe weiter funktionieren."""
    rang_tabelle = _RANG_TABELLEN.get(scope)
    if rang_tabelle is None:
        raise PermissionError_(f"Unbekannter Scope in Pruefung: {scope!r} (erlaubt: platform, tenant)")
    ziel_rolle = normalize_role(mindest_rolle)
    mindest_rang = rang_tabelle.get(ziel_rolle)
    if mindest_rang is None:
        raise PermissionError_(
            f"Unbekannte Rolle in Pruefung: {mindest_rolle} (scope={scope})"
        )
    nutzer_rollen = session_ctx.get("roles", [])
    hoechster_rang = max(
        (rang_tabelle.get(normalize_role(r), -1) for r in nutzer_rollen),
        default=-1,
    )
    if hoechster_rang < mindest_rang:
        raise PermissionError_(
            f"Zugriff verweigert (scope={scope}): benoetigt mindestens "
            f"{ziel_rolle}, Nutzer hat {nutzer_rollen or ['KEINE ROLLE']}"
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
