# WXK BUSINESS COPILOT — GOLDEN MASTER MANIFEST

**Status:** GOLDEN MASTER — ARCHITECTURE LOCKED  
**Datum:** 2026-09-29  
**Scope:** Architektur, Governance, Produktziel und Umsetzungsreihenfolge  
**Produktive Implementierung:** NOCH NICHT vollständig abgeschlossen

---

## 1. Kanonische Dokumente

Die WXK-Business-Copilot-Architektur besteht verbindlich aus:

1. `WXK_BUSINESS_COPILOT_MASTER_BLUEPRINT_LIMIT.md`
2. `VERBUNDWERK_REFERENCE_IMPLEMENTATION_BLUEPRINT.md`
3. `WXK_BUSINESS_COPILOT_LIMIT_ACCEPTANCE_MATRIX.md`
4. `WXK_BUSINESS_COPILOT_GOLDEN_MASTER_ADDENDUM.md`
5. `ADR-001-SAAS-TRUST-BOUNDARY-ROLE-DATA-PLANE.md`
6. `WXK_BUSINESS_COPILOT_KNOWLEDGE_PRIVACY_EXTENSION.md`
7. `WXK_BUSINESS_COPILOT_FINAL_ADVERSARIAL_ARCHITECTURE_AUDIT_2026-09-29.md`
8. `WXK_BUSINESS_COPILOT_GOLDEN_MASTER_EXECUTION_PLAN.md`

Dieses Manifest setzt den Gesamtstatus auf **GOLDEN MASTER**. Frühere Statusangaben wie `CANONICAL CANDIDATE` in einzelnen Teildokumenten sind damit für den Gesamtverbund superseded.

---

## 2. Verbindliches Zielbild

- WXK Business Copilot = Produkt
- wxk-enterprise-core = Shared Core
- Vertical Packs = branchenspezifische Fähigkeiten
- Tenant Configuration = kundenspezifische Regeln/Branding
- Verbundwerk Deutschland = erste produktive Distribution-&-Logistics-Referenzimplementierung
- Hermes = Router/Orchestrator
- deterministische Engines = Geld/Preis/Marge/Steuer/Bestand/Logistik/Rechnung
- Cloud Data Plane = operative Wahrheit
- Knowledge Layer = kontrollierte, tenant-isolierte Wissensschicht
- Owner = Strategie und echte Ausnahmen, nicht Routinebetrieb

---

## 3. Golden Master Change Rule

Golden Master darf nur geändert werden bei:

- neuer verifizierter Evidence
- regulatorischer Änderung
- nachgewiesenem P0/P1 Architekturproblem
- neuer Capability mit echtem strukturellem Bedarf
- messbarer Verbesserung ohne Regression

Jede Änderung benötigt:
- CHANGE_ID oder ADR
- Reason
- Evidence
- Affected Assets
- Regression Impact
- Rollback/Supersede Path

---

## 4. Wichtigste Schutzregeln

- kein Kunden-Core-Fork
- keine zweite Preis-/Daten-SSOT
- kein Cross-Tenant Access durch Tenant Owner
- keine unkontrollierte KI für Geld/Steuer/Bestand/Logistik
- keine Doppelwirkung bei Retry
- keine externe Aktion ohne Evidence
- keine stille Bankdatenänderung
- keine autonome globale Preisänderung
- kein Auto-Reorder ohne Cashflow-Gate
- kein RAG ohne Tenant-/Permission-Filter
- keine Produktivfreigabe ohne Acceptance Matrix

---

## 5. Statuswahrheit

### Architektur
**GOLDEN MASTER**

### Ausführungsreihenfolge
**EXECUTION CANON**

### Shared Core aktueller Code
**PHASE 1 (SHARED CORE HARDENING) COMPLETE — Cloud Foundation (Phase 2) offen**

CHANGE_ID: PHASE1-SHARED-CORE-HARDENING-20260930
Reason: Execution Plan Phase 1 (Role Model Migration, Access Contract,
Configuration Abstraction, Health Interface) vollständig umgesetzt.
Evidence: PRs #5/#6/#7 in wxk-enterprise-core, je mit echtem BREAK-Test
(Regression real in den Produktivcode injiziert, Test fängt sie, Fix
wiederhergestellt) und Blast-Radius-Test gegen den echten Verbundwerk-
Konsumenten (164/164 Tests weiterhin grün). Testsuite 45→53→69→79 Tests,
alle grün, CI grün auf frischem Klon.
Affected Assets: core/db.py, core/auth.py, core/rbac.py,
core/access_contract.py (neu), core/health.py, core/health_interface.py
(neu), core/backup_restore.py.
Regression Impact: keine — additive Migrationen, Legacy-Rollennamen
transparent abgebildet, bestehende Konsumenten unverändert kompatibel.
Rollback/Supersede Path: git revert der PRs #5/#6/#7 in umgekehrter
Reihenfolge stellt den Vorzustand wieder her (keine destruktiven
Migrationen, alte Spalten/Rollen bleiben erhalten).

Noch offen (Phase 1 deckt NICHT ab): Cloud Foundation (Phase 2), Canonical
Data Model (Phase 3) und alle Folgephasen bleiben unverändert offen. Aus
"Phase 1 complete" darf NICHT abgeleitet werden, dass das Produkt
produktionsreif ist — Acceptance Matrix §3.1 ist erfüllt, weitergehende
Kriterien (Cloud Data Plane, Multi-Tenant-SaaS-Betrieb) nicht.

### Verbundwerk
**REFERENCE BLUEPRINT COMPLETE — Produktive Implementierung offen**

### WXK SaaS-Produkt
**PRODUCT BLUEPRINT COMPLETE — Produktive Implementierung offen**

Diese Trennung ist verbindlich. Niemand darf aus dem Golden-Master-Status der Architektur ableiten, dass das gesamte Produkt bereits gebaut, deployed oder produktiv validiert ist.

---

## 6. Nächster erlaubter Arbeitsmodus

Ab diesem Lock wird nicht mehr frei „brainstormed“, sondern gegen den Golden Master umgesetzt:

FIND
→ MAP TO GOLDEN MASTER
→ BUILD
→ TEST
→ ADVERSARIAL TEST
→ EVIDENCE
→ CONTROLLED PROMOTION
→ LEARN

Hermes arbeitet dabei nach der Reihenfolge des `WXK_BUSINESS_COPILOT_GOLDEN_MASTER_EXECUTION_PLAN.md` und springt nur dann, wenn ein Arbeitspaket durch externen Input blockiert ist und ein späteres Paket unabhängig davon belastbar weitergeführt werden kann.

Keine neue Parallelarchitektur.
