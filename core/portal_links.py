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

import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db import get_connection

PORTAL_LINK_TTL_HOURS = 72  # Demo-/Praesentationszwecke: 3 Tage Gueltigkeit


class PortalLinkError(Exception):
    pass


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
        (token, tenant_id, client_id, expires),
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
    row = con.execute(
        "SELECT tenant_id, client_id, expires_at, revoked FROM portal_links WHERE token = ?",
        (token,),
    ).fetchone()
    if row is None:
        con.close()
        raise PortalLinkError("Ungueltiger Portal-Link")
    tenant_id, client_id, expires_at, revoked = row
    if revoked:
        con.close()
        raise PortalLinkError("Ungueltiger Portal-Link")
    if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
        con.close()
        raise PortalLinkError("Ungueltiger Portal-Link")

    con.execute(
        "UPDATE portal_links SET last_used_at = ? WHERE token = ?",
        (datetime.now(timezone.utc).isoformat(), token),
    )
    con.commit()
    con.close()
    return {"tenant_id": tenant_id, "client_id": client_id}


def revoke_portal_link(db_path: Path, token: str) -> None:
    con = get_connection(db_path)
    con.execute("UPDATE portal_links SET revoked = 1 WHERE token = ?", (token,))
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
