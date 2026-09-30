"""
Enterprise Core — Access Contract / JIT-Grants (Execution Plan Phase 1.2,
ADR-001 SaaS Trust Boundary).

Platform-Support hat KEINEN automatischen Tenant-Dateneinblick (siehe
Rollenbeschreibung PLATFORM_SUPPORT in db.py). Der einzige Weg zu Tenant-Daten
ist ein Just-in-Time-Grant: scope-begrenzt (genau EIN Tenant, genau EIN User),
zeitlich begrenzt (TTL) und auditpflichtig -- und zwar nicht nur die Erteilung,
sondern JEDE tatsaechliche Nutzung ("break-glass audit", ADR-001:
"scope-/zeitbegrenzt und auditpflichtig").

Kein Parallel-Core: die Erteilung/Widerruf/Nutzung fliesst ausschliesslich
ueber die bestehende `rbac.log_audit`-Tabelle, die Durchsetzung ausschliesslich
ueber die bestehende `auth.assert_tenant_match`. Dieses Modul liefert nur die
Grant-Verwaltung + die Grant-Pruefung.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db import get_connection
from rbac import require_role, log_audit


class AccessContractError(Exception):
    """Fehler bei der JIT-Grant-Verwaltung (z.B. fehlender Anlass)."""


def _actor_session_ctx(con, actor_user_id: str) -> dict:
    """Baut ein minimales session_ctx ({'roles': [...]}) aus den in der DB
    hinterlegten Rollen des Actors, damit die bestehende `require_role`-
    Pruefung (scope='platform') wiederverwendet werden kann -- keine zweite
    Rollenlogik."""
    roles = [r[0] for r in con.execute(
        "SELECT role_name FROM user_roles WHERE user_id = ?",
        (actor_user_id,),
    ).fetchall()]
    return {"roles": roles}


def grant_jit_access(db_path: Path, tenant_id: str, actor_user_id: str,
                     reason: str, ttl_minutes: int = 60) -> str:
    """Gewaehrt einem Platform-Support-Mitarbeiter (`actor_user_id`)
    temporaeren Zugriff auf GENAU EINEN Tenant. Gibt die grant_id zurueck.

    Nur zulaessig fuer PLATFORM_SUPPORT/PLATFORM_ADMIN/PLATFORM_ROOT
    (scope='platform' via bestehendem require_role -- PLATFORM_AUDITOR und alle
    Tenant-Rollen werden mit deny-by-default abgelehnt).

    `reason` ist PFLICHT: kein Grant ohne dokumentierten Anlass. Erteilung wird
    ueber log_audit protokolliert (break-glass audit)."""
    if reason is None or not reason.strip():
        raise AccessContractError(
            "JIT-Grant benoetigt einen dokumentierten Anlass (reason darf nicht leer sein)"
        )
    if ttl_minutes <= 0:
        raise AccessContractError("ttl_minutes muss > 0 sein")

    con = get_connection(db_path)
    try:
        # Deny-by-default: nur Platform-Ebene ab PLATFORM_SUPPORT darf erteilen.
        require_role(_actor_session_ctx(con, actor_user_id), "PLATFORM_SUPPORT",
                     scope="platform")
        grant_id = f"JIT-{uuid.uuid4().hex[:12]}"
        expires = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat()
        con.execute(
            "INSERT INTO jit_grants (grant_id, tenant_id, user_id, reason, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (grant_id, tenant_id, actor_user_id, reason.strip(), expires),
        )
        con.commit()
    finally:
        con.close()

    # Break-glass audit: die Erteilung ist sichtbar (Actor, Ziel-Tenant, Anlass).
    log_audit(db_path, tenant_id, actor=actor_user_id, action="JIT_GRANT_CREATED",
              entity=grant_id, nachher=reason.strip(), quelle="jit")
    return grant_id


def check_jit_access(db_path: Path, actor_user_id: str, tenant_id: str) -> bool:
    """Reine Pruefung (kein Seiteneffekt, kein Audit): existiert fuer GENAU
    diesen User UND GENAU diesen Tenant ein aktiver, nicht widerrufener, nicht
    abgelaufener Grant?

    Verlangt IMMER einen tenant_id-Bezug -- es gibt keinen globalen Bypass ohne
    Tenant (Abnahme: "jede API mit tenant context"). Kein Grant / abgelaufen /
    widerrufen -> False (deny-by-default)."""
    now = datetime.now(timezone.utc).isoformat()
    con = get_connection(db_path)
    row = con.execute(
        "SELECT 1 FROM jit_grants "
        "WHERE user_id = ? AND tenant_id = ? AND revoked = 0 AND expires_at > ? "
        "LIMIT 1",
        (actor_user_id, tenant_id, now),
    ).fetchone()
    con.close()
    return row is not None


def revoke_jit_access(db_path: Path, grant_id: str, revoked_by: str) -> None:
    """Widerruft einen Grant sofort (greift unabhaengig von der Rest-TTL).
    Der Widerruf wird ueber log_audit protokolliert."""
    con = get_connection(db_path)
    row = con.execute(
        "SELECT tenant_id FROM jit_grants WHERE grant_id = ?", (grant_id,),
    ).fetchone()
    con.execute(
        "UPDATE jit_grants SET revoked = 1, revoked_by = ?, revoked_at = ? "
        "WHERE grant_id = ?",
        (revoked_by, datetime.now(timezone.utc).isoformat(), grant_id),
    )
    con.commit()
    con.close()
    if row is not None:
        log_audit(db_path, row[0], actor=revoked_by, action="JIT_GRANT_REVOKED",
                  entity=grant_id, quelle="jit")
