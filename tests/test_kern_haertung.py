"""
Enterprise Core — Haertung gegen die Zusagen aus README, Docstrings und ADR-001.

Je Punkt mindestens ein positiver Test (erlaubter Fall geht weiter) und ein
negativer Test (unzulaessiger Fall wird abgewiesen):

B1  Platform-Rollen nur ueber register_platform_user (PLATFORM_ROOT-Akteur
    oder einmalige Erstanlage), nie ueber register_user.
B2  Deaktivierte Nutzer und gesperrte/archivierte Mandanten: Sitzung sofort
    ungueltig, kein Login.
B3  Globales Feature-Flag (tenant_id NULL) laesst sich abschalten; Migration
    bereinigt Doppelzeilen in Bestands-Datenbanken.
B4  Login rechnet bei unbekanntem/inaktivem Nutzer genauso oft den
    Passwort-Hash wie bei falschem Passwort.
B6  JIT-Grant: Rolle wird bei jeder Pruefung erneut verlangt, TTL hat eine
    Obergrenze, Widerruf nur mit berechtigter Rolle.
B7  Portal-Tokens nur als Hash gespeichert; Migration hasht Altbestand.
B10 Neu angelegte DB-Datei nur fuer den Eigentuemer lesbar (0600).

Alle Adressen sind Platzhalter unter example.invalid.
"""
import os
import sqlite3
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import pytest

import auth
from db import init_schema, get_connection
from auth import (
    create_tenant, register_user, register_platform_user, login,
    verify_session, assert_tenant_match, AuthError, TenantIsolationError,
)
from rbac import PLATFORM_RANG, PermissionError_, get_audit_trail
from feature_flags import set_flag, is_enabled
from access_contract import (
    grant_jit_access, check_jit_access, revoke_jit_access, AccessContractError,
    MAX_JIT_TTL_MINUTES,
)
from portal_links import (
    create_portal_link, verify_portal_link, revoke_portal_link,
    revoke_all_for_client, PortalLinkError,
)

PW = "platzhalter-passwort-123"


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "haertung.sqlite"
    init_schema(db_path)
    return db_path


def _set_status(db, table, key_col, key, status):
    con = sqlite3.connect(db)
    con.execute(f"UPDATE {table} SET status = ? WHERE {key_col} = ?", (status, key))
    con.commit()
    con.close()


def _root(db, tenant_id, email="root@example.invalid"):
    """Erster PLATFORM_ROOT ueber den dokumentierten Erstanlage-Weg."""
    return register_platform_user(db, tenant_id, email, PW, role="PLATFORM_ROOT")


# ------------------------------------------------------------------- B1 ---

@pytest.mark.parametrize("rolle", sorted(PLATFORM_RANG) + ["platform_root"])
def test_b1_register_user_vergibt_keine_platform_rolle(db, rolle):
    tid = create_tenant(db, "A")
    with pytest.raises(AuthError):
        register_user(db, tid, "neu@example.invalid", PW, role=rolle)
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert n == 0  # kein halb angelegtes Konto


@pytest.mark.parametrize("rolle,erwartet", [
    ("OWNER", "TENANT_OWNER"), ("VIEWER", "TENANT_VIEWER"),
    ("TENANT_ADMIN", "TENANT_ADMIN"), ("TENANT_SALES", "TENANT_SALES"),
])
def test_b1_register_user_tenant_und_legacy_rollen_bleiben_moeglich(db, rolle, erwartet):
    tid = create_tenant(db, "A")
    register_user(db, tid, "t@example.invalid", PW, role=rolle)
    assert verify_session(db, login(db, tid, "t@example.invalid", PW))["roles"] == [erwartet]


def test_b1_erstanlage_platform_root_ohne_akteur(db):
    a = create_tenant(db, "Plattform")
    b = create_tenant(db, "Kunde")
    _root(db, a)
    ctx = verify_session(db, login(db, a, "root@example.invalid", PW))
    assert ctx["roles"] == ["PLATFORM_ROOT"]
    assert_tenant_match(ctx, b)  # Root darf mandantenuebergreifend


def test_b1_zweite_erstanlage_ohne_akteur_abgewiesen(db):
    a = create_tenant(db, "Plattform")
    _root(db, a)
    with pytest.raises(PermissionError_):
        register_platform_user(db, a, "zweit@example.invalid", PW, role="PLATFORM_ROOT")


def test_b1_erstanlage_nur_fuer_platform_root(db):
    a = create_tenant(db, "Plattform")
    with pytest.raises(PermissionError_):
        register_platform_user(db, a, "sup@example.invalid", PW, role="PLATFORM_SUPPORT")


def test_b1_platform_rolle_nur_durch_root_akteur(db):
    a = create_tenant(db, "Plattform")
    root = _root(db, a)
    owner = register_user(db, a, "owner@example.invalid", PW, role="TENANT_OWNER")
    admin = register_platform_user(db, a, "padmin@example.invalid", PW,
                                   role="PLATFORM_ADMIN", actor_user_id=root)
    for akteur in (owner, admin, "unbekannt"):
        with pytest.raises(PermissionError_):
            register_platform_user(db, a, "x@example.invalid", PW,
                                   role="PLATFORM_SUPPORT", actor_user_id=akteur)
    sup = register_platform_user(db, a, "sup@example.invalid", PW,
                                 role="PLATFORM_SUPPORT", actor_user_id=root)
    assert verify_session(db, login(db, a, "sup@example.invalid", PW))["roles"] == ["PLATFORM_SUPPORT"]
    trail = get_audit_trail(db, a)
    vergeben = [e for e in trail if e["action"] == "PLATFORM_ROLE_GRANTED"]
    assert {e["entity"] for e in vergeben} >= {admin, sup}
    assert all(e["actor"] == root for e in vergeben if e["entity"] in (admin, sup))


def test_b1_deaktivierter_root_kann_nicht_vergeben(db):
    a = create_tenant(db, "Plattform")
    root = _root(db, a)
    _set_status(db, "users", "user_id", root, "DISABLED")
    with pytest.raises(PermissionError_):
        register_platform_user(db, a, "sup@example.invalid", PW,
                               role="PLATFORM_SUPPORT", actor_user_id=root)


def test_b1_register_platform_user_lehnt_tenant_rolle_ab(db):
    a = create_tenant(db, "Plattform")
    root = _root(db, a)
    with pytest.raises(AuthError):
        register_platform_user(db, a, "t@example.invalid", PW,
                               role="TENANT_OWNER", actor_user_id=root)


# ------------------------------------------------------------------- B2 ---

def test_b2_aktiver_nutzer_bleibt_angemeldet(db):
    tid = create_tenant(db, "A")
    register_user(db, tid, "u@example.invalid", PW)
    tok = login(db, tid, "u@example.invalid", PW)
    assert verify_session(db, tok)["tenant_id"] == tid
    assert verify_session(db, tok)["tenant_id"] == tid


def test_b2_deaktivierter_nutzer_sitzung_sofort_ungueltig(db):
    tid = create_tenant(db, "A")
    uid = register_user(db, tid, "u@example.invalid", PW)
    tok = login(db, tid, "u@example.invalid", PW)
    _set_status(db, "users", "user_id", uid, "DISABLED")
    with pytest.raises(AuthError):
        verify_session(db, tok)
    with pytest.raises(AuthError):
        login(db, tid, "u@example.invalid", PW)


@pytest.mark.parametrize("status", ["SUSPENDED", "ARCHIVED"])
def test_b2_gesperrter_mandant_sitzung_und_login_abgewiesen(db, status):
    tid = create_tenant(db, "A")
    register_user(db, tid, "u@example.invalid", PW)
    tok = login(db, tid, "u@example.invalid", PW)
    _set_status(db, "tenants", "tenant_id", tid, status)
    with pytest.raises(AuthError):
        verify_session(db, tok)
    with pytest.raises(AuthError):
        login(db, tid, "u@example.invalid", PW)


def test_b2_reaktivierung_belebt_alte_sitzung_nicht_wieder(db):
    tid = create_tenant(db, "A")
    uid = register_user(db, tid, "u@example.invalid", PW)
    tok = login(db, tid, "u@example.invalid", PW)
    _set_status(db, "users", "user_id", uid, "DISABLED")
    with pytest.raises(AuthError):
        verify_session(db, tok)
    _set_status(db, "users", "user_id", uid, "ACTIVE")
    with pytest.raises(AuthError):
        verify_session(db, tok)  # alte Sitzung bleibt ungueltig
    neu = login(db, tid, "u@example.invalid", PW)  # neue Anmeldung geht wieder
    assert verify_session(db, neu)["user_id"] == uid


def test_b2_unbekannter_status_wird_abgewiesen(db):
    tid = create_tenant(db, "A")
    register_user(db, tid, "u@example.invalid", PW)
    tok = login(db, tid, "u@example.invalid", PW)
    con = sqlite3.connect(db)
    con.execute("PRAGMA ignore_check_constraints = ON")  # Altbestand ohne CHECK simulieren
    con.execute("UPDATE tenants SET status = 'UNBEKANNT' WHERE tenant_id = ?", (tid,))
    con.commit()
    con.close()
    with pytest.raises(AuthError):
        verify_session(db, tok)


# ------------------------------------------------------------------- B3 ---

def test_b3_globales_flag_laesst_sich_abschalten(db):
    tid = create_tenant(db, "A")
    set_flag(db, "kill", True)
    assert is_enabled(db, "kill", tid) is True
    set_flag(db, "kill", False)
    assert is_enabled(db, "kill", tid) is False
    n = sqlite3.connect(db).execute(
        "SELECT COUNT(*) FROM feature_flags WHERE flag_key = 'kill'").fetchone()[0]
    assert n == 1


def test_b3_globales_flag_wieder_einschaltbar_und_override_bleibt(db):
    tid = create_tenant(db, "A")
    andere = create_tenant(db, "B")
    set_flag(db, "f", False)
    set_flag(db, "f", True)
    set_flag(db, "f", False, tenant_id=tid)
    assert is_enabled(db, "f", andere) is True
    assert is_enabled(db, "f", tid) is False


ALT_FLAGS = """
CREATE TABLE tenants (tenant_id TEXT PRIMARY KEY, name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')), status TEXT NOT NULL DEFAULT 'ACTIVE');
CREATE TABLE feature_flags (
    flag_key TEXT NOT NULL, tenant_id TEXT REFERENCES tenants(tenant_id),
    enabled INTEGER NOT NULL DEFAULT 0,
    rollout_prozent INTEGER NOT NULL DEFAULT 0 CHECK (rollout_prozent BETWEEN 0 AND 100),
    beschreibung TEXT, updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (flag_key, tenant_id));
INSERT INTO tenants (tenant_id, name) VALUES ('T-a', 'A');
-- juengster Eintrag eindeutig bestimmbar: der juengste (aus) gewinnt
INSERT INTO feature_flags VALUES ('neu_aus', NULL, 1, 100, '', '2026-01-01 10:00:00');
INSERT INTO feature_flags VALUES ('neu_aus', NULL, 0, 100, '', '2026-01-01 10:00:05');
-- juengster eindeutig bestimmbar: der juengste (an) gewinnt
INSERT INTO feature_flags VALUES ('neu_an', NULL, 0, 100, '', '2026-01-01 10:00:00');
INSERT INTO feature_flags VALUES ('neu_an', NULL, 1, 100, '', '2026-01-01 10:00:05');
-- gleicher Zeitstempel: nicht bestimmbar -> sicherer Zustand (aus)
INSERT INTO feature_flags VALUES ('gleichstand', NULL, 0, 100, '', '2026-01-01 10:00:00');
INSERT INTO feature_flags VALUES ('gleichstand', NULL, 1, 100, '', '2026-01-01 10:00:00');
-- gleicher Zeitstempel, beide an: kleinerer Rollout gewinnt
INSERT INTO feature_flags VALUES ('rollout', NULL, 1, 100, '', '2026-01-01 10:00:00');
INSERT INTO feature_flags VALUES ('rollout', NULL, 1, 20, '', '2026-01-01 10:00:00');
-- Tenant-Eintrag unberuehrt
INSERT INTO feature_flags VALUES ('neu_an', 'T-a', 0, 100, '', '2026-01-01 09:00:00');
"""


def _flags_dump(path):
    con = sqlite3.connect(path)
    rows = con.execute(
        "SELECT flag_key, tenant_id, enabled, rollout_prozent, updated_at FROM feature_flags "
        "ORDER BY flag_key, COALESCE(tenant_id, '')").fetchall()
    con.close()
    return rows


def test_b3_migration_altbestand_bereinigt_doppelzeilen_idempotent(tmp_path):
    alt = tmp_path / "alt.sqlite"
    con = sqlite3.connect(alt)
    con.executescript(ALT_FLAGS)
    con.close()
    # Vor der Migration liefert is_enabled schon dieselbe Gewinnerregel.
    assert is_enabled(alt, "gleichstand", "T-x") is False
    init_schema(alt)
    erst = _flags_dump(alt)
    init_schema(alt)
    assert _flags_dump(alt) == erst
    assert erst == [
        ("gleichstand", None, 0, 100, "2026-01-01 10:00:00"),
        ("neu_an", None, 1, 100, "2026-01-01 10:00:05"),
        ("neu_an", "T-a", 0, 100, "2026-01-01 09:00:00"),
        ("neu_aus", None, 0, 100, "2026-01-01 10:00:05"),
        ("rollout", None, 1, 20, "2026-01-01 10:00:00"),
    ]
    # Nach der Migration verhindert der eindeutige Index neue Doppelzeilen.
    set_flag(alt, "neu_an", False)
    assert is_enabled(alt, "neu_an", "T-x") is False
    assert len([r for r in _flags_dump(alt) if r[0] == "neu_an"]) == 2  # global + T-a


def test_b3_eindeutigkeit_fuer_globale_eintraege_erzwungen(db):
    con = sqlite3.connect(db)
    con.execute("INSERT INTO feature_flags (flag_key, tenant_id, enabled) VALUES ('x', NULL, 1)")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO feature_flags (flag_key, tenant_id, enabled) VALUES ('x', NULL, 0)")
    con.close()


# ------------------------------------------------------------------- B4 ---

def _hash_zaehler(monkeypatch):
    aufrufe = []
    original = auth._hash_password

    def zaehlend(password, salt=None):
        aufrufe.append(1)
        return original(password, salt)

    monkeypatch.setattr(auth, "_hash_password", zaehlend)
    return aufrufe


def _anzahl(aufrufe, fn):
    vorher = len(aufrufe)
    with pytest.raises(AuthError):
        fn()
    return len(aufrufe) - vorher


def test_b4_gleicher_hashaufwand_in_allen_fehlerfaellen(db, monkeypatch):
    tid = create_tenant(db, "A")
    gesperrt = create_tenant(db, "B")
    uid = register_user(db, tid, "aus@example.invalid", PW)
    register_user(db, tid, "an@example.invalid", PW)
    register_user(db, gesperrt, "g@example.invalid", PW)
    _set_status(db, "users", "user_id", uid, "DISABLED")
    _set_status(db, "tenants", "tenant_id", gesperrt, "SUSPENDED")
    aufrufe = _hash_zaehler(monkeypatch)

    falsches_pw = _anzahl(aufrufe, lambda: login(db, tid, "an@example.invalid", "falsch-falsch-123"))
    unbekannt = _anzahl(aufrufe, lambda: login(db, tid, "niemand@example.invalid", PW))
    inaktiv = _anzahl(aufrufe, lambda: login(db, tid, "aus@example.invalid", PW))
    mandant_aus = _anzahl(aufrufe, lambda: login(db, gesperrt, "g@example.invalid", PW))
    assert falsches_pw == 1
    assert unbekannt == inaktiv == mandant_aus == falsches_pw


def test_b4_erfolgreicher_login_unveraendert(db, monkeypatch):
    tid = create_tenant(db, "A")
    register_user(db, tid, "an@example.invalid", PW)
    aufrufe = _hash_zaehler(monkeypatch)
    tok = login(db, tid, "an@example.invalid", PW)
    assert len(aufrufe) == 1
    assert verify_session(db, tok)["tenant_id"] == tid


# ------------------------------------------------------------------- B6 ---

def _support(db):
    heim = create_tenant(db, "Plattform")
    ziel = create_tenant(db, "Kunde")
    root = _root(db, heim)
    sup = register_platform_user(db, heim, "sup@example.invalid", PW,
                                 role="PLATFORM_SUPPORT", actor_user_id=root)
    return heim, ziel, root, sup


def test_b6_jit_zugriff_endet_mit_rollenentzug(db):
    heim, ziel, _root_id, sup = _support(db)
    grant_jit_access(db, ziel, sup, reason="Vorgang 1", ttl_minutes=60)
    assert check_jit_access(db, sup, ziel) is True
    con = sqlite3.connect(db)
    con.execute("UPDATE user_roles SET role_name = 'TENANT_VIEWER' WHERE user_id = ?", (sup,))
    con.commit()
    con.close()
    assert check_jit_access(db, sup, ziel) is False
    ctx = {"user_id": sup, "tenant_id": heim, "roles": ["TENANT_VIEWER"]}
    with pytest.raises(TenantIsolationError):
        assert_tenant_match(ctx, ziel, db_path=db)


def test_b6_ttl_obergrenze(db):
    _heim, ziel, _root_id, sup = _support(db)
    assert MAX_JIT_TTL_MINUTES == 480
    grant_jit_access(db, ziel, sup, reason="Vorgang 2", ttl_minutes=MAX_JIT_TTL_MINUTES)
    with pytest.raises(AccessContractError):
        grant_jit_access(db, ziel, sup, reason="Vorgang 3", ttl_minutes=MAX_JIT_TTL_MINUTES + 1)


def test_b6_widerruf_nur_mit_berechtigter_rolle(db):
    heim, ziel, root, sup = _support(db)
    viewer = register_user(db, heim, "v@example.invalid", PW, role="TENANT_VIEWER")
    gid = grant_jit_access(db, ziel, sup, reason="Vorgang 4", ttl_minutes=60)
    for akteur in ("unbekannt", viewer):
        with pytest.raises(PermissionError_):
            revoke_jit_access(db, gid, revoked_by=akteur)
    assert check_jit_access(db, sup, ziel) is True  # nicht widerrufen
    revoke_jit_access(db, gid, revoked_by=root)
    assert check_jit_access(db, sup, ziel) is False
    row = sqlite3.connect(db).execute(
        "SELECT revoked, revoked_by FROM jit_grants WHERE grant_id = ?", (gid,)).fetchone()
    assert row == (1, root)


# ------------------------------------------------------------------- B7 ---

def _tokens_in_db(path):
    return [r[0] for r in sqlite3.connect(path).execute("SELECT token FROM portal_links")]


def test_b7_portal_token_nur_als_hash_gespeichert(db):
    tid = create_tenant(db, "A")
    tok = create_portal_link(db, tid, "K-1")
    gespeichert = _tokens_in_db(db)
    assert tok not in gespeichert
    assert gespeichert[0].startswith("sha256:")
    assert verify_portal_link(db, tok) == {"tenant_id": tid, "client_id": "K-1"}
    with pytest.raises(PortalLinkError):
        verify_portal_link(db, gespeichert[0])  # der gespeicherte Wert ist kein gueltiger Link
    revoke_portal_link(db, tok)
    with pytest.raises(PortalLinkError):
        verify_portal_link(db, tok)


def test_b7_widerruf_aller_links_eines_clients(db):
    tid = create_tenant(db, "A")
    t1 = create_portal_link(db, tid, "K-1")
    t2 = create_portal_link(db, tid, "K-1")
    assert revoke_all_for_client(db, tid, "K-1") == 2
    for t in (t1, t2):
        with pytest.raises(PortalLinkError):
            verify_portal_link(db, t)


def test_b7_migration_hasht_klartext_altbestand_idempotent(tmp_path):
    alt = tmp_path / "alt_portal.sqlite"
    init_schema(alt)
    tid = create_tenant(alt, "A")
    neu = create_portal_link(alt, tid, "K-2")  # bereits gehasht
    klartext = "altbestand-klartext-token-platzhalter-0001"
    con = sqlite3.connect(alt)
    con.execute("INSERT INTO portal_links (token, tenant_id, client_id, expires_at) "
                "VALUES (?, ?, 'K-1', '2999-01-01T00:00:00+00:00')", (klartext, tid))
    con.commit()
    con.close()
    gehasht_vorher = [t for t in _tokens_in_db(alt) if t.startswith("sha256:")]
    init_schema(alt)
    erst = sorted(_tokens_in_db(alt))
    init_schema(alt)
    assert sorted(_tokens_in_db(alt)) == erst
    assert klartext not in erst
    assert all(t.startswith("sha256:") for t in erst)
    assert set(gehasht_vorher) <= set(erst)  # bereits gehashte Zeile unberuehrt
    # Ausgegebene Links funktionieren weiter:
    assert verify_portal_link(alt, klartext)["client_id"] == "K-1"
    assert verify_portal_link(alt, neu)["client_id"] == "K-2"


# ------------------------------------------------------------------ B10 ---

@pytest.mark.skipif(os.name == "nt", reason="POSIX-Dateirechte")
def test_b10_neue_db_datei_nur_fuer_eigentuemer(tmp_path):
    alt_umask = os.umask(0)
    try:
        neu = tmp_path / "neu.sqlite"
        init_schema(neu)
    finally:
        os.umask(alt_umask)
    assert stat.S_IMODE(os.stat(neu).st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX-Dateirechte")
def test_b10_bestehende_db_datei_behaelt_ihre_rechte(tmp_path):
    vorhanden = tmp_path / "vorhanden.sqlite"
    sqlite3.connect(vorhanden).close()
    os.chmod(vorhanden, 0o640)
    init_schema(vorhanden)
    get_connection(vorhanden).close()
    assert stat.S_IMODE(os.stat(vorhanden).st_mode) == 0o640


def test_b10_speicher_db_bleibt_moeglich():
    con = get_connection(":memory:")
    assert con.execute("SELECT 1").fetchone() == (1,)
    con.close()


# ------------------------------------------- Nachbesserung nach Pruefung ---
# N1: set_flag darf Fremdschluessel-/CHECK-Fehler nicht verschlucken.

def test_n1_set_flag_unbekannter_mandant_wirft(db):
    with pytest.raises(sqlite3.IntegrityError):
        set_flag(db, "k", False, tenant_id="T-unbekannt")
    n = sqlite3.connect(db).execute("SELECT COUNT(*) FROM feature_flags").fetchone()[0]
    assert n == 0


def test_n1_set_flag_rollout_ausserhalb_wirft(db):
    with pytest.raises(sqlite3.IntegrityError):
        set_flag(db, "neu", True, rollout_prozent=150)
    set_flag(db, "vorhanden", True)
    with pytest.raises(sqlite3.IntegrityError):
        set_flag(db, "vorhanden", True, rollout_prozent=-1)
    rows = sqlite3.connect(db).execute(
        "SELECT flag_key, rollout_prozent FROM feature_flags ORDER BY flag_key").fetchall()
    assert rows == [("vorhanden", 100)]


def test_n1_set_flag_vorhandener_eintrag_wird_aktualisiert(db):
    tid = create_tenant(db, "A")
    set_flag(db, "k", True, tenant_id=tid, rollout_prozent=100)
    set_flag(db, "k", False, tenant_id=tid, rollout_prozent=40)
    rows = sqlite3.connect(db).execute(
        "SELECT enabled, rollout_prozent FROM feature_flags WHERE flag_key = 'k'").fetchall()
    assert rows == [(0, 40)]
    assert is_enabled(db, "k", tid) is False


# R6: is_enabled folgt der Gewinnerregel auch OHNE vorherige Migration.

def test_r6_is_enabled_altbestand_ohne_migration_folgt_gewinnerregel(tmp_path):
    alt = tmp_path / "alt_ohne_migration.sqlite"
    con = sqlite3.connect(alt)
    con.executescript(ALT_FLAGS)
    con.close()
    assert is_enabled(alt, "neu_aus", "T-x") is False   # juengster ist aus
    assert is_enabled(alt, "neu_an", "T-x") is True     # juengster ist an
    assert is_enabled(alt, "gleichstand", "T-x") is False  # nicht bestimmbar -> aus
    assert is_enabled(alt, "neu_an", "T-a") is False    # Tenant-Eintrag hat Vorrang
    # keine Migration ausgeloest: Doppelzeilen noch vorhanden
    assert len([r for r in _flags_dump(alt) if r[0] == "neu_aus"]) == 2


# R1: Nach der Migration steht kein Klartext mehr in den Dateibytes.

def _datei_bytes(path):
    daten = b""
    for endung in ("", "-wal"):
        p = Path(str(path) + endung)
        if p.exists():
            daten += p.read_bytes()
    return daten


def _klartext_portal_db(path, klartexte, wal=False):
    init_schema(path)
    tid = create_tenant(path, "A")
    con = sqlite3.connect(path)
    if wal:
        con.execute("PRAGMA journal_mode=WAL")
    for i, tok in enumerate(klartexte):
        con.execute("INSERT INTO portal_links (token, tenant_id, client_id, expires_at) "
                    "VALUES (?, ?, ?, '2999-01-01T00:00:00+00:00')", (tok, tid, f"K-{i}"))
    con.commit()
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    assert klartexte[0].encode() in _datei_bytes(path)  # Vorbedingung: Klartext liegt in der Datei


@pytest.mark.parametrize("wal", [False, True])
def test_r1_portal_migration_hinterlaesst_keinen_klartext_in_datei(tmp_path, wal):
    path = tmp_path / "portal_bytes.sqlite"
    klartexte = [f"ALTBESTANDPLATZHALTER{i:02d}" + "q" * 24 for i in range(3)]
    _klartext_portal_db(path, klartexte, wal=wal)
    init_schema(path)
    daten = _datei_bytes(path)
    assert not any(t.encode() in daten for t in klartexte)
    assert verify_portal_link(path, klartexte[0])["client_id"] == "K-0"  # Link gilt weiter


def test_r1_sitzungs_migration_hinterlaesst_keinen_klartext_in_datei(tmp_path):
    path = tmp_path / "sitzung_bytes.sqlite"
    init_schema(path)
    tid = create_tenant(path, "A")
    uid = register_user(path, tid, "u@example.invalid", PW)
    klartexte = [f"SITZUNGPLATZHALTER{i:03d}" + "a" * 46 for i in range(40)]
    con = sqlite3.connect(path)
    for tok in klartexte:  # Altbestand: Sitzungsschluessel im Klartext
        con.execute("INSERT INTO sessions (session_token, user_id, tenant_id, expires_at) "
                    "VALUES (?, ?, ?, '2999-01-01T00:00:00+00:00')", (tok, uid, tid))
    con.commit()
    con.close()
    assert klartexte[0].encode() in _datei_bytes(path)
    assert verify_session(path, klartexte[0])["tenant_id"] == tid  # migriert und gueltig
    daten = _datei_bytes(path)
    assert not any(t.encode() in daten for t in klartexte)


def test_r1_migration_ohne_altbestand_aendert_nichts(tmp_path):
    path = tmp_path / "leer.sqlite"
    init_schema(path)
    tid = create_tenant(path, "A")
    create_portal_link(path, tid, "K-1")
    vorher = path.read_bytes()
    init_schema(path)
    from portal_links import migrate_plaintext_portal_links
    con = sqlite3.connect(path)
    assert migrate_plaintext_portal_links(con) == 0
    con.close()
    assert path.read_bytes() == vorher


# R3: Portal-Link eines nicht aktiven Mandanten wird abgewiesen.

def test_r3_portal_link_aktiver_mandant_gilt(db):
    tid = create_tenant(db, "A")
    tok = create_portal_link(db, tid, "K-1")
    assert verify_portal_link(db, tok)["tenant_id"] == tid


@pytest.mark.parametrize("status", ["SUSPENDED", "ARCHIVED"])
def test_r3_portal_link_gesperrter_mandant_abgewiesen(db, status):
    tid = create_tenant(db, "A")
    tok = create_portal_link(db, tid, "K-1")
    _set_status(db, "tenants", "tenant_id", tid, status)
    with pytest.raises(PortalLinkError, match="^Ungueltiger Portal-Link$"):
        verify_portal_link(db, tok)


# R2: Statuspruefung fuer Akteur und Beguenstigten im JIT-Pfad.

def test_r2_deaktivierter_akteur_kann_nicht_erteilen(db):
    _heim, ziel, _root_id, sup = _support(db)
    _set_status(db, "users", "user_id", sup, "DISABLED")
    with pytest.raises(PermissionError_):
        grant_jit_access(db, ziel, sup, reason="Vorgang 5", ttl_minutes=60)


def test_r2_deaktivierter_beguenstigter_hat_keinen_jit_zugriff(db):
    _heim, ziel, _root_id, sup = _support(db)
    grant_jit_access(db, ziel, sup, reason="Vorgang 6", ttl_minutes=60)
    assert check_jit_access(db, sup, ziel) is True
    _set_status(db, "users", "user_id", sup, "DISABLED")
    assert check_jit_access(db, sup, ziel) is False


def test_r2_beguenstigter_mit_gesperrtem_heimatmandant_hat_keinen_zugriff(db):
    heim, ziel, _root_id, sup = _support(db)
    grant_jit_access(db, ziel, sup, reason="Vorgang 7", ttl_minutes=60)
    _set_status(db, "tenants", "tenant_id", heim, "SUSPENDED")
    assert check_jit_access(db, sup, ziel) is False


def test_r2_deaktivierter_akteur_kann_nicht_widerrufen(db):
    _heim, ziel, root, sup = _support(db)
    gid = grant_jit_access(db, ziel, sup, reason="Vorgang 8", ttl_minutes=60)
    _set_status(db, "users", "user_id", root, "DISABLED")
    with pytest.raises(PermissionError_):
        revoke_jit_access(db, gid, revoked_by=root)
    assert check_jit_access(db, sup, ziel) is True
    revoke_jit_access(db, gid, revoked_by=sup)  # aktiver Support darf widerrufen
    assert check_jit_access(db, sup, ziel) is False


@pytest.mark.parametrize("ttl", [float("nan"), float("inf"), 0, -5, 480.5])
def test_r2_ungueltige_ttl_liefert_access_contract_error(db, ttl):
    _heim, ziel, _root_id, sup = _support(db)
    with pytest.raises(AccessContractError):
        grant_jit_access(db, ziel, sup, reason="Vorgang 9", ttl_minutes=ttl)


# ------------------------------------------ Runde 2 der Pruefung (L1/L2) ---
# Alle Faelle ohne Uhrzeitmessung; fremde Sperren werden deterministisch
# gesetzt, busy_timeout nur auf der Testverbindung klein (kein langes Warten).

import warnings  # noqa: E402

from auth import migrate_plaintext_sessions  # noqa: E402
from portal_links import migrate_plaintext_portal_links  # noqa: E402


def _schnelle_verbindung(path):
    con = get_connection(path)
    con.execute("PRAGMA busy_timeout = 50")
    return con


def _offener_leser(path):
    leser = sqlite3.connect(path, isolation_level=None)
    leser.execute("BEGIN")
    leser.execute("SELECT COUNT(*) FROM tenants").fetchone()
    return leser


def _keine_warnung(fn):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ergebnis = fn()
    assert [x for x in w if issubclass(x.category, RuntimeWarning)] == []
    return ergebnis


KLARTEXTE = [f"ALTBESTANDPLATZHALTER{i:02d}" + "q" * 24 for i in range(30)]


def test_l1_wal_checkpoint_blockiert_durch_leser_warnt(tmp_path):
    path = tmp_path / "wal_leser.sqlite"
    _klartext_portal_db(path, KLARTEXTE, wal=True)
    leser = _offener_leser(path)
    con = _schnelle_verbindung(path)
    try:
        with pytest.warns(RuntimeWarning, match="Checkpoint"):
            assert migrate_plaintext_portal_links(con) == len(KLARTEXTE)
    finally:
        con.close()
        leser.execute("ROLLBACK")
        leser.close()
    assert verify_portal_link(path, KLARTEXTE[0])["client_id"] == "K-0"


def test_l2d_wal_checkpoint_nach_migration_leert_wal(tmp_path):
    path = tmp_path / "wal_ohne_leser.sqlite"
    _klartext_portal_db(path, KLARTEXTE, wal=True)
    con = _schnelle_verbindung(path)  # bleibt offen: kein Auto-Checkpoint beim Schliessen
    try:
        assert _keine_warnung(lambda: migrate_plaintext_portal_links(con)) == len(KLARTEXTE)
        wal = Path(str(path) + "-wal")
        assert not wal.exists() or wal.stat().st_size == 0
        haupt = path.read_bytes()
        assert not any(t.encode() in haupt for t in KLARTEXTE)
    finally:
        con.close()


def test_l2a_vacuum_gesperrt_warnt_und_migration_bleibt_gueltig(tmp_path):
    path = tmp_path / "vacuum_gesperrt.sqlite"
    _klartext_portal_db(path, KLARTEXTE)  # Rollback-Journal: Leser blockiert VACUUM
    con = _schnelle_verbindung(path)
    leser = []

    def sperre_vor_vacuum(sql):
        # Fremde Lesesperre genau zwischen Commit der Migration und VACUUM.
        if sql.strip().upper() == "VACUUM" and not leser:
            leser.append(_offener_leser(path))

    con.set_trace_callback(sperre_vor_vacuum)
    try:
        with pytest.warns(RuntimeWarning, match="VACUUM"):
            assert migrate_plaintext_portal_links(con) == len(KLARTEXTE)
    finally:
        con.set_trace_callback(None)
        con.close()
        for l in leser:
            l.execute("ROLLBACK")
            l.close()
    assert leser, "Sperre wurde nicht gesetzt"
    gespeichert = _tokens_in_db(path)
    assert all(t.startswith("sha256:") for t in gespeichert)  # Migration committet
    assert verify_portal_link(path, KLARTEXTE[0])["client_id"] == "K-0"


def test_l2b_sitzungsmigration_ohne_altbestand_ist_leerlauf(tmp_path):
    path = tmp_path / "sitzung_leer.sqlite"
    init_schema(path)
    tid = create_tenant(path, "A")
    register_user(path, tid, "u@example.invalid", PW)
    tok = login(path, tid, "u@example.invalid", PW)
    con = get_connection(path)
    anweisungen = []
    con.set_trace_callback(anweisungen.append)
    assert migrate_plaintext_sessions(con) == 0
    con.close()
    assert all(a.lstrip().upper().startswith("SELECT") for a in anweisungen), anweisungen
    vorher = path.read_bytes()
    for _ in range(3):
        assert verify_session(path, tok)["tenant_id"] == tid
    assert path.read_bytes() == vorher  # kein VACUUM bei wiederholter Pruefung


def test_l2b_sitzungsmigration_mit_altbestand_arbeitet(tmp_path):
    path = tmp_path / "sitzung_alt.sqlite"
    init_schema(path)
    tid = create_tenant(path, "A")
    uid = register_user(path, tid, "u@example.invalid", PW)
    con = sqlite3.connect(path)
    con.execute("INSERT INTO sessions (session_token, user_id, tenant_id, expires_at) "
                "VALUES ('SITZUNGPLATZHALTER-ALT', ?, ?, '2999-01-01T00:00:00+00:00')", (uid, tid))
    con.commit()
    con.close()
    con = get_connection(path)
    anweisungen = []
    con.set_trace_callback(anweisungen.append)
    assert migrate_plaintext_sessions(con) == 1
    con.close()
    assert any(a.strip().upper() == "VACUUM" for a in anweisungen)


def test_l2c_nan_ttl_wird_als_nicht_positive_dauer_abgewiesen(db):
    _heim, ziel, _root_id, sup = _support(db)
    with pytest.raises(AccessContractError, match="muss > 0"):
        grant_jit_access(db, ziel, sup, reason="Vorgang 10", ttl_minutes=float("nan"))
    with pytest.raises(AccessContractError, match="hoechstens"):
        grant_jit_access(db, ziel, sup, reason="Vorgang 11", ttl_minutes=float("inf"))
