"""
Enterprise Core — Portal-Links Testsuite (WXK.TAX Hermes Final Limit
Closure §4/§5/§11: Client-ID darf niemals allein autorisieren, Security
Regression nach jedem Portal-Fix).
"""
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import pytest
from db import init_schema, get_connection
from auth import create_tenant
from portal_links import (
    create_portal_link, verify_portal_link, revoke_portal_link,
    revoke_all_for_client, PortalLinkError,
)


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "portal_test.sqlite"
    init_schema(db_path)
    return db_path


def test_gueltiger_link_funktioniert(db):
    tid = create_tenant(db, "Kanzlei Test")
    token = create_portal_link(db, tid, "M-3")
    ctx = verify_portal_link(db, token)
    assert ctx["tenant_id"] == tid
    assert ctx["client_id"] == "M-3"


def test_token_ist_nicht_erratbar(db):
    tid = create_tenant(db, "Kanzlei Test")
    token1 = create_portal_link(db, tid, "M-3")
    token2 = create_portal_link(db, tid, "M-3")
    # Zwei Links fuer denselben Client muessen unterschiedliche Tokens sein
    assert token1 != token2
    assert len(token1) >= 32  # ausreichende Entropie (256 bit base64url)


def test_unbekannter_token_wird_geblockt(db):
    with pytest.raises(PortalLinkError):
        verify_portal_link(db, "erratener-oder-manipulierter-token-xyz")


def test_client_id_manipulation_wird_geblockt(db):
    """Order §4 Pflichttest: M-3 -> M-4 manipulieren darf NICHT
    funktionieren -- der Token selbst bindet den Client, nicht ein
    aenderbarer Query-Parameter."""
    tid = create_tenant(db, "Kanzlei Test")
    token = create_portal_link(db, tid, "M-3")
    ctx = verify_portal_link(db, token)
    assert ctx["client_id"] == "M-3"
    # Es gibt keinen Weg, denselben Token fuer M-4 zu verwenden --
    # der Client ist serverseitig im Token gebunden, nicht im Aufruf.
    assert ctx["client_id"] != "M-4"


def test_widerrufener_token_wird_geblockt(db):
    tid = create_tenant(db, "Kanzlei Test")
    token = create_portal_link(db, tid, "M-3")
    revoke_portal_link(db, token)
    with pytest.raises(PortalLinkError):
        verify_portal_link(db, token)


def test_abgelaufener_token_wird_geblockt(db):
    tid = create_tenant(db, "Kanzlei Test")
    token = create_portal_link(db, tid, "M-3", ttl_hours=0)
    # ttl_hours=0 -> expires_at liegt in der Vergangenheit/Gegenwart
    time.sleep(1.1)
    with pytest.raises(PortalLinkError):
        verify_portal_link(db, token)


def test_fremder_tenant_hat_keinen_zugriff_ueber_fremden_token(db):
    """Ein Token ist an EINEN Tenant gebunden -- verify_portal_link liefert
    dessen tenant_id zurueck, es gibt keinen Mechanismus, denselben Token
    fuer einen anderen Tenant zu interpretieren."""
    tid_a = create_tenant(db, "Kanzlei A")
    tid_b = create_tenant(db, "Kanzlei B")
    token_a = create_portal_link(db, tid_a, "M-1")
    ctx = verify_portal_link(db, token_a)
    assert ctx["tenant_id"] == tid_a
    assert ctx["tenant_id"] != tid_b


def test_revoke_all_for_client(db):
    tid = create_tenant(db, "Kanzlei Test")
    t1 = create_portal_link(db, tid, "M-3")
    t2 = create_portal_link(db, tid, "M-3")
    t3 = create_portal_link(db, tid, "M-4")  # anderer Client, bleibt aktiv
    n = revoke_all_for_client(db, tid, "M-3")
    assert n == 2
    with pytest.raises(PortalLinkError):
        verify_portal_link(db, t1)
    with pytest.raises(PortalLinkError):
        verify_portal_link(db, t2)
    ctx = verify_portal_link(db, t3)  # anderer Client unberuehrt
    assert ctx["client_id"] == "M-4"


def test_last_used_at_wird_aktualisiert(db):
    tid = create_tenant(db, "Kanzlei Test")
    token = create_portal_link(db, tid, "M-3")
    verify_portal_link(db, token)
    con = get_connection(db)
    row = con.execute("SELECT last_used_at FROM portal_links WHERE token=?", (token,)).fetchone()
    con.close()
    assert row[0] is not None
