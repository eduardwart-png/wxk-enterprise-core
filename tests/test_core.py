"""
Enterprise Core — Testsuite (Master-Spec Eddy-Korrektur #10:
BUILD -> TEST -> BREAK -> RECOVER -> VERIFY nach jedem Block).

Deckt ab: Passwort-Hashing/Login, Session-Lifecycle, RBAC-Rangfolge,
Audit-Trail, und als SEV-0-Pflichttest: Cross-Tenant-Isolation
(Master-Spec §10 "technisch ausgeschlossen, nicht nur geprueft").
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import pytest
from db import init_schema
from auth import (
    create_tenant, register_user, login, verify_session, revoke_session,
    assert_tenant_match, AuthError, TenantIsolationError,
)
from rbac import require_role, log_audit, get_audit_trail, PermissionError_


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "core_test.sqlite"
    init_schema(db_path)
    return db_path


# ---------------------------------------------------------- BUILD/TEST ---

def test_tenant_und_user_anlage(db):
    tid = create_tenant(db, "Verbundwerk Deutschland")
    assert tid.startswith("T-")
    uid = register_user(db, tid, "eddy@verbundwerk.de", "korrektes-passwort-123", role="ADMIN")
    assert uid.startswith("U-")


def test_login_erfolgreich(db):
    tid = create_tenant(db, "WXK Pilot")
    register_user(db, tid, "eddy@wxk.de", "sicheres-passwort-456", role="OWNER")
    token = login(db, tid, "eddy@wxk.de", "sicheres-passwort-456")
    assert len(token) == 64  # 32 bytes hex


def test_login_falsches_passwort_wird_abgelehnt(db):
    tid = create_tenant(db, "T1")
    register_user(db, tid, "user@t1.de", "richtiges-passwort-789")
    with pytest.raises(AuthError):
        login(db, tid, "user@t1.de", "falsches-passwort")


def test_login_unbekannter_nutzer_gleiche_fehlermeldung(db):
    """User-Enumeration-Schutz: gleiche Exception fuer falsches PW und
    unbekannten Nutzer."""
    tid = create_tenant(db, "T1")
    try:
        login(db, tid, "existiert-nicht@t1.de", "irgendein-passwort")
        assert False, "haette AuthError werfen muessen"
    except AuthError as e:
        assert str(e) == "Login fehlgeschlagen"


def test_zu_kurzes_passwort_wird_abgelehnt(db):
    tid = create_tenant(db, "T1")
    with pytest.raises(AuthError):
        register_user(db, tid, "user@t1.de", "kurz")


def test_session_verifikation(db):
    tid = create_tenant(db, "T1")
    register_user(db, tid, "user@t1.de", "passwort-1234567890", role="VIEWER")
    token = login(db, tid, "user@t1.de", "passwort-1234567890")
    ctx = verify_session(db, token)
    assert ctx["tenant_id"] == tid
    assert "VIEWER" in ctx["roles"]


def test_session_widerruf_greift_sofort(db):
    tid = create_tenant(db, "T1")
    register_user(db, tid, "user@t1.de", "passwort-1234567890")
    token = login(db, tid, "user@t1.de", "passwort-1234567890")
    verify_session(db, token)  # funktioniert noch
    revoke_session(db, token)
    with pytest.raises(AuthError):
        verify_session(db, token)


def test_rbac_rangfolge(db):
    tid = create_tenant(db, "T1")
    register_user(db, tid, "viewer@t1.de", "passwort-1234567890", role="VIEWER")
    token = login(db, tid, "viewer@t1.de", "passwort-1234567890")
    ctx = verify_session(db, token)
    require_role(ctx, "VIEWER")  # muss durchgehen
    with pytest.raises(PermissionError_):
        require_role(ctx, "ADMIN")  # muss verweigert werden


def test_audit_trail_wird_geschrieben(db):
    tid = create_tenant(db, "T1")
    log_audit(db, tid, actor="U-test", action="ORDER_CREATED", entity="ORD-1",
              vorher=None, nachher="LEAD", quelle="test")
    trail = get_audit_trail(db, tid)
    assert len(trail) == 1
    assert trail[0]["action"] == "ORDER_CREATED"


# --------------------------------------------------------- BREAK/RECOVER --

def test_SEV0_cross_tenant_leak_wird_verhindert(db):
    """Der Pflichttest aus Master-Spec §10: technisch ausgeschlossen, dass
    Mandant A Daten von Mandant B sieht. BREAK: Session von Tenant A wird
    gezielt gegen Tenant B verwendet. RECOVER/VERIFY: assert_tenant_match
    muss das blockieren."""
    tenant_a = create_tenant(db, "Verbundwerk Kunde A")
    tenant_b = create_tenant(db, "Verbundwerk Kunde B")
    register_user(db, tenant_a, "user_a@kundea.de", "passwort-aaaaaaaaaa")
    token_a = login(db, tenant_a, "user_a@kundea.de", "passwort-aaaaaaaaaa")
    ctx_a = verify_session(db, token_a)

    # BREAK: Versuch, mit Tenant-A-Session auf Tenant-B-Daten zuzugreifen
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx_a, tenant_b)

    # VERIFY: Zugriff auf den EIGENEN Tenant bleibt weiterhin erlaubt
    assert_tenant_match(ctx_a, tenant_a)  # wirft nicht


def test_SEV0_owner_darf_mandantenuebergreifend(db):
    """OWNER (nur Eduard, Root Admin) ist die einzige bewusste Ausnahme von
    der Tenant-Grenze -- muss funktionieren, sonst waere Eduard selbst
    ausgesperrt."""
    tenant_a = create_tenant(db, "A")
    tenant_b = create_tenant(db, "B")
    register_user(db, tenant_a, "eduard@root.de", "root-passwort-999999", role="OWNER")
    token = login(db, tenant_a, "eduard@root.de", "root-passwort-999999")
    ctx = verify_session(db, token)
    assert_tenant_match(ctx, tenant_b)  # darf NICHT werfen


def test_abgelaufene_session_wird_abgelehnt(db, monkeypatch):
    """BREAK: Session-Ablaufzeit manuell in die Vergangenheit setzen (simuliert
    Zeitablauf ohne 12h echte Wartezeit), VERIFY: wird abgelehnt."""
    import sqlite3
    tid = create_tenant(db, "T1")
    register_user(db, tid, "user@t1.de", "passwort-1234567890")
    token = login(db, tid, "user@t1.de", "passwort-1234567890")

    con = sqlite3.connect(db)
    con.execute("UPDATE sessions SET expires_at = '2020-01-01T00:00:00+00:00' WHERE session_token = ?", (token,))
    con.commit()
    con.close()

    with pytest.raises(AuthError):
        verify_session(db, token)


def test_doppelte_email_im_gleichen_tenant_wird_abgelehnt(db):
    tid = create_tenant(db, "T1")
    register_user(db, tid, "dupe@t1.de", "passwort-1234567890")
    with pytest.raises(Exception):  # sqlite3.IntegrityError (UNIQUE constraint)
        register_user(db, tid, "dupe@t1.de", "anderes-passwort-999")


def test_gleiche_email_in_verschiedenen_tenants_erlaubt(db):
    """Kein globaler Unique-Constraint auf email -- zwei Mandanten duerfen
    denselben Nutzer-E-Mail-Namen unabhaengig voneinander haben."""
    tenant_a = create_tenant(db, "A")
    tenant_b = create_tenant(db, "B")
    register_user(db, tenant_a, "shared@example.de", "passwort-1234567890")
    uid_b = register_user(db, tenant_b, "shared@example.de", "anderes-passwort-999")
    assert uid_b.startswith("U-")
