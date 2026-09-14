"""
Enterprise Core — Auth (Master-Spec §9/§43 Security Baseline).

PBKDF2-HMAC-SHA256 (Python-Stdlib `hashlib`, KEINE neue Abhaengigkeit noetig,
Master-Spec §63 "keine unnoetigen Neubauten" -- Passwort-Hashing ist
sicherheitskritisch genug, um NICHT selbst kryptografisch neu zu erfinden,
aber stdlib-PBKDF2 ist ein anerkannter, ausreichender Standard ohne
zusaetzliche Paket-Abhaengigkeit).

Sessions: zufaellige 256-bit Tokens (secrets.token_hex), serverseitig
widerrufbar (revoked-Flag), Ablaufzeit erzwungen.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db import get_connection

PBKDF2_ITERATIONS = 600_000  # OWASP-Empfehlung 2023+ fuer PBKDF2-SHA256
SESSION_TTL_HOURS = 12


class AuthError(Exception):
    pass


class TenantIsolationError(Exception):
    """Wird geworfen, wenn ein Zugriff die Mandantengrenze verletzen wuerde.
    Master-Spec §10: Cross-Tenant-Leakage ist SEVERITY-0."""


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return digest.hex(), salt.hex()


def create_tenant(db_path: Path, name: str) -> str:
    tenant_id = f"T-{uuid.uuid4().hex[:12]}"
    con = get_connection(db_path)
    con.execute("INSERT INTO tenants (tenant_id, name) VALUES (?, ?)", (tenant_id, name))
    con.commit()
    con.close()
    return tenant_id


def register_user(db_path: Path, tenant_id: str, email: str, password: str,
                   role: str = "VIEWER") -> str:
    if len(password) < 12:
        raise AuthError("Passwort zu kurz (Mindestlaenge 12 Zeichen, Security Baseline)")
    pw_hash, salt = _hash_password(password)
    user_id = f"U-{uuid.uuid4().hex[:12]}"
    con = get_connection(db_path)
    try:
        con.execute(
            "INSERT INTO users (user_id, tenant_id, email, password_hash, password_salt) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, tenant_id, email, pw_hash, salt),
        )
        con.execute(
            "INSERT INTO user_roles (user_id, role_name, tenant_id) VALUES (?, ?, ?)",
            (user_id, role, tenant_id),
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return user_id


def login(db_path: Path, tenant_id: str, email: str, password: str) -> str:
    """Gibt bei Erfolg ein Session-Token zurueck. Wirft AuthError bei
    falschem Passwort/unbekanntem Nutzer -- KEIN Unterschied in der
    Fehlermeldung (verhindert User-Enumeration, Security Baseline §43)."""
    con = get_connection(db_path)
    row = con.execute(
        "SELECT user_id, password_hash, password_salt, status FROM users "
        "WHERE tenant_id = ? AND email = ?",
        (tenant_id, email),
    ).fetchone()
    if row is None:
        con.close()
        raise AuthError("Login fehlgeschlagen")
    user_id, stored_hash, salt_hex, status = row
    if status != "ACTIVE":
        con.close()
        raise AuthError("Login fehlgeschlagen")
    check_hash, _ = _hash_password(password, bytes.fromhex(salt_hex))
    if not secrets.compare_digest(check_hash, stored_hash):
        con.close()
        raise AuthError("Login fehlgeschlagen")

    token = secrets.token_hex(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
    con.execute(
        "INSERT INTO sessions (session_token, user_id, tenant_id, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, tenant_id, expires),
    )
    con.commit()
    con.close()
    return token


def verify_session(db_path: Path, session_token: str) -> dict:
    """Prueft ein Session-Token und gibt {user_id, tenant_id, roles} zurueck.
    Wirft AuthError bei abgelaufener/widerrufener/unbekannter Session."""
    con = get_connection(db_path)
    row = con.execute(
        "SELECT user_id, tenant_id, expires_at, revoked FROM sessions WHERE session_token = ?",
        (session_token,),
    ).fetchone()
    if row is None:
        con.close()
        raise AuthError("Ungueltige Session")
    user_id, tenant_id, expires_at, revoked = row
    if revoked:
        con.close()
        raise AuthError("Session widerrufen")
    if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
        con.close()
        raise AuthError("Session abgelaufen")

    roles = [r[0] for r in con.execute(
        "SELECT role_name FROM user_roles WHERE user_id = ? AND tenant_id = ?",
        (user_id, tenant_id),
    ).fetchall()]
    con.close()
    return {"user_id": user_id, "tenant_id": tenant_id, "roles": roles}


def revoke_session(db_path: Path, session_token: str) -> None:
    con = get_connection(db_path)
    con.execute("UPDATE sessions SET revoked = 1 WHERE session_token = ?", (session_token,))
    con.commit()
    con.close()


def assert_tenant_match(session_ctx: dict, requested_tenant_id: str) -> None:
    """Zentrale Durchsetzungsstelle gegen Cross-Tenant-Zugriff. JEDE
    Datenoperation in einem Produkt MUSS dies vor dem eigentlichen Query
    aufrufen (Master-Spec §10: technisch ausgeschlossen, nicht nur geprueft)."""
    if session_ctx.get("roles") and "OWNER" in session_ctx["roles"]:
        return  # Root Admin (nur Eduard) darf mandantenuebergreifend
    if session_ctx["tenant_id"] != requested_tenant_id:
        raise TenantIsolationError(
            f"SEV-0: Session gehoert zu Tenant {session_ctx['tenant_id']}, "
            f"Zugriff auf Tenant {requested_tenant_id} verweigert"
        )
