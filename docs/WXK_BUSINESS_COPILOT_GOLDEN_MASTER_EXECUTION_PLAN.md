# WXK BUSINESS COPILOT — GOLDEN MASTER EXECUTION PLAN

**Status:** EXECUTION CANON  
**Datum:** 2026-09-29  
**Ziel:** Den gelockten Golden Master kontrolliert in produktionsfähige Software überführen, ohne Parallelarchitektur, ohne Schein-Fertigmeldungen und ohne unnötige Owner-Arbeit.

---

## 0. Arbeitsregel

Jedes Arbeitspaket läuft nach:

FIND
→ MAP TO GOLDEN MASTER
→ IMPLEMENT
→ TEST
→ ADVERSARIAL TEST
→ EVIDENCE
→ CONTROLLED PROMOTION
→ LEARN

Eine Capability gilt erst als fertig, wenn die zugehörige Acceptance Matrix bestanden ist.

---

## 1. Reihenfolge und Abhängigkeiten

### PHASE 0 — GOLDEN MASTER LOCK
**Status:** DONE

Ergebnis:
- Master Blueprint
- Verbundwerk Reference Blueprint
- Acceptance Matrix
- SaaS/Finance/AI/Knowledge/Privacy Addenda
- Trust-Boundary ADR
- Final Adversarial Architecture Audit
- Golden Master Manifest

Abhängigkeit für alle weiteren Phasen.

---

## 2. PHASE 1 — SHARED CORE HARDENING

**Status:** DONE (2026-09-30, PRs #5/#6/#7 in wxk-enterprise-core)

### Ziele
- Legacy OWNER-Semantik trennen
- lokale Pfadannahmen abstrahieren
- Plattform-/Tenant-Rollen sauber modellieren
- Configuration Registry vorbereiten
- Health Provider Interface schaffen

### Arbeitspakete

#### 1.1 Role Model Migration
- PLATFORM_ROOT
- PLATFORM_ADMIN
- PLATFORM_SUPPORT
- PLATFORM_AUDITOR
- TENANT_OWNER
- TENANT_ADMIN
- TENANT_REVIEWER
- TENANT_OPERATOR
- TENANT_FINANCE
- TENANT_SALES
- TENANT_VIEWER

#### 1.2 Access Contract
- jede API mit tenant context
- deny-by-default
- platform support JIT grants
- break-glass audit

#### 1.3 Configuration Abstraction
- Local Path → Config/Registry
- keine Nutzerpfade als Produktionsannahme

#### 1.4 Health Interface
- product adapter
- dependency checks
- normalized GREEN/DEGRADED/RED

### Abnahme
- Cross-Tenant Read/Write Red-Team
- Tenant Owner kann niemals Platform Root werden
- vorhandene Tests grün
- neue Role Tests
- keine hardcoded Production Paths

---

## 3. PHASE 2 — CLOUD FOUNDATION

### Ziele
Produktionsfähige Data Plane schaffen.

### Bausteine
- PostgreSQL/Supabase oder bestätigte äquivalente Plattform
- Auth
- RLS
- Storage
- Vault
- Queue
- Cron/Scheduler
- Audit
- Backup
- Observability

### Vor Umsetzung benötigte Owner-/externe Inputs
- neues Verbundwerk/WXK-Supabase-Projekt nur nach Kostenprüfung/Freigabe
- Zielregion
- produktive Domain/Environment
- MFA/Owner Accounts

### Abnahme
- DEV/STAGING/PRODUCTION getrennt
- Tenant Isolation real getestet
- Queue Retry/DLQ
- Secret nicht im Browser
- Backup
- isolierter Restore

---

## 4. PHASE 3 — CANONICAL DATA MODEL & MIGRATION

### Ziele
Lokale XLSX/SQLite/JSONL-Wahrheiten in eine versionierte Cloud-SSOT überführen.

### Datenbereiche
- Tenant/Legal Entity
- Kunden
- Lieferanten
- Produkte/SKUs
- Preise
- Verträge
- Zertifikate
- Policies
- Angebote/Aufträge
- Events
- Dokumente

### Migration
1. Source Inventory
2. Canonical ID Mapping
3. Schema
4. Dry Run
5. Counts/Hashes
6. Conflict Report
7. Shadow Read
8. Reconciliation
9. Feature-Flag Cutover
10. Legacy Read-only

### Abnahme
- 100 % Datensatz-Counts erklärt
- keine doppelten IDs
- Preisversionen stimmen
- Kunden stimmen
- Event History erhalten
- Restore funktioniert

---

## 5. PHASE 4 — PRODUCT / PRICE / POLICY

### Ziele
Eine einzige produktive Produkt-/Preiswahrheit.

### Bausteine
- SKU Master
- Physical Profiles
- Supplier SKU Mapping
- Supplier Price Versions
- Customer Price Books
- Hard Floors
- Margin Policies
- Tax Profiles
- Cost Change Engine
- VIES Evidence

### Abnahme
Adversarial:
- fehlender EK
- abgelaufener EK
- falsche Einheit
- doppelter Rabatt
- Preisänderung nach Angebots-Snapshot
- Fracht doppelt eingerechnet

---

## 6. PHASE 5 — QUOTE & ORDER CORE

### Ziele
Angebot und Bestellung vollständig aus dem Shared Core fahren.

### Bausteine
- Quote Aggregate
- immutable snapshot
- external send evidence
- Order State Machine
- cancel/return/claim branches
- idempotency
- reservations
- approval policy

### Abnahme
- identischer Request → ein Auftrag
- altes Angebot bleibt unverändert
- ungültiger Transition blockiert
- Storno vor/nach Fulfillment korrekt
- kein Angebot unter Hard Floor autonom

---

## 7. PHASE 6 — LOGISTICS PLANNING

### Ziele
Automatische Lieferwegentscheidung auf Basis echter Daten.

### Vorbedingungen
- Produktgewicht/Volumen/Länge
- Verpackungseinheiten
- Italien-Origin
- Deutschlanddestination
- reale Frachttabellen
- Zuschlagsmatrix

### Bausteine
- Package/Pallet/LTL/PTL/FTL
- Freight Quote Matrix
- Baustellenanforderungen
- Delivery Promise Engine
- Route Score
- fallback route

### Abnahme
- Route reproduzierbar
- Frachtquote sichtbar
- Marge nach Fracht
- fehlende Physikdaten → HOLD
- keine erfundene 3-Tage-Zusage

---

## 8. PHASE 7 — CARRIER LIVE INTEGRATION

### Reihenfolge
1. Carrier Contract Matrix
2. Quote Adapter
3. Booking Adapter
4. Tracking
5. ETA
6. POD
7. Freight Invoice Reconciliation

### Kandidaten
- DHL Freight
- Raben
- weitere Anbieter erst nach Vergleich

### Owner-/externer Input
- Geschäftskundenvertrag
- API/EDI Zugang
- reale Preis-/Zuschlagslisten

### Abnahme
- echter Quote
- echte Booking-ID
- Duplicate Booking Test
- Tracking
- POD
- Carrier Invoice Abgleich

---

## 9. PHASE 8 — SUPPLIER PROCUREMENT / ITALIEN

### Ziele
Bestehenden Italien-Workflow produktiv machen.

### Bausteine
- Supplier PO
- structured document
- API/EDI wenn möglich
- strukturierte Mail als Fallback
- Send Evidence
- Supplier ACK
- Confirmation Parser
- price/qty/date reconcile
- retry/DLQ
- change/cancel

### Owner-/externer Input
- finaler Vertragspartner
- Bestellkanal
- Preislisten
- Zahlungsbedingungen
- Cut-off
- Lager/Dispatch
- SLA

### Abnahme
- keine Doppelbestellung
- kein SENT ohne Beweis
- kein CONFIRMED ohne ACK
- Abweichung → HOLD

---

## 10. PHASE 9 — INVOICE / E-INVOICE / ACCOUNTING

### Bausteine
- Legal Entity Master
- Tax Profile
- Invoice Number Service
- PDF
- ZUGFeRD
- XRechnung
- EN-16931 Validator
- immutable archive
- Storno/Korrektur/Gutschrift
- Accounting Adapter
- DATEV-kompatibler Export/Connector

### Abnahme
- Parallelrechnung erzeugt keine Nummerndublette
- technische Validierung 100 %
- Beleg jederzeit rekonstruierbar
- E-Rechnung Original erhalten
- Buchhaltungsübergabe nachvollziehbar

---

## 11. PHASE 10 — PAYMENT / AP / DUNNING

### Kundenforderungen
- Bankimport/API
- exact/tolerant matching
- partial/over/under payment
- open items
- dunning

### Lieferantenverbindlichkeiten
- Supplier Invoice Ingest
- PO/Confirmation/Delivery Match
- Payment Approval
- Bank Detail Guard

### Abnahme
- keine Zahlung doppelt zugeordnet
- geänderte Lieferantenbank → Hard Review
- Mahnung nicht bei bezahlter/disputed Rechnung
- Supplier Duplicate Invoice erkannt

---

## 12. PHASE 11 — TREASURY / CASHFLOW

### Bausteine
- aktuelle Liquidität
- erwarteter Cash-In
- fällige AP
- committed PO
- tax reserve
- refund exposure
- 7/30/90 Tage Forecast

### Verwendung
Auto-Reorder und größere Beschaffung brauchen Cash Policy.

### Abnahme
- Bestellung wird bei verletzter Cash Reserve nicht autonom ausgelöst
- Forecast hat Datenquellen und Freshness

---

## 13. PHASE 12 — INVENTORY & REORDER

### Bausteine
- Italy stock
- DE emergency stock
- on_hand/reserved/available/inbound
- stock movement ledger
- ABC/XYZ
- safety stock
- reorder point
- max stock
- auto-reorder

### Abnahme
- atomare Reservierung
- kein negativer verfügbarer Bestand
- Storno gibt Bestand frei
- partial receipt
- damaged stock
- Reorder respektiert Price/Cash/Quality Gates

---

## 14. PHASE 13 — CUSTOMER / SUPPLIER PORTALS

### Customer Portal
- Angebote
- Aufträge
- Lieferstatus
- Rechnungen
- Dokumente
- Reorder
- Claim

### Supplier/Partner Interface
- PO
- ACK
- Lieferstatus
- Dokumente
- Zertifikate
- Abweichungen

### Abnahme
- Isolation
- Mobile
- Accessibility
- Dokumentberechtigung
- AI disclosure falls interaktiver Copilot

---

## 15. PHASE 14 — KNOWLEDGE / RAG / AI GOVERNANCE

### Bausteine
- Tenant Knowledge Layer
- Versioning
- Permissions
- embeddings/vector index
- evidence citations
- conflict detection
- prompt registry
- AI capability registry
- eval pipeline
- provider routing
- prompt injection defense

### Abnahme
- fremder Tenant im Retrieval unmöglich
- superseded Dokument nicht aktuell
- Injection Tests
- sensitive routing
- delete/permission propagation

---

## 16. PHASE 15 — WXK SAAS PRODUCTIZATION

### Bausteine
- Plan/Subscription
- Standard/Premium/Enterprise
- Entitlements
- Usage Meter
- AI Budget
- Seats
- Connector Limits
- Billing
- onboarding wizard
- offboarding/export
- support tier
- SLA

### Gold Test
Zweiter echter Pilot-Tenant wird ohne Code-Fork konfiguriert.

### Abnahme
- Tenant anlegen ohne Codeänderung
- Module konfigurieren
- Branding
- Policy
- Connector
- Export/Offboarding
- Isolation

---

## 17. PHASE 16 — OWNER DAILY BRIEF & CONTROL CENTER

### Owner sieht
- Systemstatus
- Umsatz/DB
- Cash
- Lieferungen
- Risiken
- Forderungen
- Stock
- Claims
- DLQ
- Entscheidungen

### Regel
Keine Kennzahl ohne Datenquelle/Freshness.

### Abnahme
Owner kann normalen Betrieb mobil überblicken, ohne operativen Detailzwang.

---

## 18. PHASE 17 — HUMAN INTERVENTION ELIMINATION

### Ziel
Routineeingriffe messen und systematisch entfernen.

### Prozess
log
→ cluster
→ classify
→ root cause
→ automation candidate
→ build
→ shadow
→ promote
→ measure again

### Zielwerte
- Pilot <30 Min/Kunde/Monat
- stabil <10
- reif <5

---

## 19. PHASE 18 — CONTROLLED AUTONOMY

Capability für Capability:

A0 Observe
→ A1 Recommend
→ A2 Prepare
→ A3 Execute within Policy
→ A4 Committed External Action

Keine pauschale „Copilot ist autonom“-Freigabe.

### A4 nur wenn
- echte History
- keine P0/P1
- external evidence
- idempotency
- reconciliation
- kill switch
- monitoring
- owner capability approval

---

## 20. PHASE 19 — VERBUNDWERK GOLDEN PILOT

Pflichtfälle:
- normaler Handwerkerauftrag
- kleiner unwirtschaftlicher Auftrag
- Express/Priority
- mehrere Paletten
- Backorder
- Lieferverzug
- Transportschaden
- Storno vor/nach Fulfillment
- Rechnung
- Teilzahlung
- Mahnung
- Gutschrift
- Reorder
- Lieferantenpreisabweichung
- Carrierabweichung
- Connector-Ausfall
- Retry/Duplicate Event
- Restore

### Pilot bestanden wenn
- keine Doppelwirkung
- keine verlorene Order
- alle Rechnungen valide
- jede externe Aktion Evidence
- jeder Betrag rekonstruierbar
- Owner nur echte Ausnahmeentscheidungen

---

## 21. PHASE 20 — WXK COMMERCIAL PRODUCT GATE

Erst nach Verbundwerk Golden Pilot:

- zweite Branche/Pilot prüfen
- Pricing WXK
- Verträge/DPA
- Support/SLA
- Onboarding Runbook
- Sales Demo
- Referenz-KPIs
- standardisierte Implementierungspakete

Verbundwerk wird erst dann als belastbare Referenzinstallation vermarktet, wenn die Acceptance Matrix bestanden ist.

---

## 22. Owner Entscheidungen, die nicht künstlich vorweggenommen werden

Diese Punkte werden erst zum richtigen Zeitpunkt eskaliert:

- bezahlte Cloud-Projektanlage
- Carrier-/Supplier-Vertragsabschluss
- Bank-/Payment-Zugang
- DATEV-/Steuerberater-Zugang
- neue globale Verkaufspreise
- Rechts-/Steuerfreigaben
- Produktionsdomain
- größere Budgets
- produktive A4-Capability-Freigabe

Alles andere soll autonom vorbereitet/umgesetzt/getestet werden.

---

## 23. Priorität für Hermes

Hermes arbeitet immer am frühesten ungesperrten Arbeitspaket.

Wenn eine Phase auf externe Daten wartet:
- blockierten Teil markieren
- parallel alle unabhängigen Teile weiterbauen
- keine Owner-Frage stellen, wenn die Information noch nicht notwendig ist

Der Owner wird nur bei einem echten Hard Gate eingeschaltet.

---

## 24. Definition „fertig“

Nicht:
- Code geschrieben
- Dokument vorhanden
- ein Test grün

Sondern:
- Acceptance Matrix bestanden
- Evidence gespeichert
- Failure Paths getestet
- Runtime Health sichtbar
- Rollback/Kill vorhanden
- kein offenes P0/P1
- kanonische Doku aktualisiert
- Learning/Intervention erfasst

---

## 25. Endzustand

Der Endzustand ist erreicht, wenn Verbundwerk seinen normalen operativen Betrieb über den WXK Business Copilot führen kann und der gleiche Shared Core einen zweiten Kunden ohne Core-Fork bedienen kann.

Dann ist aus dem Verbundwerk-Co-Piloten ein belastbares WXK-Produkt geworden.
