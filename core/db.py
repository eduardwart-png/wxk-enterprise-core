"""
Enterprise Core — Datenbankschicht (Master-Spec §9 Shared Enterprise Core,
§10 Multi-Tenancy von Anfang an, §65 Schema-First).

Gemeinsame technische Basis fuer WXK + Verbundwerk. Faktisch getrennte
fachliche Datenbanken bleiben getrennt (Spec §9: "keine Vermischung
sensibler WXK-Finanzdaten mit Verbundwerk-Geschaeftsdaten") -- dieses Modul
liefert nur Auth/RBAC/Tenant/Audit als wiederverwendbare Infrastruktur,
jedes Produkt bekommt seine EIGENE core.sqlite (kein gemeinsamer Datentopf).

SQLite statt sofort Postgres/Supabase (Master-Spec §32/§63: guenstige
Infrastruktur zuerst, kein Hosting-Sprung ohne Freigabe/nachgewiesene
Notwendigkeit -- bei <10 Mandanten technisch ausreichend, Migrationspfad
zu Postgres bleibt offen und ist durch das reine SQL-Schema unten nicht
blockiert).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'SUSPENDED', 'ARCHIVED'))
);

CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    email           TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    password_salt   TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'DISABLED')),
    UNIQUE (tenant_id, email)
);

CREATE TABLE IF NOT EXISTS roles (
    role_name       TEXT PRIMARY KEY,
    beschreibung    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id         TEXT NOT NULL REFERENCES users(user_id),
    role_name       TEXT NOT NULL REFERENCES roles(role_name),
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    PRIMARY KEY (user_id, role_name)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_token   TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(user_id),
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL,
    revoked         INTEGER NOT NULL DEFAULT 0
);

-- Audit Trail (Master-Spec §45: manipulationsresistent -- append-only per
-- Konvention, kein UPDATE/DELETE-Pfad im Code auf diese Tabelle).
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL,
    actor            TEXT NOT NULL,
    action          TEXT NOT NULL,
    entity          TEXT,
    vorher          TEXT,
    nachher         TEXT,
    quelle          TEXT NOT NULL DEFAULT 'system',
    timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sessions_tenant ON sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id);

-- Feature Flags (Master-Prompt §42, Continuation-Order §5)
CREATE TABLE IF NOT EXISTS feature_flags (
    flag_key        TEXT NOT NULL,
    tenant_id       TEXT REFERENCES tenants(tenant_id),  -- NULL = globaler Default
    enabled         INTEGER NOT NULL DEFAULT 0,
    rollout_prozent INTEGER NOT NULL DEFAULT 0 CHECK (rollout_prozent BETWEEN 0 AND 100),
    beschreibung    TEXT,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (flag_key, tenant_id)
);

-- Portal-Links (Master-Spec §10/§43: Mandanten-/Kunden-Selbstbedienungslinks
-- duerfen NIEMALS allein durch eine erratbare Client-ID autorisieren --
-- WXK.TAX Hermes Final Limit Closure §4/§5. Serverseitig gebundener,
-- zeitlich begrenzter, widerrufbarer Zufalls-Token statt Query-Parameter.
-- Generisch fuer jedes Produkt nutzbar (Kanzlei-Mandant, B2B-Kunde etc.).
CREATE TABLE IF NOT EXISTS portal_links (
    token           TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    client_id       TEXT NOT NULL,  -- produktspezifische ID (z.B. Mandant M-3), NICHT die Autoritaet selbst
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL,
    revoked         INTEGER NOT NULL DEFAULT 0,
    last_used_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_portal_links_tenant ON portal_links(tenant_id);

-- Just-in-Time-Grants (ADR-001: Support-Zugriff ist "scope-/zeitbegrenzt und
-- auditpflichtig"). Platform-Support hat KEINEN automatischen
-- Tenant-Dateneinblick (siehe Rollenbeschreibung PLATFORM_SUPPORT) -- ein
-- temporaerer, auf GENAU EINEN Tenant und GENAU EINEN User begrenzter Grant
-- ist der einzige Weg. Analog zu portal_links (zeitlich begrenzt,
-- widerrufbar), aber gebunden an user_id statt an einen erratbaren Token:
-- der Grant autorisiert einen konkreten Support-Mitarbeiter, nicht den
-- Besitz eines Geheimnisses. `reason` ist NOT NULL (kein Grant ohne
-- dokumentierten Anlass -- Break-Glass-Pflicht).
CREATE TABLE IF NOT EXISTS jit_grants (
    grant_id        TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    user_id         TEXT NOT NULL,  -- Support-Mitarbeiter (Platform-Ebene, evtl. anderer tenant_id)
    reason          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL,
    revoked         INTEGER NOT NULL DEFAULT 0,
    revoked_by      TEXT,
    revoked_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_jit_grants_lookup ON jit_grants(tenant_id, user_id, revoked);

-- Background Jobs / Queue (Master-Prompt §35/§36, Continuation-Order §5:
-- Retry, Backoff, Dead Letter Queue, Idempotency als Shared-Core-Pflicht)
CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    job_type        TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload_json    TEXT,
    status          TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'RETRYING', 'FAILED_DLQ')),
    versuche        INTEGER NOT NULL DEFAULT 0,
    max_versuche    INTEGER NOT NULL DEFAULT 3,
    letzter_fehler  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_status ON jobs(tenant_id, status);

-- Legacy-Rollen (ADR-001 "LEGACY_FOUNDATION_ONLY"): NICHT loeschen, sonst
-- brechen FKs bestehender user_roles-Zeilen und Alt-Konsumenten. Neue Rollen
-- werden rein additiv per INSERT OR IGNORE ergaenzt (kein Rebuild).
INSERT OR IGNORE INTO roles (role_name, beschreibung) VALUES
    ('OWNER', 'LEGACY (ADR-001): historisch mandantenuebergreifend -- wird jetzt auf TENANT_OWNER abgebildet, KEIN Cross-Tenant-Bypass mehr'),
    ('ADMIN', 'LEGACY (ADR-001): wird auf TENANT_ADMIN abgebildet'),
    ('REVIEWER', 'LEGACY (ADR-001): wird auf TENANT_REVIEWER abgebildet'),
    ('VIEWER', 'LEGACY (ADR-001): wird auf TENANT_VIEWER abgebildet');

-- Platform-Ebene (global, NICHT an einen Mandanten gebunden). Nur diese
-- Ebene darf ueberhaupt mandantenuebergreifend agieren (ADR-001 Entsch. 1).
INSERT OR IGNORE INTO roles (role_name, beschreibung) VALUES
    ('PLATFORM_ROOT', 'Plattform-Root: einzige Rolle mit Cross-Tenant-Bypass (assert_tenant_match)'),
    ('PLATFORM_ADMIN', 'Plattform-Administration ohne automatischen Tenant-Dateninhalt'),
    ('PLATFORM_SUPPORT', 'Plattform-Support: kein automatischer Tenant-Dateneinblick (JIT-Grant noetig)'),
    ('PLATFORM_AUDITOR', 'Plattform-Audit: niedrigster Platform-Rang, nur Metadaten/Audit');

-- Tenant-Ebene (strikt auf genau EINEN Mandanten beschraenkt, NIEMALS
-- Cross-Tenant, unabhaengig vom Rang -- ADR-001 "TENANT_OWNER ist niemals
-- PLATFORM_ROOT").
INSERT OR IGNORE INTO roles (role_name, beschreibung) VALUES
    ('TENANT_OWNER', 'Voller Admin-Zugriff INNERHALB genau eines Mandanten (kein Cross-Tenant)'),
    ('TENANT_ADMIN', 'Administration innerhalb des eigenen Mandanten'),
    ('TENANT_REVIEWER', 'Bearbeitet Review-Faelle im eigenen Mandanten'),
    ('TENANT_OPERATOR', 'Operativer Bearbeiter im eigenen Mandanten'),
    ('TENANT_FINANCE', 'Finanz-/Abrechnungsrolle im eigenen Mandanten'),
    ('TENANT_SALES', 'Vertriebsrolle im eigenen Mandanten'),
    ('TENANT_VIEWER', 'Nur Lesezugriff innerhalb des eigenen Mandanten');
"""

# Legacy-Rollennamen -> neue Tenant-Rollen (ADR-001 Entscheidung 3).
# Bewusste Verhaltensaenderung: Legacy 'OWNER' wird tenant-scoped
# (TENANT_OWNER) und verliert damit den Cross-Tenant-Bypass, den er nie
# haette haben duerfen (ADR-001: "Kein externer Kunde darf die heutige
# mandantenuebergreifende OWNER-Semantik erhalten"). Der Cross-Tenant-Pfad
# ist ab jetzt ausschliesslich PLATFORM_ROOT vorbehalten.
LEGACY_ROLE_MAP = {
    "OWNER": "TENANT_OWNER",
    "ADMIN": "TENANT_ADMIN",
    "REVIEWER": "TENANT_REVIEWER",
    "VIEWER": "TENANT_VIEWER",
}


def normalize_role(role: str) -> str:
    """Bildet einen Legacy-Rollennamen transparent auf die neue Rolle ab.
    Neue Rollennamen (PLATFORM_*/TENANT_*) bleiben unveraendert. Zentrale
    Stelle, damit Alt-Konsumenten (crm_api.py, WXK-Workbench) mit
    role='OWNER' NICHT crashen, aber die korrekte tenant-scoped Semantik
    bekommen."""
    return LEGACY_ROLE_MAP.get(role, role)


def get_connection(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _add_column_if_missing(con: sqlite3.Connection, table: str, column: str,
                            definition: str) -> None:
    """Additive Migration: fuegt eine Spalte nur hinzu, wenn sie noch fehlt.
    SQLite kennt kein `ADD COLUMN IF NOT EXISTS`, daher Vorpruefung ueber
    PRAGMA table_info -- so bleibt mehrfacher init_schema-Aufruf auf derselben
    DB idempotent (kein doppeltes ADD COLUMN -> kein OperationalError)."""
    vorhandene = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    if column not in vorhandene:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def init_schema(db_path: Path) -> None:
    con = get_connection(db_path)
    con.executescript(SCHEMA)
    # Additive Migration (ADR-001 / Limit-Matrix 3.1): Service Accounts von
    # Human Users trennen. CHECK-Constraint erzwingt gueltige Werte, Default
    # 'HUMAN' bricht keine bestehende Zeile.
    _add_column_if_missing(
        con, "users", "account_type",
        "account_type TEXT NOT NULL DEFAULT 'HUMAN' "
        "CHECK (account_type IN ('HUMAN', 'SERVICE'))",
    )
    con.commit()
    con.close()
