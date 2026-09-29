# WXK BUSINESS COPILOT — GOLDEN MASTER MANIFEST

**Status:** GOLDEN MASTER — ARCHITECTURE LOCKED  
**Datum:** 2026-09-29  
**Scope:** Architektur, Governance und Produktziel  
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

### Shared Core aktueller Code
**FOUNDATION — Migration/Erweiterung erforderlich**

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

Keine neue Parallelarchitektur.
