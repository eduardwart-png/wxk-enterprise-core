"""Enterprise Core — Memory Constitution Engine (LIMIT Enterprise Memory
Constitution, Eddy-Direktive 18.09.2026).

Kanonische, produktuebergreifende Memory-Control-Plane. Diese Datei ist die
GLOBALE Engine (Layer-Modell, Registry, Konfliktaufloesung, Promotion-Guard,
Retrieval-Ranking) -- produktspezifische Bindung (z.B. WXK.TAX) lebt in
einer separaten Datei, die diese Engine importiert und mit eigenen Records
befuellt (Bindungs-Pattern identisch zu zone_guard.py/release_certification.py:
Kern hier, Produktbindung im Produkt-Repo).

Hierarchie (Sec1 der Order):
    GLOBAL LIMIT CONSTITUTION           (extern, hier nur referenziert)
    -> PRODUCT DOMAIN INVARIANTS        (Layer L1)
    -> PRODUCT-SPECIFIC INVARIANTS      (Layer L2)
    -> VERIFIED GENERAL LESSONS         (Layer L3)
    -> CASE/PROJECT REFERENCES          (Layer L4)
    -> LIVE SSOT / RUNTIME STATE        (Layer L5 -- NIEMALS in dieser
                                          Registry gespeichert, nur als
                                          Pointer auf die echte SSOT-Quelle)
    -> RESTRICTED/SENSITIVE             (Layer L6)

EVIDENCE OVER MEMORY. CURRENT PRIMARY SOURCE OVER STALE MEMORY.
PRODUCT RULE OVER CASE ACCIDENT. VERIFIED LESSON OVER OBSERVATION.
LIVE SSOT OVER STORED STATUS. ONE CANONICAL ACTIVE TRUTH.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


class MemoryLayer:
    L0_GLOBAL_CONSTITUTION = "L0_GLOBAL_CONSTITUTION"
    L1_DOMAIN_INVARIANTS = "L1_DOMAIN_INVARIANTS"
    L2_PRODUCT_INVARIANTS = "L2_PRODUCT_INVARIANTS"
    L3_VERIFIED_GENERAL_LESSONS = "L3_VERIFIED_GENERAL_LESSONS"
    L4_CASE_PROJECT_REFERENCES = "L4_CASE_PROJECT_REFERENCES"
    L5_LIVE_SSOT_RUNTIME_STATE = "L5_LIVE_SSOT_RUNTIME_STATE"
    L6_RESTRICTED_SENSITIVE = "L6_RESTRICTED_SENSITIVE"

    ALL = {
        L0_GLOBAL_CONSTITUTION, L1_DOMAIN_INVARIANTS, L2_PRODUCT_INVARIANTS,
        L3_VERIFIED_GENERAL_LESSONS, L4_CASE_PROJECT_REFERENCES,
        L5_LIVE_SSOT_RUNTIME_STATE, L6_RESTRICTED_SENSITIVE,
    }


class CanonicalStatus:
    """Sec30: erlaubte Statuswerte. Keine zwei widersprüchlichen ACTIVE-
    Eintraege fuer dieselbe Regel (erzwungen in Registry.add())."""
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"

    ALL = {CANDIDATE, VERIFIED, ACTIVE, DEPRECATED, SUPERSEDED, REJECTED}
    # Promotion-Reihenfolge (Sec34): CANDIDATE -> GENERALIZED(=VERIFIED-Vorstufe,
    # hier als VERIFIED gefuehrt) -> TESTED(=VERIFIED) -> REVIEWED(=VERIFIED) ->
    # VERIFIED -> ACTIVE. Modelliert als einfache Vorwaerts-Kette.
    PROMOTION_ORDER = [CANDIDATE, VERIFIED, ACTIVE]


class Sensitivity:
    NORMAL = "NORMAL"
    RESTRICTED = "RESTRICTED"  # L6: personenbezogen/sensibel, nicht global-promotable


class MemoryConstitutionError(Exception):
    pass


class PersonalToGlobalPromotionBlocked(MemoryConstitutionError):
    """Sec35 NO_PERSONAL_TO_GLOBAL_PROMOTION: eine Regel mit source_type
    GOLDEN_CASE/CASE_SPECIFIC darf niemals direkt als L1/L2
    GLOBAL_PRODUCT_RULE mit Status ACTIVE geschrieben werden."""


class ConflictingActiveRuleError(MemoryConstitutionError):
    """Sec30: zwei ACTIVE-Eintraege mit identischem rule_key in gleichem
    scope sind verboten, ausser der neue Eintrag supersedet den alten
    explizit (supersedes-Feld gesetzt)."""


class VolatileStateInMemoryError(MemoryConstitutionError):
    """Sec25/Sec40: volatile state (Testzahlen, Hashes, Build-IDs, aktuelle
    Dateizaehler) darf NIEMALS in L1-L4 dauerhaft geschrieben werden --
    nur als Pointer auf eine externe SSOT in L5."""


# Sec25: Muster, die auf volatilen Zustand hindeuten -- werden bei jedem
# add() gegen layer != L5 geprüft (Write Guard, nicht nur Konvention).
_VOLATILE_STATE_PATTERNS = re.compile(
    r"\b\d+/\d+\s*(PASS|passed|CERTIFIED)|"          # "233/234 PASS", "880/880 CERTIFIED"
    r"\bSHA256:\s*[0-9a-f]{16,}|"                      # konkreter Hash-Wert
    r"\bBUILD-\d{8}T\d{6}Z\b|"                          # Build-ID
    r"\b\d+\s*Dateien\b(?!.*erwartet)",                 # konkrete Dateizahl als Fakt
    re.IGNORECASE,
)

# Sec14/Sec21: Domaenen, die IMMER Freshness-Pflichtfelder benoetigen.
_TIME_SENSITIVE_CATEGORIES = {
    "TAX_LAW", "ADMINISTRATIVE_GUIDANCE", "GOBD", "E_INVOICING_RULES",
    "DATEV_API", "DATEV_FORMAT", "LEGAL_AMOUNT", "DEADLINE", "SUBSIDY_RATE",
    "API_VERSION", "PRODUCT_PRICE", "EXTERNAL_PROVIDER_RULE",
}


@dataclass
class MemoryRecord:
    """Sec29 Memory Record Schema -- vollstaendig, jedes Pflichtfeld
    vorhanden (leere Werte erlaubt wo sachlich zutreffend, aber das Feld
    existiert immer)."""
    memory_id: str
    layer: str
    scope: str                      # z.B. "GLOBAL", "WXK_TAX", "WXK_TAX/KSZ"
    category: str
    rule_key: str                   # stabile, menschenlesbare Kennung fuer Konflikterkennung
    title: str
    rule_text: str
    canonical_status: str
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = ""
    source_type: str = "GENERAL"    # GENERAL / GOLDEN_CASE / CASE_SPECIFIC / PRIMARY_SOURCE
    authority: str = ""
    evidence_pointer: str = ""
    confidence: float = 0.8
    valid_from: str = ""
    valid_until: str = ""
    freshness_required: bool = False
    review_trigger: str = ""
    sensitivity: str = Sensitivity.NORMAL
    tenant_scope: str = "GLOBAL"    # GLOBAL oder eine konkrete tenant_id
    supersedes: str = ""            # memory_id des abgeloesten Eintrags
    superseded_by: str = ""
    promotion_state: str = CanonicalStatus.CANDIDATE
    rollback_reference: str = ""
    guard: str = ""                 # Verweis auf Regressionstest/technischen Guard
    regression_test: str = ""
    last_reviewed: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


REGISTRY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_records (
    memory_id           TEXT PRIMARY KEY,
    layer                TEXT NOT NULL,
    scope                TEXT NOT NULL,
    category             TEXT NOT NULL,
    rule_key             TEXT NOT NULL,
    title                TEXT NOT NULL,
    rule_text            TEXT NOT NULL,
    canonical_status     TEXT NOT NULL,
    version              INTEGER NOT NULL DEFAULT 1,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    source               TEXT,
    source_type          TEXT NOT NULL DEFAULT 'GENERAL',
    authority            TEXT,
    evidence_pointer     TEXT,
    confidence           REAL NOT NULL DEFAULT 0.8,
    valid_from           TEXT,
    valid_until          TEXT,
    freshness_required   INTEGER NOT NULL DEFAULT 0,
    review_trigger       TEXT,
    sensitivity          TEXT NOT NULL DEFAULT 'NORMAL',
    tenant_scope         TEXT NOT NULL DEFAULT 'GLOBAL',
    supersedes           TEXT,
    superseded_by        TEXT,
    promotion_state      TEXT NOT NULL DEFAULT 'CANDIDATE',
    rollback_reference   TEXT,
    guard                TEXT,
    regression_test      TEXT,
    last_reviewed        TEXT
);
CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory_records(scope);
CREATE INDEX IF NOT EXISTS idx_memory_layer ON memory_records(layer);
CREATE INDEX IF NOT EXISTS idx_memory_rule_key ON memory_records(rule_key);
CREATE INDEX IF NOT EXISTS idx_memory_status ON memory_records(canonical_status);

CREATE TABLE IF NOT EXISTS memory_audit_log (
    audit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id    TEXT NOT NULL,
    action       TEXT NOT NULL,
    detail       TEXT,
    timestamp    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS memory_snapshots (
    snapshot_id   TEXT PRIMARY KEY,
    created_at    TEXT NOT NULL,
    record_count  INTEGER NOT NULL,
    payload_json  TEXT NOT NULL
);
"""


class MemoryRegistry:
    """Zentrale Registry. Ein SQLite-File pro Produkt (Tenant-Trennung
    Sec19/Multi-Tenant Memory Isolation: separate DB-Datei ist die
    staerkste Isolationsform, keine gemeinsame Tabelle ueber Produkte)."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        con = sqlite3.connect(self.db_path)
        con.executescript(REGISTRY_SCHEMA)
        con.commit()
        con.close()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _audit(self, con: sqlite3.Connection, memory_id: str, action: str, detail: str = "") -> None:
        con.execute(
            "INSERT INTO memory_audit_log (memory_id, action, detail) VALUES (?, ?, ?)",
            (memory_id, action, detail),
        )

    def add(self, record: MemoryRecord, allow_active: bool = False) -> str:
        """Fuegt einen neuen Record hinzu. Erzwingt (Write Guard, nicht nur
        Konvention):
        - Sec35 NO_PERSONAL_TO_GLOBAL_PROMOTION: source_type GOLDEN_CASE/
          CASE_SPECIFIC + layer in (L1,L2) + canonical_status ACTIVE wird
          IMMER geblockt, unabhaengig vom allow_active-Flag.
        - Sec30: kein zweiter ACTIVE-Eintrag mit gleichem rule_key+scope,
          ausser supersedes ist gesetzt und zeigt auf den alten Eintrag
          (der wird dann automatisch auf SUPERSEDED gesetzt).
        - Sec25: volatile-state-verdaechtiger Text darf nicht in Layern
          ungleich L5 landen.
        - allow_active=False (Default): neue Eintraege starten immer als
          CANDIDATE, unabhaengig vom uebergebenen canonical_status (Sec34
          Promotion-Pflicht CANDIDATE->...->ACTIVE). allow_active=True ist
          fuer kontrollierte Migrations-Importe bereits VERIFIZIERTER
          Bestandsregeln gedacht (z.B. Migration bestehender Skill-Lessons).
        """
        if record.layer not in MemoryLayer.ALL:
            raise MemoryConstitutionError(f"Unbekannter Layer: {record.layer}")
        if record.canonical_status not in CanonicalStatus.ALL:
            raise MemoryConstitutionError(f"Unbekannter Status: {record.canonical_status}")

        if (record.source_type in ("GOLDEN_CASE", "CASE_SPECIFIC") and
                record.layer in (MemoryLayer.L1_DOMAIN_INVARIANTS, MemoryLayer.L2_PRODUCT_INVARIANTS) and
                record.canonical_status == CanonicalStatus.ACTIVE):
            raise PersonalToGlobalPromotionBlocked(
                f"BLOCKED: source_type={record.source_type} darf nicht direkt als "
                f"{record.layer} mit Status ACTIVE geschrieben werden (Sec35). "
                f"Erst generalisieren (OBSERVATION->CANDIDATE->GENERALIZE->TEST->"
                f"REVIEW->VERIFIED->PROMOTED)."
            )

        # Sec28 L6 RESTRICTED/SENSITIVE: ein Record mit sensitivity=RESTRICTED
        # darf NIEMALS in einem globalen/produktweiten Layer (L1-L3) ACTIV
        # werden -- er gehoert entweder nach L4 (fallgebundene Referenz, mit
        # begrenzter Sichtbarkeit) oder bleibt explizit L6. Dies ist eine
        # eigenstaendige Pruefung neben der source_type-Pruefung oben, weil
        # ein Record durchaus source_type=GENERAL aber trotzdem persoenliche/
        # sensible Daten enthalten kann (die beiden Signale sind unabhaengig).
        if (record.sensitivity == Sensitivity.RESTRICTED and
                record.layer in (MemoryLayer.L1_DOMAIN_INVARIANTS, MemoryLayer.L2_PRODUCT_INVARIANTS,
                                  MemoryLayer.L3_VERIFIED_GENERAL_LESSONS) and
                record.canonical_status == CanonicalStatus.ACTIVE):
            raise PersonalToGlobalPromotionBlocked(
                f"BLOCKED: sensitivity=RESTRICTED darf nicht in {record.layer} ACTIVE werden "
                f"(Sec28 SENSITIVE_DATA_REQUIRES_NECESSITY) -- gehoert nach L4 (case-scoped) "
                f"oder L6 (restricted), nie als globale/produktweite aktive Regel."
            )

        if record.layer != MemoryLayer.L5_LIVE_SSOT_RUNTIME_STATE:
            combined_text = f"{record.title} {record.rule_text}"
            if _VOLATILE_STATE_PATTERNS.search(combined_text):
                raise VolatileStateInMemoryError(
                    f"BLOCKED: Record enthaelt volatilen Zustand (Testzahlen/Hash/Build-ID) "
                    f"in Layer {record.layer} -- gehoert nur nach L5 als SSOT-Pointer, "
                    f"nie als eingebrannter Fakt (Sec25/Sec40)."
                )

        if not record.memory_id:
            record.memory_id = f"MEM-{uuid.uuid4().hex[:12]}"

        if not allow_active:
            record.canonical_status = CanonicalStatus.CANDIDATE
            record.promotion_state = CanonicalStatus.CANDIDATE

        con = self._connect()
        try:
            if record.canonical_status == CanonicalStatus.ACTIVE:
                existing_active = con.execute(
                    "SELECT memory_id FROM memory_records WHERE rule_key=? AND scope=? "
                    "AND canonical_status='ACTIVE' AND memory_id != ?",
                    (record.rule_key, record.scope, record.memory_id),
                ).fetchall()
                if existing_active:
                    if not record.supersedes:
                        raise ConflictingActiveRuleError(
                            f"BLOCKED: bereits ein ACTIVE-Eintrag fuer rule_key={record.rule_key!r} "
                            f"scope={record.scope!r} vorhanden ({[r['memory_id'] for r in existing_active]}) "
                            f"-- neuer Eintrag muss 'supersedes' explizit setzen (Sec30)."
                        )
                    for row in existing_active:
                        con.execute(
                            "UPDATE memory_records SET canonical_status='SUPERSEDED', "
                            "superseded_by=?, updated_at=? WHERE memory_id=?",
                            (record.memory_id, datetime.now(timezone.utc).isoformat(), row["memory_id"]),
                        )
                        self._audit(con, row["memory_id"], "SUPERSEDED", f"by {record.memory_id}")

            d = record.to_dict()
            d["freshness_required"] = int(d["freshness_required"])
            cols = ", ".join(d.keys())
            placeholders = ", ".join("?" for _ in d)
            con.execute(f"INSERT INTO memory_records ({cols}) VALUES ({placeholders})", list(d.values()))
            self._audit(con, record.memory_id, "ADDED", f"status={record.canonical_status}")
            con.commit()
        finally:
            con.close()
        return record.memory_id

    def promote(self, memory_id: str, to_status: str, reviewer: str = "") -> None:
        """Sec34 Promotion-Pflicht: CANDIDATE -> ... -> VERIFIED -> ACTIVE.
        Erzwingt, dass nicht direkt von CANDIDATE nach ACTIVE gesprungen
        wird (muss ueber VERIFIED)."""
        con = self._connect()
        try:
            row = con.execute("SELECT * FROM memory_records WHERE memory_id=?", (memory_id,)).fetchone()
            if row is None:
                raise MemoryConstitutionError(f"Unbekannte memory_id: {memory_id}")
            current = row["canonical_status"]
            if to_status not in CanonicalStatus.ALL:
                raise MemoryConstitutionError(f"Unbekannter Zielstatus: {to_status}")
            if to_status == CanonicalStatus.ACTIVE and current == CanonicalStatus.CANDIDATE:
                raise MemoryConstitutionError(
                    "BLOCKED: kein Direktsprung CANDIDATE->ACTIVE erlaubt -- muss erst VERIFIED "
                    "durchlaufen (Sec34 Promotion-Pflicht)."
                )
            if (row["source_type"] in ("GOLDEN_CASE", "CASE_SPECIFIC") and
                    row["layer"] in (MemoryLayer.L1_DOMAIN_INVARIANTS, MemoryLayer.L2_PRODUCT_INVARIANTS) and
                    to_status == CanonicalStatus.ACTIVE):
                raise PersonalToGlobalPromotionBlocked(
                    f"BLOCKED: {memory_id} hat source_type={row['source_type']} und darf in "
                    f"{row['layer']} nicht auf ACTIVE promoted werden (Sec35)."
                )
            if (row["sensitivity"] == Sensitivity.RESTRICTED and
                    row["layer"] in (MemoryLayer.L1_DOMAIN_INVARIANTS, MemoryLayer.L2_PRODUCT_INVARIANTS,
                                      MemoryLayer.L3_VERIFIED_GENERAL_LESSONS) and
                    to_status in (CanonicalStatus.VERIFIED, CanonicalStatus.ACTIVE)):
                raise PersonalToGlobalPromotionBlocked(
                    f"BLOCKED: {memory_id} hat sensitivity=RESTRICTED und darf in {row['layer']} "
                    f"nicht auf {to_status} promoted werden (Sec28)."
                )

            if to_status == CanonicalStatus.ACTIVE:
                existing_active = con.execute(
                    "SELECT memory_id FROM memory_records WHERE rule_key=? AND scope=? "
                    "AND canonical_status='ACTIVE' AND memory_id != ?",
                    (row["rule_key"], row["scope"], memory_id),
                ).fetchall()
                if existing_active and not row["supersedes"]:
                    raise ConflictingActiveRuleError(
                        f"BLOCKED: Promotion auf ACTIVE wuerde Konflikt erzeugen -- "
                        f"bereits ACTIVE: {[r['memory_id'] for r in existing_active]}, "
                        f"kein supersedes gesetzt."
                    )
                # Sec30: bei erlaubtem supersedes werden die alten ACTIVE-
                # Eintraege real auf SUPERSEDED gesetzt (derselbe Effekt wie
                # in add(), hier fuer den Promote-Pfad -- vorher fehlte
                # dieser Schritt komplett, was zu 2 gleichzeitig ACTIVE
                # Eintraegen fuehrte, siehe Red-Team Test 3/6 Root Cause).
                now_supersede = datetime.now(timezone.utc).isoformat()
                for r in existing_active:
                    con.execute(
                        "UPDATE memory_records SET canonical_status='SUPERSEDED', "
                        "superseded_by=?, updated_at=? WHERE memory_id=?",
                        (memory_id, now_supersede, r["memory_id"]),
                    )
                    self._audit(con, r["memory_id"], "SUPERSEDED", f"by {memory_id} via promote()")

            now = datetime.now(timezone.utc).isoformat()
            con.execute(
                "UPDATE memory_records SET canonical_status=?, promotion_state=?, "
                "updated_at=?, last_reviewed=? WHERE memory_id=?",
                (to_status, to_status, now, now if reviewer else row["last_reviewed"], memory_id),
            )
            self._audit(con, memory_id, "PROMOTED", f"{current} -> {to_status} by {reviewer or 'unknown'}")
            con.commit()
        finally:
            con.close()

    def get(self, memory_id: str) -> dict | None:
        con = self._connect()
        try:
            row = con.execute("SELECT * FROM memory_records WHERE memory_id=?", (memory_id,)).fetchone()
            return dict(row) if row else None
        finally:
            con.close()

    def retrieve(self, scope: str | None = None, category: str | None = None,
                 include_non_active: bool = False, tenant_scope: str | None = None) -> list[dict]:
        """Sec33 Retrieval-Ranking: Scope-Match > Canonical-Status >
        Authority > Freshness > Evidence > Confidence > Version >
        Applicability. Ein aelterer aber semantisch aehnlicher Eintrag darf
        eine aktuelle kanonische ACTIVE-Regel nicht ueberschreiben -- hier
        umgesetzt als strikte Sortierung, ACTIVE + neuere last_reviewed
        immer vor SUPERSEDED/DEPRECATED, unabhaengig von Aehnlichkeit."""
        con = self._connect()
        try:
            query = "SELECT * FROM memory_records WHERE 1=1"
            params: list = []
            if not include_non_active:
                query += " AND canonical_status = 'ACTIVE'"
            if scope:
                query += " AND (scope = ? OR scope = 'GLOBAL')"
                params.append(scope)
            if category:
                query += " AND category = ?"
                params.append(category)
            if tenant_scope:
                query += " AND (tenant_scope = ? OR tenant_scope = 'GLOBAL')"
                params.append(tenant_scope)
            rows = [dict(r) for r in con.execute(query, params).fetchall()]
        finally:
            con.close()

        status_rank = {CanonicalStatus.ACTIVE: 0, CanonicalStatus.VERIFIED: 1,
                        CanonicalStatus.CANDIDATE: 2, CanonicalStatus.DEPRECATED: 3,
                        CanonicalStatus.SUPERSEDED: 4, CanonicalStatus.REJECTED: 5}

        def sort_key(r: dict):
            scope_match = 0 if r["scope"] == scope else 1
            return (
                scope_match,
                status_rank.get(r["canonical_status"], 9),
                -(r["confidence"] or 0),
                r["last_reviewed"] or "",
                -(r["version"] or 1),
            )

        rows.sort(key=sort_key)
        return rows

    def detect_conflicts(self, scope: str | None = None) -> list[dict]:
        """Sec31/Sec36 Drift Monitor: findet widerspruechliche ACTIVE-
        Eintraege (gleicher rule_key+scope, mehr als 1x ACTIVE -- sollte
        durch add()/promote() strukturell verhindert sein, dieser Scan ist
        der unabhaengige Beweis dafuer)."""
        con = self._connect()
        try:
            query = ("SELECT rule_key, scope, COUNT(*) as n, GROUP_CONCAT(memory_id) as ids "
                      "FROM memory_records WHERE canonical_status='ACTIVE'")
            params: list = []
            if scope:
                query += " AND scope = ?"
                params.append(scope)
            query += " GROUP BY rule_key, scope HAVING n > 1"
            rows = [dict(r) for r in con.execute(query, params).fetchall()]
        finally:
            con.close()
        return rows

    def detect_stale_freshness(self, as_of: str | None = None) -> list[dict]:
        """Sec21/Sec42: freshness_required=True Eintraege, deren
        last_reviewed vor valid_until liegt bzw. keine last_reviewed
        gesetzt haben -- muessen vor Nutzung gegen die Primaerquelle
        aufgefrischt werden."""
        as_of = as_of or datetime.now(timezone.utc).isoformat()
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT * FROM memory_records WHERE freshness_required=1 AND canonical_status='ACTIVE' "
                "AND (last_reviewed IS NULL OR last_reviewed = '' OR "
                "(valid_until IS NOT NULL AND valid_until != '' AND valid_until < ?))",
                (as_of,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()

    def snapshot(self) -> str:
        """Sec37: Snapshot vor jeder Migration -- kompletter Export als
        JSON in eine eigene Tabelle, Rollback-faehig."""
        con = self._connect()
        try:
            rows = [dict(r) for r in con.execute("SELECT * FROM memory_records").fetchall()]
            snapshot_id = f"SNAP-{uuid.uuid4().hex[:12]}"
            payload = json.dumps(rows, ensure_ascii=False)
            con.execute(
                "INSERT INTO memory_snapshots (snapshot_id, created_at, record_count, payload_json) "
                "VALUES (?, ?, ?, ?)",
                (snapshot_id, datetime.now(timezone.utc).isoformat(), len(rows), payload),
            )
            con.commit()
            return snapshot_id
        finally:
            con.close()

    def rollback_to_snapshot(self, snapshot_id: str) -> int:
        """Sec37: stellt exakt den Zustand des Snapshots wieder her (volles
        Replace, kein Merge -- Rollback muss deterministisch sein)."""
        con = self._connect()
        try:
            row = con.execute(
                "SELECT payload_json FROM memory_snapshots WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
            if row is None:
                raise MemoryConstitutionError(f"Unbekannte snapshot_id: {snapshot_id}")
            records = json.loads(row["payload_json"])
            con.execute("DELETE FROM memory_records")
            for r in records:
                cols = ", ".join(r.keys())
                placeholders = ", ".join("?" for _ in r)
                con.execute(f"INSERT INTO memory_records ({cols}) VALUES ({placeholders})", list(r.values()))
            con.commit()
            return len(records)
        finally:
            con.close()

    def count_by_layer(self) -> dict[str, int]:
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT layer, COUNT(*) as n FROM memory_records GROUP BY layer"
            ).fetchall()
            return {r["layer"]: r["n"] for r in rows}
        finally:
            con.close()
