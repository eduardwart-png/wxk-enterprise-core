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
from auth import session_digest, migrate_plaintext_sessions  # noqa: E402
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
    # BEWUSSTE AENDERUNG (Phase 1.1 / ADR-001): Legacy 'VIEWER' wird bei der
    # Registrierung transparent auf 'TENANT_VIEWER' abgebildet. Die gespeicherte
    # und zurueckgegebene Rolle ist ab jetzt der neue Name.
    assert "TENANT_VIEWER" in ctx["roles"]


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


def test_TENANT_OWNER_darf_NICHT_mandantenuebergreifend(db):
    """KERN-ACCEPTANCE Phase 1.1 / ADR-001: "TENANT_OWNER ist niemals
    PLATFORM_ROOT". Ein Tenant-Owner ist voller Admin INNERHALB seines
    Mandanten, hat aber NIEMALS Cross-Tenant-Zugriff.

    Dieser Test ersetzt bewusst den frueheren
    `test_SEV0_owner_darf_mandantenuebergreifend`, der das GEGENTEIL erwartete.
    Die alte Erwartung (Legacy-OWNER darf mandantenuebergreifend) war genau
    die Sicherheitsluecke, die ADR-001 schliesst: Der Cross-Tenant-Bypass ist
    ab jetzt ausschliesslich an PLATFORM_ROOT gekoppelt. Legacy 'OWNER' wird
    auf TENANT_OWNER abgebildet und verliert diesen Bypass."""
    tenant_a = create_tenant(db, "A")
    tenant_b = create_tenant(db, "B")
    register_user(db, tenant_a, "owner@a.de", "tenant-owner-pw-999999", role="TENANT_OWNER")
    token = login(db, tenant_a, "owner@a.de", "tenant-owner-pw-999999")
    ctx = verify_session(db, token)
    assert "TENANT_OWNER" in ctx["roles"]
    # BREAK: Tenant-Owner versucht Cross-Tenant -> MUSS blockiert werden
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx, tenant_b)
    # VERIFY: eigener Mandant bleibt erlaubt
    assert_tenant_match(ctx, tenant_a)


def test_PLATFORM_ROOT_darf_mandantenuebergreifend(db):
    """Ersatz-Pfad fuer den frueheren OWNER-Bypass, jetzt korrekt benannt und
    an die Platform-Ebene gebunden. PLATFORM_ROOT ist die EINZIGE Rolle mit
    Cross-Tenant-Bypass (ADR-001 Entscheidung 1)."""
    tenant_a = create_tenant(db, "A")
    tenant_b = create_tenant(db, "B")
    register_user(db, tenant_a, "root@platform.de", "platform-root-pw-999999",
                  role="PLATFORM_ROOT")
    token = login(db, tenant_a, "root@platform.de", "platform-root-pw-999999")
    ctx = verify_session(db, token)
    assert "PLATFORM_ROOT" in ctx["roles"]
    assert_tenant_match(ctx, tenant_b)  # darf NICHT werfen


def test_legacy_rollenname_OWNER_wird_transparent_auf_TENANT_OWNER_abgebildet(db):
    """Rueckwaertskompatibilitaet fuer bestehende Konsumenten (crm_api.py,
    WXK-Workbench), die weiterhin role='OWNER' registrieren. Der Aufruf darf
    NICHT crashen und muss die tenant-scoped Semantik (TENANT_OWNER) erhalten
    -- OHNE Cross-Tenant-Bypass (bewusste Verhaltensaenderung, ADR-001)."""
    tenant_a = create_tenant(db, "A")
    tenant_b = create_tenant(db, "B")
    # Legacy-Aufruf wie im Bestandscode -- darf nicht werfen:
    register_user(db, tenant_a, "legacy@a.de", "legacy-owner-pw-999999", role="OWNER")
    token = login(db, tenant_a, "legacy@a.de", "legacy-owner-pw-999999")
    ctx = verify_session(db, token)
    # Transparent auf den neuen Namen abgebildet:
    assert ctx["roles"] == ["TENANT_OWNER"]
    # Hat volle Tenant-Admin-Rechte im eigenen Mandanten ...
    require_role(ctx, "TENANT_ADMIN", scope="tenant")
    # ... aber KEINEN Cross-Tenant-Bypass mehr (der Sicherheits-Fix):
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx, tenant_b)


def test_platform_und_tenant_rang_sind_getrennt(db):
    """Explizite Trennung der Ebenen (ADR-001): Ein PLATFORM_AUDITOR
    (niedrigster Platform-Rang) hat NICHT automatisch TENANT_ADMIN-Rechte,
    nur weil er eine Platform-Rolle traegt. Kein impliziter Rang-Durchgriff."""
    tenant_a = create_tenant(db, "A")
    register_user(db, tenant_a, "auditor@platform.de", "platform-auditor-pw-99",
                  role="PLATFORM_AUDITOR")
    token = login(db, tenant_a, "auditor@platform.de", "platform-auditor-pw-99")
    ctx = verify_session(db, token)
    # Platform-Rang wird auf Platform-Ebene erkannt:
    require_role(ctx, "PLATFORM_AUDITOR", scope="platform")
    # ... zaehlt aber auf Tenant-Ebene NICHT (deny-by-default):
    with pytest.raises(PermissionError_):
        require_role(ctx, "TENANT_ADMIN", scope="tenant")
    with pytest.raises(PermissionError_):
        require_role(ctx, "TENANT_VIEWER", scope="tenant")
    # Und umgekehrt: ein reiner Tenant-Owner erreicht KEINEN Platform-Rang.
    tenant_b = create_tenant(db, "B")
    register_user(db, tenant_b, "owner@b.de", "tenant-owner-pw-888888", role="TENANT_OWNER")
    tok_b = login(db, tenant_b, "owner@b.de", "tenant-owner-pw-888888")
    ctx_b = verify_session(db, tok_b)
    with pytest.raises(PermissionError_):
        require_role(ctx_b, "PLATFORM_AUDITOR", scope="platform")


def test_cross_tenant_blockiert_fuer_jeden_tenant_rang(db):
    """Abnahme Matrix §3.1: Cross-Tenant-Lese-/Schreibversuch blockiert fuer
    TENANT_*-Rollen JEDEN Rangs (nicht nur VIEWER). assert_tenant_match ist
    die gemeinsame Durchsetzungsstelle fuer Lesen UND Schreiben."""
    tenant_a = create_tenant(db, "A")
    tenant_b = create_tenant(db, "B")
    tenant_rollen = [
        "TENANT_VIEWER", "TENANT_SALES", "TENANT_FINANCE", "TENANT_OPERATOR",
        "TENANT_REVIEWER", "TENANT_ADMIN", "TENANT_OWNER",
    ]
    for i, rolle in enumerate(tenant_rollen):
        register_user(db, tenant_a, f"user{i}@a.de", "tenant-user-pw-1234567", role=rolle)
        token = login(db, tenant_a, f"user{i}@a.de", "tenant-user-pw-1234567")
        ctx = verify_session(db, token)
        assert ctx["roles"] == [rolle]
        with pytest.raises(TenantIsolationError):
            assert_tenant_match(ctx, tenant_b)  # gilt fuer Read wie Write
        assert_tenant_match(ctx, tenant_a)  # eigener Mandant bleibt erlaubt


def test_platform_interne_rang_grenzen(db):
    """Abnahme Matrix §3.1: PLATFORM_ROOT/ADMIN/SUPPORT/AUDITOR-Grenzen
    (Platform-intern) getestet -- monoton steigender Rang."""
    tid = create_tenant(db, "P")
    stufen = ["PLATFORM_AUDITOR", "PLATFORM_SUPPORT", "PLATFORM_ADMIN", "PLATFORM_ROOT"]
    for i, rolle in enumerate(stufen):
        register_user(db, tid, f"p{i}@platform.de", "platform-pw-12345678", role=rolle)
        token = login(db, tid, f"p{i}@platform.de", "platform-pw-12345678")
        ctx = verify_session(db, token)
        # erreicht alle Raenge <= dem eigenen ...
        for erlaubt in stufen[: i + 1]:
            require_role(ctx, erlaubt, scope="platform")
        # ... aber keinen hoeheren.
        for verweigert in stufen[i + 1:]:
            with pytest.raises(PermissionError_):
                require_role(ctx, verweigert, scope="platform")


def test_tenant_interne_rang_grenzen(db):
    """Abnahme Matrix §3.1: TENANT_OWNER/ADMIN/REVIEWER/OPERATOR/FINANCE/
    SALES/VIEWER-Grenzen getestet. VIEWER darf nicht ADMIN, ADMIN erreicht
    VIEWER, OWNER erreicht alles."""
    tid = create_tenant(db, "T")
    register_user(db, tid, "v@t.de", "tenant-pw-123456789", role="TENANT_VIEWER")
    register_user(db, tid, "o@t.de", "tenant-pw-123456789", role="TENANT_OWNER")
    ctx_v = verify_session(db, login(db, tid, "v@t.de", "tenant-pw-123456789"))
    ctx_o = verify_session(db, login(db, tid, "o@t.de", "tenant-pw-123456789"))
    require_role(ctx_v, "TENANT_VIEWER", scope="tenant")  # geht
    with pytest.raises(PermissionError_):
        require_role(ctx_v, "TENANT_ADMIN", scope="tenant")  # zu niedrig
    # Owner erreicht jeden Tenant-Rang:
    for rolle in ["TENANT_VIEWER", "TENANT_SALES", "TENANT_FINANCE",
                  "TENANT_OPERATOR", "TENANT_REVIEWER", "TENANT_ADMIN", "TENANT_OWNER"]:
        require_role(ctx_o, rolle, scope="tenant")


def test_audit_actor_vorhanden_bei_rollen_event(db):
    """Abnahme Matrix §3.1: Audit actor vorhanden. Nutzt den bestehenden
    log_audit (kein Neubau) und prueft, dass der Actor persistiert wird."""
    tid = create_tenant(db, "T")
    uid = register_user(db, tid, "actor@t.de", "tenant-pw-123456789", role="TENANT_ADMIN")
    log_audit(db, tid, actor=uid, action="ROLE_ASSIGNED", entity="TENANT_ADMIN",
              vorher=None, nachher="TENANT_ADMIN", quelle="test")
    trail = get_audit_trail(db, tid)
    assert trail[0]["actor"] == uid
    assert trail[0]["action"] == "ROLE_ASSIGNED"


def test_BREAK_regression_wird_vom_test_wirklich_gefangen(db):
    """Echter BREAK->RECOVER->VERIFY-Nachweis, dass der Kern-Test die
    Regression tatsaechlich faengt (nicht nur zufaellig gruen ist).

    BREAK: Wir reproduzieren die alte, verwundbare Bypass-Logik
    (Cross-Tenant-Bypass, sobald die Tenant-Owner-Rolle vorhanden ist -- so
    war 'OWNER' frueher gekoppelt). Unter dieser Logik wuerde die
    Sicherheits-Erwartung 'TENANT_OWNER darf NICHT cross-tenant' brechen: es
    fliegt KEINE TenantIsolationError -> der Test faengt die Regression.

    RECOVER/VERIFY: Die echte, produktive assert_tenant_match (Bypass nur
    fuer PLATFORM_ROOT) blockiert denselben Zugriff korrekt.
    """
    tenant_a = create_tenant(db, "A")
    tenant_b = create_tenant(db, "B")
    register_user(db, tenant_a, "owner@a.de", "tenant-owner-pw-777777", role="TENANT_OWNER")
    ctx = verify_session(db, login(db, tenant_a, "owner@a.de", "tenant-owner-pw-777777"))

    def _regressed_assert_tenant_match(session_ctx, requested_tenant_id):
        # ALTE, FEHLERHAFTE Bypass-Bedingung (Regression bewusst reingelegt):
        if session_ctx.get("roles") and "TENANT_OWNER" in session_ctx["roles"]:
            return
        if session_ctx["tenant_id"] != requested_tenant_id:
            raise TenantIsolationError("blockiert")

    # BREAK-Beweis: unter der Regression greift die Isolation NICHT -- der
    # Aufruf kehrt ohne Exception zurueck (genau das haetten wir uebersehen,
    # wenn der Kern-Test schwach waere).
    regressed_hat_geblockt = False
    try:
        _regressed_assert_tenant_match(ctx, tenant_b)
    except TenantIsolationError:
        regressed_hat_geblockt = True
    assert regressed_hat_geblockt is False, (
        "Regressionslogik sollte den Cross-Tenant-Zugriff faelschlich DURCHLASSEN"
    )

    # RECOVER/VERIFY: die echte Funktion blockiert denselben Zugriff korrekt.
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx, tenant_b)


def test_abgelaufene_session_wird_abgelehnt(db, monkeypatch):
    """BREAK: Session-Ablaufzeit manuell in die Vergangenheit setzen (simuliert
    Zeitablauf ohne 12h echte Wartezeit), VERIFY: wird abgelehnt."""
    import sqlite3
    tid = create_tenant(db, "T1")
    register_user(db, tid, "user@t1.de", "passwort-1234567890")
    token = login(db, tid, "user@t1.de", "passwort-1234567890")

    con = sqlite3.connect(db)
    con.execute("UPDATE sessions SET expires_at = '2020-01-01T00:00:00+00:00' WHERE session_token = ?", (session_digest(token),))
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


# ---- NO_PLAINTEXT_REUSABLE_CREDENTIAL_IN_TRACKED_DB (Fix 03.10.2026) ----
def _db_mit_nutzer(tmp_path):
    db = tmp_path / "core.sqlite"
    init_schema(db)
    tid = create_tenant(db, "T")
    register_user(db, tid, "a@t.local", "geheim-test-123")
    return db, tid


def test_session_schluessel_nur_als_hash(tmp_path):
    import sqlite3
    db, tid = _db_mit_nutzer(tmp_path)
    tok = login(db, tid, "a@t.local", "geheim-test-123")
    gespeichert = [r[0] for r in sqlite3.connect(db).execute("SELECT session_token FROM sessions")]
    assert tok not in gespeichert and gespeichert == [session_digest(tok)]
    assert verify_session(db, tok)["tenant_id"] == tid
    with pytest.raises(AuthError):
        verify_session(db, session_digest(tok))      # gestohlener DB-Wert taugt NICHT als Schluessel
    revoke_session(db, tok)
    with pytest.raises(AuthError):
        verify_session(db, tok)


def test_alt_klartext_sitzung_wird_migriert_und_bleibt_gueltig(tmp_path):
    import sqlite3
    db, tid = _db_mit_nutzer(tmp_path)
    tok = login(db, tid, "a@t.local", "geheim-test-123")
    con = sqlite3.connect(db)
    con.execute("UPDATE sessions SET session_token = ?", (tok,)); con.commit()   # Altbestand simulieren
    assert verify_session(db, tok)["tenant_id"] == tid
    assert [r[0] for r in con.execute("SELECT session_token FROM sessions")] == [session_digest(tok)]
    assert migrate_plaintext_sessions(sqlite3.connect(db)) == 0                  # idempotent
