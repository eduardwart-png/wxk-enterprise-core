"""
Enterprise Core — Access Contract / JIT-Grants Testsuite (Execution Plan
Phase 1.2, ADR-001: Support-Zugriff scope-/zeitbegrenzt und auditpflichtig).

Deckt ab: platform support JIT grants, deny-by-default, jede API mit tenant
context, break-glass audit (Erteilung UND jede Nutzung).
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import pytest
from db import init_schema, get_connection
from auth import (
    create_tenant, register_user, verify_session, login,
    assert_tenant_match, TenantIsolationError,
)
from rbac import get_audit_trail, PermissionError_
from access_contract import (
    grant_jit_access, check_jit_access, revoke_jit_access, AccessContractError,
)


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "access_contract_test.sqlite"
    init_schema(db_path)
    return db_path


def _support_user(db, tenant_id):
    """Ein Platform-Support-Mitarbeiter (Platform-Rolle, eigener Tenant)."""
    uid = register_user(db, tenant_id, "support@plattform.example", "supersicher123",
                        role="PLATFORM_SUPPORT")
    return uid


def _support_ctx(uid, home_tenant_id):
    """session_ctx eines Support-Users, dessen Heimat-Tenant NICHT der
    Ziel-Tenant ist -- so ist der Zugriff nur ueber einen JIT-Grant moeglich."""
    return {"user_id": uid, "tenant_id": home_tenant_id, "roles": ["PLATFORM_SUPPORT"]}


# --- Kern: JIT-Grant erlaubt zeitlich begrenzten Zugriff --------------------

def test_jit_grant_erlaubt_zeitlich_begrenzten_zugriff(db):
    home = create_tenant(db, "Plattform-Heimat")
    ziel = create_tenant(db, "Kunde A")
    support = _support_user(db, home)
    ctx = _support_ctx(support, home)

    # OHNE Grant: blockiert (deny-by-default)
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx, ziel, db_path=db)

    # MIT aktivem Grant: durchgelassen
    grant_jit_access(db, ziel, support, reason="Ticket #4711 Datenpruefung", ttl_minutes=60)
    assert check_jit_access(db, support, ziel) is True
    assert_tenant_match(ctx, ziel, db_path=db)  # wirft nicht


def test_jit_grant_abgelaufen_wird_verweigert(db):
    home = create_tenant(db, "Plattform-Heimat")
    ziel = create_tenant(db, "Kunde A")
    support = _support_user(db, home)
    ctx = _support_ctx(support, home)

    grant_jit_access(db, ziel, support, reason="Ticket #4712", ttl_minutes=60)
    # TTL manuell in die Vergangenheit setzen (simuliert Ablauf ohne sleep)
    con = get_connection(db)
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    con.execute("UPDATE jit_grants SET expires_at = ? WHERE tenant_id = ?", (past, ziel))
    con.commit()
    con.close()

    assert check_jit_access(db, support, ziel) is False
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx, ziel, db_path=db)


def test_jit_grant_widerruf_greift_sofort(db):
    home = create_tenant(db, "Plattform-Heimat")
    ziel = create_tenant(db, "Kunde A")
    support = _support_user(db, home)
    ctx = _support_ctx(support, home)

    grant_id = grant_jit_access(db, ziel, support, reason="Ticket #4713", ttl_minutes=60)
    assert check_jit_access(db, support, ziel) is True

    revoke_jit_access(db, grant_id, revoked_by=support)
    # TTL waere noch gueltig, Widerruf greift trotzdem sofort
    assert check_jit_access(db, support, ziel) is False
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx, ziel, db_path=db)


def test_jit_grant_gilt_nur_fuer_den_gewaehrten_tenant(db):
    home = create_tenant(db, "Plattform-Heimat")
    tenant_a = create_tenant(db, "Kunde A")
    tenant_b = create_tenant(db, "Kunde B")
    support = _support_user(db, home)
    ctx = _support_ctx(support, home)

    grant_jit_access(db, tenant_a, support, reason="Ticket #4714", ttl_minutes=60)

    # Grant fuer A -> Zugriff auf A erlaubt, auf B verweigert
    assert check_jit_access(db, support, tenant_a) is True
    assert check_jit_access(db, support, tenant_b) is False
    assert_tenant_match(ctx, tenant_a, db_path=db)  # wirft nicht
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx, tenant_b, db_path=db)


# --- Break-glass audit: Erteilung UND Nutzung -------------------------------

def test_jit_grant_erteilung_erzeugt_audit_eintrag(db):
    home = create_tenant(db, "Plattform-Heimat")
    ziel = create_tenant(db, "Kunde A")
    support = _support_user(db, home)

    grant_id = grant_jit_access(db, ziel, support, reason="Ticket #4715", ttl_minutes=60)

    trail = get_audit_trail(db, ziel)
    created = [e for e in trail if e["action"] == "JIT_GRANT_CREATED"]
    assert len(created) == 1
    assert created[0]["entity"] == grant_id
    assert created[0]["actor"] == support
    assert "Ticket #4715" in created[0]["nachher"]


def test_jit_grant_nutzung_erzeugt_eigenen_audit_eintrag(db):
    """Kern von break-glass audit: JEDE tatsaechliche Nutzung erzeugt einen
    EIGENEN JIT_ACCESS_USED-Eintrag, nicht nur die Erteilung."""
    home = create_tenant(db, "Plattform-Heimat")
    ziel = create_tenant(db, "Kunde A")
    support = _support_user(db, home)
    ctx = _support_ctx(support, home)

    grant_jit_access(db, ziel, support, reason="Ticket #4716", ttl_minutes=60)

    # Drei tatsaechliche Zugriffe -> drei eigene Nutzungs-Eintraege
    assert_tenant_match(ctx, ziel, db_path=db)
    assert_tenant_match(ctx, ziel, db_path=db)
    assert_tenant_match(ctx, ziel, db_path=db)

    trail = get_audit_trail(db, ziel)
    used = [e for e in trail if e["action"] == "JIT_ACCESS_USED"]
    created = [e for e in trail if e["action"] == "JIT_GRANT_CREATED"]
    assert len(created) == 1  # Erteilung genau einmal
    assert len(used) == 3     # jede Nutzung ein eigener Eintrag
    assert all(e["actor"] == support for e in used)


# --- Deny-by-default: Erteilung nur fuer berechtigte Rollen -----------------

def test_grant_ohne_platform_support_rolle_wird_verweigert(db):
    home = create_tenant(db, "Kunde A")
    # Ein reiner Tenant-Nutzer (kein Platform-Support) darf sich selbst
    # keinen JIT-Grant erteilen.
    viewer = register_user(db, home, "viewer@kunde.example", "supersicher123",
                          role="TENANT_VIEWER")
    with pytest.raises(PermissionError_):
        grant_jit_access(db, home, viewer, reason="will heimlich rein", ttl_minutes=60)


def test_grant_ohne_reason_wird_abgelehnt(db):
    home = create_tenant(db, "Plattform-Heimat")
    ziel = create_tenant(db, "Kunde A")
    support = _support_user(db, home)

    with pytest.raises(AccessContractError):
        grant_jit_access(db, ziel, support, reason="", ttl_minutes=60)
    with pytest.raises(AccessContractError):
        grant_jit_access(db, ziel, support, reason="   ", ttl_minutes=60)


def test_platform_auditor_darf_keinen_grant_erteilen(db):
    """Deny-by-default innerhalb der Platform-Ebene: PLATFORM_AUDITOR (Rang 0)
    liegt unter PLATFORM_SUPPORT (Rang 1) und darf nicht erteilen."""
    home = create_tenant(db, "Plattform-Heimat")
    ziel = create_tenant(db, "Kunde A")
    auditor = register_user(db, home, "auditor@plattform.example", "supersicher123",
                           role="PLATFORM_AUDITOR")
    with pytest.raises(PermissionError_):
        grant_jit_access(db, ziel, auditor, reason="nur gucken", ttl_minutes=60)


def test_check_jit_access_verlangt_immer_tenant_context(db):
    """Abnahme 'jede API mit tenant context': check_jit_access liefert ohne
    passenden Tenant-Bezug niemals True -- es gibt keinen globalen Bypass."""
    home = create_tenant(db, "Plattform-Heimat")
    tenant_a = create_tenant(db, "Kunde A")
    tenant_b = create_tenant(db, "Kunde B")
    support = _support_user(db, home)

    grant_jit_access(db, tenant_a, support, reason="Ticket #4717", ttl_minutes=60)
    # exakt der gewaehrte Tenant -> True, jeder andere -> False
    assert check_jit_access(db, support, tenant_a) is True
    assert check_jit_access(db, support, tenant_b) is False
    assert check_jit_access(db, support, home) is False


# --- Service Accounts getrennt von Human Users ------------------------------

def test_service_account_flag_default_human(db):
    """Bestehender register_user()-Aufruf ohne account_type bleibt HUMAN
    (keine Regression)."""
    tid = create_tenant(db, "Kunde A")
    uid = register_user(db, tid, "mensch@kunde.example", "supersicher123")
    con = get_connection(db)
    row = con.execute("SELECT account_type FROM users WHERE user_id = ?", (uid,)).fetchone()
    con.close()
    assert row[0] == "HUMAN"


def test_service_account_kann_als_service_markiert_werden(db):
    tid = create_tenant(db, "Kunde A")
    uid = register_user(db, tid, "bot@kunde.example", "supersicher123",
                       account_type="SERVICE")
    con = get_connection(db)
    row = con.execute("SELECT account_type FROM users WHERE user_id = ?", (uid,)).fetchone()
    con.close()
    assert row[0] == "SERVICE"


def test_init_schema_ist_idempotent_fuer_account_type(db):
    """Mehrfacher init_schema-Aufruf auf derselben DB darf nicht am doppelten
    ADD COLUMN scheitern (additive Migration mit Vorpruefung)."""
    init_schema(db)
    init_schema(db)  # zweiter Aufruf muss ohne OperationalError durchlaufen
    tid = create_tenant(db, "Kunde A")
    uid = register_user(db, tid, "mensch2@kunde.example", "supersicher123")
    assert uid.startswith("U-")


# --- Deny-by-default: unbekannte Rollen/Scopes (Phase-1.1-Absicherung) ------

def test_deny_by_default_unbekannte_rolle_kein_zugriff(db):
    """Ein Nutzer ganz ohne Rolle erreicht keinen Mindestrang -> Zugriff
    verweigert (deny-by-default, nicht 'erlaubt weil nichts gefunden')."""
    from rbac import require_role
    ctx = {"user_id": "U-x", "tenant_id": "T-x", "roles": []}
    with pytest.raises(PermissionError_):
        require_role(ctx, "TENANT_VIEWER", scope="tenant")


def test_deny_by_default_unbekannter_scope_wird_abgelehnt(db):
    from rbac import require_role
    ctx = {"user_id": "U-x", "tenant_id": "T-x", "roles": ["TENANT_OWNER"]}
    with pytest.raises(PermissionError_):
        require_role(ctx, "TENANT_VIEWER", scope="galaxy")


def test_tenant_rolle_zaehlt_nicht_im_platform_scope(db):
    """Ein TENANT_OWNER (hoechster Tenant-Rang) hat im Platform-Scope Rang -1
    -> darf keinen JIT-Grant erteilen (keine Rang-Vermischung)."""
    home = create_tenant(db, "Kunde A")
    ziel = create_tenant(db, "Kunde B")
    owner = register_user(db, home, "owner@kunde.example", "supersicher123",
                         role="TENANT_OWNER")
    with pytest.raises(PermissionError_):
        grant_jit_access(db, ziel, owner, reason="will cross-tenant", ttl_minutes=60)
