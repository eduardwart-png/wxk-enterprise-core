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

from db import get_connection, normalize_role
from rbac import log_audit

PBKDF2_ITERATIONS = 600_000  # OWASP-Empfehlung 2023+ fuer PBKDF2-SHA256
SESSION_TTL_HOURS = 12


SESSION_DIGEST_PREFIX = "sha256:"


def session_digest(session_token: str) -> str:
    """Sitzungsschluessel nur als Hash speichern (Fix 03.10.2026: Klartext-Schluessel lagen in einer
    versionierten DB). Der Client behaelt den Rohschluessel; die DB kennt ihn nicht."""
    return SESSION_DIGEST_PREFIX + hashlib.sha256(session_token.encode("utf-8")).hexdigest()


def migrate_plaintext_sessions(con) -> int:
    """Alt-Zeilen mit Klartext-Schluessel in place hashen (idempotent; laufende Sitzungen bleiben gueltig)."""
    rows = con.execute("SELECT session_token FROM sessions WHERE session_token NOT LIKE ?",
                       (SESSION_DIGEST_PREFIX + "%",)).fetchall()
    for (tok,) in rows:
        con.execute("UPDATE sessions SET session_token = ? WHERE session_token = ?", (session_digest(tok), tok))
    if rows:
        con.commit()
    return len(rows)


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
                   role: str = "VIEWER", account_type: str = "HUMAN") -> str:
    if len(password) < 12:
        raise AuthError("Passwort zu kurz (Mindestlaenge 12 Zeichen, Security Baseline)")
    # Service Accounts (z.B. Integrations-/Bot-Konten) werden bewusst von
    # Human Users getrennt (Limit-Matrix 3.1). Default HUMAN -> kein
    # Verhaltensbruch fuer bestehende Aufrufer.
    if account_type not in ("HUMAN", "SERVICE"):
        raise AuthError(f"Ungueltiger account_type: {account_type!r} (erlaubt: HUMAN, SERVICE)")
    # Legacy-Rollennamen (OWNER/ADMIN/...) transparent auf das neue
    # Rollenmodell abbilden, damit Alt-Konsumenten nicht crashen (ADR-001).
    role = normalize_role(role)
    pw_hash, salt = _hash_password(password)
    user_id = f"U-{uuid.uuid4().hex[:12]}"
    con = get_connection(db_path)
    try:
        con.execute(
            "INSERT INTO users (user_id, tenant_id, email, password_hash, password_salt, account_type) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, tenant_id, email, pw_hash, salt, account_type),
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
    migrate_plaintext_sessions(con)
    con.execute(
        "INSERT INTO sessions (session_token, user_id, tenant_id, expires_at) VALUES (?, ?, ?, ?)",
        (session_digest(token), user_id, tenant_id, expires),
    )
    con.commit()
    con.close()
    return token


def verify_session(db_path: Path, session_token: str) -> dict:
    """Prueft ein Session-Token und gibt {user_id, tenant_id, roles} zurueck.
    Wirft AuthError bei abgelaufener/widerrufener/unbekannter Session."""
    con = get_connection(db_path)
    migrate_plaintext_sessions(con)
    row = con.execute(
        "SELECT user_id, tenant_id, expires_at, revoked FROM sessions WHERE session_token = ?",
        (session_digest(session_token),),
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
    migrate_plaintext_sessions(con)
    con.execute("UPDATE sessions SET revoked = 1 WHERE session_token = ?", (session_digest(session_token),))
    con.commit()
    con.close()


def assert_tenant_match(session_ctx: dict, requested_tenant_id: str,
                         db_path: Path | None = None) -> None:
    """Zentrale Durchsetzungsstelle gegen Cross-Tenant-Zugriff. JEDE
    Datenoperation in einem Produkt MUSS dies vor dem eigentlichen Query
    aufrufen (Master-Spec §10: technisch ausgeschlossen, nicht nur geprueft).

    ADR-001 Entscheidung 1/3: Cross-Tenant-Zugriff ist AUSSCHLIESSLICH ueber
    die Platform-Rolle PLATFORM_ROOT moeglich. Die fruehere Kopplung an
    'OWNER' (heute TENANT_OWNER) ist entfernt -- ein Tenant-Role-Token
    verleiht NIEMALS mandantenuebergreifende Rechte, unabhaengig vom Rang.

    JIT-Pfad (Phase 1.2, nur wenn `db_path` uebergeben wird): kein direkter
    Tenant-Match und kein PLATFORM_ROOT, ABER ein aktiver JIT-Grant fuer genau
    diesen Tenant UND diesen User -> Zugriff erlaubt. Jede solche Nutzung
    erzeugt einen EIGENEN Audit-Eintrag "JIT_ACCESS_USED" (break-glass audit:
    nicht nur die Erteilung, jede Verwendung ist sichtbar). Ohne gueltigen
    Grant bleibt der Zugriff blockiert (deny-by-default)."""
    if session_ctx.get("roles") and "PLATFORM_ROOT" in session_ctx["roles"]:
        return  # Nur Plattform-Root darf mandantenuebergreifend (ADR-001)
    if session_ctx["tenant_id"] == requested_tenant_id:
        return

    # Kein direkter Match: JIT-Grant pruefen (nur wenn eine DB verfuegbar ist --
    # Alt-Aufrufer ohne db_path verhalten sich unveraendert wie zuvor).
    if db_path is not None:
        import access_contract  # lazy import, vermeidet Import-Zyklus
        actor_user_id = session_ctx.get("user_id")
        if actor_user_id and access_contract.check_jit_access(
                db_path, actor_user_id, requested_tenant_id):
            log_audit(db_path, requested_tenant_id, actor=actor_user_id,
                      action="JIT_ACCESS_USED", entity=requested_tenant_id,
                      quelle="jit")
            return

    raise TenantIsolationError(
        f"SEV-0: Session gehoert zu Tenant {session_ctx['tenant_id']}, "
        f"Zugriff auf Tenant {requested_tenant_id} verweigert"
    )
