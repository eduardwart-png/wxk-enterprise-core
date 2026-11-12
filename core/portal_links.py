"""
Enterprise Core — Portal-Links (WXK.TAX Hermes Final Limit Closure §4/§5).

Mandanten-/Kunden-Selbstbedienungsportale duerfen NIEMALS allein durch eine
erratbare Client-ID autorisieren (`?portal=M-3` ist IDOR/BOLA, kein Auth).
Dieses Modul stellt kryptografisch zufaellige, serverseitig gebundene,
zeitlich begrenzte, widerrufbare Tokens bereit -- generisch fuer jedes
Produkt (Kanzlei-Mandant, B2B-Kunde etc.), analog zu auth.py fuer normale
Logins.

Bindungskette (Order §5): SESSION/TOKEN -> TENANT -> CLIENT -> ALLOWED
RESOURCES. Der Token selbst traegt keine Bedeutung (256-bit Zufall,
`secrets.token_urlsafe`) -- die Bindung liegt ausschliesslich serverseitig
in der `portal_links`-Tabelle, niemals im Client-Parameter.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from auth import ACTIVE_STATUS
from db import begin_secure_rewrite, finish_secure_rewrite, get_connection

PORTAL_LINK_TTL_HOURS = 72  # Demo-/Praesentationszwecke: 3 Tage Gueltigkeit


PORTAL_TOKEN_DIGEST_PREFIX = "sha256:"


class PortalLinkError(Exception):
    pass


def portal_token_digest(token: str) -> str:
    """Portal-Token nur als Hash speichern (gleiches Muster wie
    auth.session_digest). Der Link traegt den Rohtoken; die DB kennt ihn nicht,
    eine Kopie der DB enthaelt also keine gueltigen Links."""
    return PORTAL_TOKEN_DIGEST_PREFIX + hashlib.sha256(token.encode("utf-8")).hexdigest()


def migrate_plaintext_portal_links(con) -> int:
    """Alt-Zeilen mit Klartext-Token an Ort und Stelle hashen. Idempotent:
    bereits gehashte Zeilen (Praefix sha256:) bleiben unberuehrt; ausgegebene
    Links funktionieren weiter. secrets.token_urlsafe enthaelt nie ':', ein
    Klartext-Token kann also nicht mit dem Praefix verwechselt werden."""
    rows = con.execute("SELECT token FROM portal_links WHERE token NOT LIKE ?",
                       (PORTAL_TOKEN_DIGEST_PREFIX + "%",)).fetchall()
    if not rows:
        return 0  # nichts zu tun: keine Schreibvorgaenge, kein Checkpoint
    begin_secure_rewrite(con)  # Klartext nicht in freien Seiten zuruecklassen
    for (tok,) in rows:
        con.execute("UPDATE portal_links SET token = ? WHERE token = ?",
                    (portal_token_digest(tok), tok))
    con.commit()
    finish_secure_rewrite(con)
    return len(rows)


def create_portal_link(db_path: Path, tenant_id: str, client_id: str,
                        ttl_hours: int = PORTAL_LINK_TTL_HOURS) -> str:
    """Erzeugt einen neuen, nicht erratbaren Portal-Token fuer genau einen
    Client innerhalb eines Tenants. Gibt den Token zurueck (in die URL
    einzubetten, z.B. ?token=...)."""
    token = secrets.token_urlsafe(32)  # 256 bit Entropie
    expires = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
    con = get_connection(db_path)
    con.execute(
        "INSERT INTO portal_links (token, tenant_id, client_id, expires_at) VALUES (?, ?, ?, ?)",
        (portal_token_digest(token), tenant_id, client_id, expires),
    )
    con.commit()
    con.close()
    return token


def verify_portal_link(db_path: Path, token: str) -> dict:
    """Prueft einen Portal-Token serverseitig. Gibt {tenant_id, client_id}
    zurueck. Wirft PortalLinkError bei unbekanntem/abgelaufenem/
    widerrufenem Token -- KEIN Unterschied in der Fehlermeldung zwischen
    'existiert nicht' und 'abgelaufen' (verhindert Enumeration, analog zu
    auth.login())."""
    con = get_connection(db_path)
    migrate_plaintext_portal_links(con)
    digest = portal_token_digest(token)
    row = con.execute(
        "SELECT p.tenant_id, p.client_id, p.expires_at, p.revoked, t.status "
        "FROM portal_links p LEFT JOIN tenants t ON t.tenant_id = p.tenant_id "
        "WHERE p.token = ?",
        (digest,),
    ).fetchone()
    if row is None:
        con.close()
        raise PortalLinkError("Ungueltiger Portal-Link")
    tenant_id, client_id, expires_at, revoked, tenant_status = row
    # Gleiche Regel wie auth.login/verify_session: nur ein ACTIVE-Mandant;
    # gleiche neutrale Meldung wie bei unbekanntem Token.
    if revoked or tenant_status != ACTIVE_STATUS:
        con.close()
        raise PortalLinkError("Ungueltiger Portal-Link")
    if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
        con.close()
        raise PortalLinkError("Ungueltiger Portal-Link")

    con.execute(
        "UPDATE portal_links SET last_used_at = ? WHERE token = ?",
        (datetime.now(timezone.utc).isoformat(), digest),
    )
    con.commit()
    con.close()
    return {"tenant_id": tenant_id, "client_id": client_id}


def revoke_portal_link(db_path: Path, token: str) -> None:
    con = get_connection(db_path)
    migrate_plaintext_portal_links(con)
    con.execute("UPDATE portal_links SET revoked = 1 WHERE token = ?",
                (portal_token_digest(token),))
    con.commit()
    con.close()


def revoke_all_for_client(db_path: Path, tenant_id: str, client_id: str) -> int:
    """Widerruft alle Links eines Clients (z.B. bei Demo-Reset). Gibt die
    Anzahl widerrufener Links zurueck."""
    con = get_connection(db_path)
    cur = con.execute(
        "UPDATE portal_links SET revoked = 1 WHERE tenant_id = ? AND client_id = ? AND revoked = 0",
        (tenant_id, client_id),
    )
    n = cur.rowcount
    con.commit()
    con.close()
    return n
