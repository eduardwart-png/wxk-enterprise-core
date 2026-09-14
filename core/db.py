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

INSERT OR IGNORE INTO roles (role_name, beschreibung) VALUES
    ('OWNER', 'Voller Zugriff, alle Mandanten (nur Eduard, Root Admin)'),
    ('ADMIN', 'Voller Zugriff innerhalb des eigenen Mandanten'),
    ('REVIEWER', 'Kann Review-Faelle bearbeiten, keine Admin-Rechte'),
    ('VIEWER', 'Nur Lesezugriff innerhalb des eigenen Mandanten');
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_schema(db_path: Path) -> None:
    con = get_connection(db_path)
    con.executescript(SCHEMA)
    con.commit()
    con.close()
