# WXK BUSINESS COPILOT — FINAL ADVERSARIAL ARCHITECTURE AUDIT

**Datum:** 2026-09-29  
**Scope:** Architektur/Governance, nicht produktive Runtime-Abnahme  
**Ergebnis:** ARCHITECTURE_GOLDEN_MASTER_ELIGIBLE

---

## 1. Prüfziel

Die Architektur wurde nicht auf „Vollständigkeit der Feature-Liste“, sondern auf strukturelle Ausfallklassen geprüft:

- falsche Systemgrenzen
- zweite SSOT
- Mandantenleck
- unkontrollierte KI-Entscheidung
- Geld-/Rechnungsfehler
- Logistikverlust
- Lieferanten-Doppelbestellung
- fehlende Accounting-/Tax-Kette
- fehlende SaaS-Produktisierung
- fehlende Datenportabilität
- fehlende Release-/Rollback-Struktur
- fehlendes Knowledge/RAG-Governance
- fehlendes Datenschutz-/Subprozessor-Modell
- fehlende Owner-Ausnahmegrenzen
- Vendor Lock-in
- Betrieb ohne Observability/Recovery

---

## 2. Gefundene Architektur-Lücken und Schließung

### FINDING A-01 — PLATFORM ROOT VS TENANT OWNER

**Severity vor Fix:** P1  
**Problem:** Bestehender lokaler Core verwendet OWNER als mandantenübergreifende Root-Rolle. Für SaaS wäre diese Semantik gefährlich/mehrdeutig.

**Fix:** `ADR-001-SAAS-TRUST-BOUNDARY-ROLE-DATA-PLANE.md`
- PLATFORM_* und TENANT_* strikt getrennt
- Support Zugriff zeitlich/scope-limitiert
- Break-glass auditpflichtig
- Legacy OWNER vor Production zu migrieren

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-02 — LOKALE SQLITE/PFAD-ARCHITEKTUR KÖNNTE ZUM PRODUKTENDZUSTAND WERDEN

**Severity vor Fix:** P1  
**Problem:** aktueller Foundation-Core enthält lokale SQLite-/Windows-Pfadannahmen.

**Fix:** ADR-001:
- PostgreSQL/Data Plane als Produktionsziel
- SQLite nur Development/Test/Migration
- keine hardcoded Local Paths
- Health über Adapter/Registry

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-03 — BUCHHALTUNG/LEGAL ENTITY NICHT VOLLSTÄNDIG ALS EIGENE DOMÄNE

**Severity vor Fix:** P1  
**Problem:** Invoice/Payment vorhanden, aber Gesellschaft, Tax Profile, Buchhaltungsübergabe, Eingangsrechnungen und Bankstammdaten nicht ausreichend als Systemgrenze modelliert.

**Fix:** GOLDEN_MASTER_ADDENDUM:
- Legal Entity Master
- Tax Profiles
- Accounting Adapter/DATEV
- AP/Supplier Invoice
- Three-/Four-way Match
- Bank Data Lock

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-04 — LIQUIDITÄT FEHLTE ALS AUTONOMIE-GATE

**Severity vor Fix:** P1  
**Problem:** Auto-Reorder nur nach Bedarf/Marge könnte Liquidität gefährden.

**Fix:** Treasury & Cashflow Engine:
- 7/30/90-Day Forecast
- Working Capital
- committed PO
- Supplier Due
- Cash Reserve
- Cash Policy als Beschaffungs-Gate

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-05 — WXK ALS SAAS-PRODUKT NICHT VOLLSTÄNDIG ABGEBILDET

**Severity vor Fix:** P1  
**Problem:** Core/Vertical Packs vorhanden, aber Lizenzierung, Entitlements, Metering, On-/Offboarding und Support fehlten.

**Fix:** GOLDEN_MASTER_ADDENDUM:
- SaaS Billing
- Entitlements
- Usage Metering
- Tenant Onboarding
- Tenant Offboarding/Portability
- Support/SLA/Incident Operations

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-06 — RELEASE GOVERNANCE UNTERDEFINIERT

**Severity vor Fix:** P1  
**Problem:** Feature Flags vorhanden, aber DEV/STAGING/PROD, DB Migration, Tenant Canary und Rollback nicht vollständig festgeschrieben.

**Fix:** Environment & Release Architecture:
- DEV/STAGING/PROD
- versionierte Migration
- Shadow/Canary
- per-Tenant Rollout
- Rollback
- Release Manifest

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-07 — AI ROUTING OHNE VOLLSTÄNDIGEN AI-LIFECYCLE

**Severity vor Fix:** P1  
**Problem:** Hermes Routing stark, aber produktive Prompt-/Capability-Versionierung und Evals fehlten als Pflichtdomäne.

**Fix:** AI Governance:
- AI Registry
- Prompt Registry
- Testsets/Evals
- Provider Independence
- Data-class Routing
- Cost/Latency Gates
- AI Transparency

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-08 — TENANT KNOWLEDGE/RAG ALS UNKONTROLLIERTE PARALLELWELT MÖGLICH

**Severity vor Fix:** P1  
**Problem:** Dokumente waren modelliert, aber Retrieval, Quellenpriorität, Vector Index und Prompt Injection nicht ausreichend geregelt.

**Fix:** `WXK_BUSINESS_COPILOT_KNOWLEDGE_PRIVACY_EXTENSION.md`
- Tenant Knowledge Layer
- Evidence Contract
- RAG abgeleitet, niemals SSOT
- Tenant Filter vor Retrieval
- Conflict Detection
- Prompt Injection Boundary
- Source Lifecycle

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-09 — PRIVACY/SUBPROCESSOR-BETRIEB ZU GENERISCH

**Severity vor Fix:** P1  
**Problem:** Security/Retention vorhanden, aber SaaS-Datenschutzbetrieb mit Subprocessor Registry, Datenexport und Offboarding nicht tief genug.

**Fix:** Knowledge & Privacy Extension:
- Privacy Operations
- Subprocessor Governance
- Data Classification
- Export/Delete/Retention
- Data Minimization
- Sensitive Provider Routing

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-10 — CONTRACT/CERTIFICATE ALS STATISCHE DOKUMENTE STATT LIFECYCLE

**Severity vor Fix:** P2  
**Problem:** Ablauf, Renewal, Kündigung, Versicherungsnachweise und Change Propagation nicht vollständig.

**Fix:** Contract + Certificate Lifecycle:
- Fristen
- renewal/notice
- expiry alerts
- public claim status
- change propagation

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-11 — EXTERNE INTEGRATIONEN BRAUCHEN EIN STANDARDISIERTES TRUST CONTRACT

**Severity vor Fix:** P2  
**Problem:** Adapteridee vorhanden, aber Public API/Webhook/Connector SDK nicht vollständig standardisiert.

**Fix:** GOLDEN_MASTER_ADDENDUM:
- versioned APIs
- scoped tokens
- webhook signatures
- replay protection
- dedup
- connector capability contract

**Status:** CLOSED_ARCHITECTURE

---

### FINDING A-12 — CORE KENNT SEINE EIGENE WXK-WIRTSCHAFTLICHKEIT NICHT

**Severity vor Fix:** P2  
**Problem:** Endkundenmarge modelliert, SaaS Unit Economics nicht.

**Fix:** Cost & Unit Economics:
- AI/Infra/Support/Storage/Connector COGS
- Margin per Tenant
- Cost Governor
- Vendor Dependency Registry

**Status:** CLOSED_ARCHITECTURE

---

## 3. Adversarial Szenarien — Architekturantwort

| Angriff/Fehler | Architekturantwort |
|---|---|
| Doppelklick Kunde | Idempotency Key |
| Worker stirbt nach Carrier Booking | External Evidence + Reconciliation vor Retry |
| Webhook doppelt | Inbox Dedup/Event ID |
| Lieferant sendet manipulierte „Instructions“ | untrusted content / Prompt Injection Boundary |
| PDF fordert Bankänderung | Bank Master Owner-Lock |
| Kunde A fragt Daten Kunde B ab | Tenant Isolation + RLS + server authorization |
| Platform Support liest Kunden ohne Anlass | scoped JIT support grant |
| LLM erfindet Fracht | deterministic Logistics Engine/Evidence |
| LLM erfindet Steuerregel | Tax Profile/Hard Block |
| Preis wird geändert | versionierter Price Record, alte Snapshot unverändert |
| Rechnung parallel erzeugt | server sequence/idempotent invoice creation |
| Lieferantenbestellung Retry | Supplier PO idempotency + ACK |
| Spedition nicht erreichbar | Queue/Retry/Fallback/DLQ |
| Carrier Preis höher als Quote | Freight Reconciliation/Tolerance |
| Lieferant erhöht Rohstoff pauschal | Cost-change evidence engine |
| Auto-Reorder trotz Cashmangel | Treasury Gate |
| Zertifikat läuft ab | lifecycle alert/block/public claim propagation |
| KI-Modell wird schlechter | Eval/Capability status/Routing |
| Anbieter fällt aus | adapter/provider fallback |
| Tenant kündigt | export/offboarding/retention/revoke |
| Release fehlerhaft | feature flag/canary/rollback |
| Datenbank verloren | Backup + real Restore Gate |
| RAG liefert altes Dokument | version/supersede/freshness filter |
| Vector Search findet fremden Tenant | tenant filter before retrieval + test |
| KI-Kosten explodieren | Tenant AI budget/Cost Governor |
| Owner bekommt 100 Routineentscheidungen | intervention elimination + policy promotion |

---

## 4. P0/P1 Ergebnis

### Offene P0 Architektur-Lücken
**0**

### Offene P1 Architektur-Lücken
**0**

### Offene P2 Architektur-Lücken
**0 bekannte strukturelle Lücken nach aktuellem Scope**

Dies ist kein Anspruch, dass zukünftige reale Evidence niemals eine bessere Lösung ermöglicht.

---

## 5. Bewusst keine Architektur-Lücke: Implementierung ist noch nicht fertig

Folgende Punkte sind **Implementation Work**, kein fehlender Bauplan:

- Cloud Data Plane aufbauen
- Legacy OWNER Rollen refactoren
- lokale Pfade entfernen
- bestehende SQLite/XLSX-Daten migrieren
- Invoice/E-Rechnung Engine bauen
- Accounting Adapter bauen
- Payment/Bank Reconciliation bauen
- Logistics Engine bauen
- echte Carrier API/EDI anbinden
- Supplier Adapter produktiv versenden/ACK
- Inventory Engine bauen
- Customer Portal bauen
- Knowledge Layer/RAG bauen
- SaaS Entitlements/Metering bauen
- DEV/STAGING/PROD etablieren
- AI Eval Pipeline bauen

Keiner dieser Punkte darf als bereits produktiv behauptet werden.

---

## 6. Audit Verdict

**ARCHITECTURE:** GOLDEN MASTER ELIGIBLE  
**PRODUCTION SYSTEM:** NOT YET PRODUCTION READY  
**VERBUNDWERK REFERENCE IMPLEMENTATION:** BLUEPRINT COMPLETE / IMPLEMENTATION PENDING  
**WXK PRODUCTIZATION:** BLUEPRINT COMPLETE / IMPLEMENTATION PENDING

Die Architektur darf jetzt als verbindlicher Zielzustand gelockt werden.

Änderungen am Golden Master benötigen künftig:
- neue reale Evidence,
- regulatorische Änderung,
- P0/P1 Fund,
- messbare Verbesserung ohne neue strukturelle Regression,
- dokumentierte ADR/Change-ID.
