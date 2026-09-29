# WXK BUSINESS COPILOT — MASTER BLUEPRINT LIMIT

**Status:** CANONICAL CANDIDATE  
**Datum:** 2026-09-29  
**Owner:** WXK Wart & Klomfas GbR  
**Erste Referenzimplementierung:** Verbundwerk Deutschland  
**Architekturprinzip:** SHARED CORE + VERTICAL PACKS + TENANT CONFIGURATION  
**Orchestrierung:** Hermes als Router/Orchestrator, nicht als Default-Executor

---

## 0. Ziel

WXK Business Copilot ist kein Chatbot und kein einzelnes Dashboard. Es ist ein mandantenfähiges operatives Betriebssystem für kleine und mittlere Unternehmen, das wiederkehrende Geschäftsprozesse soweit wie technisch, wirtschaftlich und rechtlich sinnvoll automatisiert.

Das Produktziel lautet:

> Der Unternehmer steuert Strategie, Ausnahmen und irreversible Entscheidungen. Der Copilot führt den regelbasierten operativen Betrieb aus, überwacht sich selbst, dokumentiert jede relevante Aktion und verbessert seine Entscheidungen aus realen Betriebsdaten.

Verbundwerk Deutschland ist die erste vollständige Referenzimplementierung für Handel, Distribution, Lieferantensteuerung, Logistik, Bestand, Rechnungen und wiederkehrende Kundenaufträge.

---

## 1. Nicht verhandelbare Grundsätze

1. **Ein Shared Core.** Keine kundenindividuellen Code-Forks. Branchen- und Kundenunterschiede werden über Konfiguration, Policies, Adapter und Vertical Packs abgebildet.
2. **Deterministisch vor generativ.** Preise, Margen, Steuern, Rechnungsnummern, Bestände, Zahlungsstatus, Frachtlogik und Freigabegrenzen werden durch testbaren Code berechnet, nicht durch freie LLM-Ausgabe.
3. **Hermes orchestriert.** Hermes erkennt Aufgabentyp, Datenempfindlichkeit, benötigte Fähigkeiten und Systemzustand und routet an die passende Engine, den passenden Agenten oder Connector.
4. **Event-driven.** Jede relevante Zustandsänderung erzeugt ein Ereignis. Daraus entstehen idempotente Jobs. Kein Auftrag darf durch Neustart, Timeout oder Doppelklick doppelt ausgeführt werden.
5. **Fail closed.** Fehlende Pflichtdaten, unklare Preise, nicht bestätigte Lieferbarkeit oder fehlende Berechtigung führen zu HOLD/REVIEW statt zu Schätzungen.
6. **Zero Silent Failure.** Kein Fehler darf unsichtbar bleiben. Jeder endgültig gescheiterte Job landet in einer sichtbaren Dead-Letter-Queue mit Ursache und nächster Aktion.
7. **Evidence first.** Aussagen wie „versendet“, „bezahlt“, „zugestellt“, „Zertifikat gültig“ oder „Bestand verfügbar“ brauchen maschinenlesbare Evidence.
8. **Policy as Code.** Rabatte, Mindestmargen, Zahlungsziele, Autonomiegrenzen, Reklamationslimits, Preisänderungsregeln und Eskalationen werden versioniert und testbar hinterlegt.
9. **Eine operative Wahrheit pro Domäne.** Keine parallelen Excel-/JSON-/Datenbank-Preisstände. Import- und Exportdateien sind niemals SSOT.
10. **Mobile Owner Control.** Der Owner sieht auf dem Handy: Systemstatus, Umsatz/DB, offene Risiken, Lieferstatus und nur die Entscheidungen, die tatsächlich menschliche Freigabe brauchen.
11. **Lernen aus Realität.** Geplante Kosten/Laufzeiten werden immer mit tatsächlichen Ergebnissen verglichen.
12. **Adapter statt Abhängigkeit.** Spedition, Buchhaltung, Bank, E-Mail, Zahlungsanbieter, Lieferanten und KI-Provider werden über austauschbare Adapter integriert.
13. **Security by default.** Mandantentrennung, Least Privilege, Secret Vault, Audit, Backup/Restore und Kill-Switches sind Kernfunktionen.
14. **Compliance by design.** Rechnungsformate, Datenschutz, KI-Transparenz, Aufbewahrung, Nachvollziehbarkeit und Freigaben werden nicht nachträglich ergänzt.
15. **Kein Fake-Autonomie-Label.** Eine Funktion ist erst autonom, wenn Happy Path, Retry, Duplikate, Teilfehler, Recovery und Audit real getestet sind.

---

## 2. Produktarchitektur

### 2.1 Control Plane

Der Control Plane steuert das Produkt über alle Mandanten:

- Tenant Registry
- Plan-/Lizenzstatus
- Feature Flags
- Capability Registry
- Provider-/Connector-Registry
- Policy-Versionen
- Secret-Referenzen
- Release-/Migration-Status
- Health & Observability
- Incident-/Kill-Switch-Steuerung
- Hermes Routing
- globale Templates und Vertical Packs

Der Control Plane speichert keine unnötigen operativen Kundendaten.

### 2.2 Tenant Data Plane

Jeder Mandant besitzt logisch isolierte Geschäftsdaten.

Standard/Premium:
- gemeinsamer Postgres-Cluster
- jede geschäftliche Tabelle mit tenant_id
- Row Level Security
- serverseitige Authorisierung zusätzlich zur RLS
- keine service-role Credentials im Browser

Enterprise optional:
- dedizierter Datenbank-/Projektbereich
- getrennte Backups/Retention
- kundenspezifische Integrationsgrenzen
- optional private Networking / eigene Region

### 2.3 Surfaces

Vier Oberflächen greifen auf denselben Core zu:

1. **Owner/Operations Cockpit**
   - Tagesstatus
   - Ausnahmen
   - Freigaben
   - Umsatz/Deckungsbeitrag
   - Liefer-/Zahlungsrisiken
   - Systemgesundheit

2. **Mitarbeiter-Cockpit**
   - rollenabhängige Aufgaben
   - Kunden/Angebote/Aufträge
   - keine Owner-only Entscheidungen

3. **Kundenportal**
   - Angebote
   - Bestellungen
   - Rechnungen
   - Tracking
   - Dokumente
   - Reklamationen/Nachbestellungen

4. **Supplier/Partner Interface**
   - Lieferantenbestellungen
   - Bestätigungen
   - ETA/Versanddaten
   - Preislistenänderungen
   - Zertifikate
   - Reklamationen

---

## 3. Shared Core

Der Shared Core besteht mindestens aus diesen Modulen:

### Identity & Tenant
- Auth
- Rollen/RBAC
- Sessions
- Tenant-Isolation
- Audit
- API Keys / Service Accounts
- Connector Permissions

### Customer & CRM
- Firmen/Kontakte
- Kundentyp
- Projekte
- Kredit-/Zahlungsstatus
- Kommunikationshistorie
- Next Best Action
- Wiederbestellmuster

### Product & Price
- Produkt
- SKU
- Variante/Dimension
- physische Daten
- Hersteller/Factory
- Zertifikatsstatus
- Lieferanten-SKU
- Preisversionen
- Einkaufspreis
- Ziel-/Max-EK
- Verkaufspreis
- Mindest-VK
- Kundensonderpreis
- Projektpreis
- Gültigkeit
- Quelle/Evidence

### Quote
- Angebotskopf
- Positionen
- Preis-Snapshot
- Liefer-Snapshot
- Margin-Snapshot
- Freigabestatus
- Gültigkeit
- PDF/strukturierter Beleg
- Versionierung

### Order
- Order State Machine
- Positionen
- Reservierungen
- Zahlungsbedingung
- Lieferziel
- Idempotency Key
- Audit Trail
- Cancel/Return/Claim paths

### Procurement
- Supplier Purchase Order
- PO Lines
- Lieferantenbestätigung
- Preis-/Mengenabweichungen
- Liefertermin
- Supplier SLA
- Vendor Score

### Logistics
- Package profile
- Palletization
- Carrier quotes
- Routing
- Booking
- Tracking
- ETA
- POD
- Freight invoice reconciliation
- damage/claim path

### Inventory
- Standorte
- Bestand
- reserviert
- verfügbar
- erwartet
- Bewegungen
- Mindestbestand
- Sicherheitsbestand
- Meldebestand
- ABC/XYZ
- Reorder proposals / auto-reorder policies

### Invoice & Finance Ops
- Rechnung
- Rechnungspositionen
- Steuerlogik
- fortlaufende Nummerierung
- ZUGFeRD/XRechnung
- Validierung
- Korrektur/Storno/Gutschrift
- Zahlung
- Bankabgleich
- Mahnwesen
- offene Posten
- Supplier invoice matching

### Claims & Returns
- Reklamation
- Rückgabe
- Transportschaden
- Herstellerfehler
- Gutschrift
- Ersatzlieferung
- Regress
- Evidence

### Documents & Compliance
- Zertifikate
- Produktdatenblätter
- Verträge
- Rechnungen
- POD
- CMR
- Preislisten
- Versionsstatus
- Ablaufdatum
- Freigabestatus

### Events & Jobs
- Event Ledger
- Durable Queue
- Retry/Backoff
- DLQ
- Outbox
- Webhook Inbox
- Idempotency
- Scheduled Jobs

### Notification
- interne Alerts
- Kundeninformationen
- Lieferstatus
- Mahnungen
- Eskalationen
- Quiet Hours / Dedup / Severity

### Learning & Optimization
- planned_vs_actual
- carrier score
- supplier score
- demand patterns
- reorder accuracy
- human intervention log
- lost opportunities
- margin drift
- delivery promise accuracy

---

## 4. Canonical Data Model

Mindestens folgende Entitäten werden als normalisierte Tabellen bzw. klar versionierte Aggregate modelliert:

- tenants
- users
- roles
- user_roles
- customers
- customer_contacts
- customer_terms
- projects
- products
- skus
- product_physical_profiles
- manufacturers
- factories
- suppliers
- supplier_skus
- supplier_price_versions
- customer_price_books
- customer_price_versions
- certificates
- warehouses
- inventory_balances
- inventory_movements
- inventory_reservations
- demand_history
- quotes
- quote_lines
- orders
- order_lines
- fulfillment_plans
- purchase_orders
- purchase_order_lines
- supplier_confirmations
- carrier_accounts
- carrier_quotes
- shipments
- shipment_events
- delivery_evidence
- invoices
- invoice_lines
- payments
- bank_transactions
- credit_notes
- dunning_cases
- returns
- claims
- documents
- policy_versions
- approvals
- audit_events
- domain_events
- jobs
- dead_letter_items
- human_interventions
- learning_metrics
- system_health_events

Jede geschäftskritische Entität besitzt:
- tenant_id
- stabile ID
- created_at / updated_at
- source / actor
- version oder immutable snapshot
- Status
- Evidence-Verweis, wo erforderlich

---

## 5. Autonomie-Modell

### A0 — Observe
System liest und bewertet, führt aber nichts aus.

### A1 — Recommend
System erzeugt Empfehlung mit Begründung und Zahlen.

### A2 — Prepare
System erstellt vollständigen Entwurf/Dokument/Job, aber keine externe irreversible Aktion.

### A3 — Execute within Policy
System führt reversible oder vertraglich definierte Standardaktionen autonom aus.

Beispiele:
- Standardangebot innerhalb freigegebener Preismatrix
- Versandbuchung innerhalb SLA/Budget
- Rechnung nach validiertem Auftrag
- Statuskommunikation
- Mahnung nach Policy
- Reorder innerhalb definiertem Rahmen

### A4 — Committed External Action
Nur für Capability-Klassen, die ausreichend real getestet, überwacht und rollback-/kompensationsfähig sind.

Immer owner-/rollenpflichtig bleiben mindestens:
- neuer Vertrag oder Vertragsänderung
- neue Preisstrategie / globale Preisänderung
- Preis unter Hard Floor
- neuer Bankempfänger / geänderte Bankdaten
- größere Gutschriften außerhalb Policy
- außergewöhnliche Haftung/Rechtsstreit
- erhebliche Budgetänderung
- irreversible Löschung
- neue hochkritische Integration
- Änderung von Steuer-/Gesellschafts-Stammdaten

---

## 6. Hermes-Orchestrierung

Hermes ist die Kontroll- und Routingebene.

Vor jeder nicht-trivialen Aufgabe prüft Hermes:

1. task class
2. required capabilities
3. data sensitivity
4. policy constraints
5. live connector availability
6. provider health
7. auth/quota
8. quality requirement
9. context requirement
10. cost
11. latency
12. deterministic engine available?
13. evidence requirement
14. rollback/compensation path

Routing-Regel:

> Wenn ein deterministischer, verifizierter Business-Service existiert, wird dieser verwendet. Ein LLM darf ihn erklären oder orchestrieren, aber nicht ersetzen.

Beispiele:
- Rechnung rechnen → Invoice Engine
- Marge → Margin Engine
- Versandoptionen → Logistics Engine
- Bestand → Inventory Engine
- italienische Lieferanten-Mail interpretieren → Hermes + Sprachmodell
- neue Vertragsklausel analysieren → Hermes + Legal Analysis capability
- Code-Fix → geeigneter Coding Provider
- Bild-/Dokumentprüfung → multimodales Modell

selected_provider muss actual_executor entsprechen. Abweichung ist ein Fehler.

---

## 7. End-to-End Order Flow

Canonical Flow:

LEAD
→ QUALIFIED
→ QUOTE_DRAFT
→ QUOTE_VALIDATED
→ QUOTE_SENT
→ CUSTOMER_ACCEPTED
→ ORDER_CREATED
→ ORDER_VALIDATED
→ CREDIT_TERMS_OK
→ STOCK_PLAN_CREATED
→ LOGISTICS_PLAN_CREATED
→ MARGIN_FINAL_OK
→ ORDER_CONFIRMED
→ PROCUREMENT_CREATED
→ CARRIER_BOOKED
→ FULFILLMENT
→ SHIPPED
→ IN_TRANSIT
→ OUT_FOR_DELIVERY
→ DELIVERED
→ INVOICED
→ PAYMENT_OPEN
→ PAID
→ CLOSED

Nebenpfade:
- ON_HOLD
- MANUAL_REVIEW
- CANCEL_REQUESTED / CANCELLED
- PARTIAL_FULFILLMENT
- BACKORDER
- CLAIM_OPEN
- RETURN_REQUESTED
- CREDIT_NOTE_REQUIRED
- PAYMENT_OVERDUE
- FAILED / RECOVERY_REQUIRED

Jeder Übergang:
- prüft Policy
- prüft Precondition
- hat idempotency_key
- schreibt Domain Event
- schreibt Audit Event
- erzeugt ggf. Folgejobs
- ist rekonstruierbar

---

## 8. Price & Margin Engine

### 8.1 True Landed Cost

true_landed_cost =
supplier_net_price
+ allocated_freight
+ packaging
+ handling
+ insurance
+ payment_cost
+ customs/import_if_applicable
+ fulfillment_cost
+ expected_claim_reserve
+ other_attributable_variable_costs

### 8.2 Pricing hierarchy

Priorität:
1. legally/contractually fixed project price
2. customer-specific approved price
3. framework price
4. volume tier
5. standard price book
6. generated proposal within policy

### 8.3 Hard guards

- Mindestmarge je Kundentyp
- Hard Floor unterhalb dessen keine autonome Freigabe
- maximale autonome Rabattspanne
- Freight-to-Revenue Guard
- Gesamt-DB Guard
- Preisgültigkeit
- EK-Evidence
- kein Verkauf eines BLOCKED products

### 8.4 Cost-change engine

Preisänderungen von Lieferanten werden zerlegt in:
- Material
- Energie
- Fracht
- Maut
- Verpackung
- staatliche Abgaben
- sonstige belegte Komponenten

Regeln:
- kein pauschales Durchreichen ohne Nachweis
- nur tatsächlicher Kostenanteil
- keine Doppelberechnung
- symmetrische Reduktion bei fallenden Faktoren
- bestehende bestätigte Projekte/Aufträge geschützt
- Abweichungen oberhalb Policy → Review

---

## 9. Logistics Engine

Die Logistics Engine entscheidet nicht nur nach Preis, sondern nach Gesamtnutzen.

### 9.1 Input

- SKU weight/volume/length
- packaging unit
- pallet type
- stackability
- long-goods flag
- dangerous-goods flag
- origin warehouse
- destination
- site constraints
- desired date
- customer SLA
- inventory availability
- carrier contracts
- live carrier quotes
- historical reliability

### 9.2 Transport classes

- parcel
- half pallet / pallet
- multi-pallet LTL
- PTL
- FTL
- priority
- express
- emergency-stock Germany

### 9.3 Decision score

route_score = weighted(
total_cost,
promised_delivery_probability,
historical_OTIF,
damage_rate,
customer_SLA_fit,
margin_after_freight,
operational_complexity
)

### 9.4 Required outputs

- chosen origin
- chosen carrier/service
- freight net
- surcharge breakdown
- planned pickup
- promised delivery date
- confidence
- margin after freight
- fallback route
- evidence/quote ID

### 9.5 Planned vs Actual

Zu jeder Sendung:
- quoted freight vs invoiced freight
- promised vs actual pickup
- promised vs actual delivery
- damage yes/no
- partial yes/no
- claim yes/no
- delivery attempts
- surcharge variance

Diese Daten aktualisieren Carrier Score und künftige Lieferzusagen.

### 9.6 Carrier adapters

Adapter contract:
- quote()
- book()
- cancel()
- track()
- fetch_documents()
- fetch_invoice_or_cost()
- healthcheck()

Beispiel DHL Freight: Price Quote + Shipment Booking können für europäische palettierte Straßenfracht genutzt werden, sofern ein gültiger Geschäftskundenvertrag besteht.

Raben: myRaben/MyOrder/Track & Trace/ETA/MyOffer; bei größeren Modellen EDI/Systemintegration projektbezogen.

---

## 10. Inventory Engine

### 10.1 Ziele

- möglichst wenig gebundenes Kapital
- hohe Lieferfähigkeit
- Notfallversorgung für A-Artikel
- keine Bauchgefühl-Bestände

### 10.2 Klassifizierung

ABC:
- A = hoher Wert/hohe Geschäftskritikalität
- B = mittel
- C = gering

XYZ:
- X = stabiler Bedarf
- Y = schwankend/saisonal
- Z = unregelmäßig/projektbezogen

### 10.3 Steuergrößen

- average daily demand
- lead time p50/p90
- demand variability
- service level
- safety stock
- reorder point
- max stock
- reserved
- inbound
- backorders

### 10.4 Deutschland-Notfalllager

Ein SKU kommt nur hinein, wenn reale Daten die Entscheidung stützen:
- häufige Nachbestellung
- hoher Baustellenstillstands-Schaden
- kurze Lagerreichweite
- wirtschaftlicher Bestand
- relevante Marge / Kundenbindung

Kein SKU wird allein aufgrund subjektiver Annahme dauerhaft eingelagert.

---

## 11. Invoice & Payment Engine

### 11.1 Invoice

- Rechnung aus unveränderlichem Order-/Delivery-Snapshot
- keine manuelle Neuberechnung
- eindeutige Nummernfolge
- Pflichtangaben
- Steuerregel
- Zahlungsziel
- Bankdaten aus gesperrtem Stammdatensatz
- ZUGFeRD / XRechnung
- technische Validierung vor Versand
- PDF + strukturierter Datenteil
- unveränderliches Archiv
- Korrekturen über Storno/Korrekturrechnung/Gutschrift, nicht Überschreiben

### 11.2 Payment

- Bank-/Payment-Import
- automatic matching
- partial payment
- overpayment
- underpayment
- unknown payment
- refund approval rules
- open receivables
- dunning

### 11.3 Three-way match for procurement

Supplier invoice:
purchase order
↔ supplier confirmation / goods fulfillment
↔ supplier invoice

Abweichung außerhalb Toleranz → HOLD.

---

## 12. Customer Communication

Der Copilot kommuniziert ereignisbasiert, nicht spam-basiert.

Standard:
- Angebot
- Auftrag bestätigt
- Liefertermin bestätigt
- Ware versendet
- relevante ETA-Änderung
- Zustellung
- Rechnung
- Zahlungsbestätigung falls sinnvoll
- Mahnung
- Reklamationsstatus

Jede Nachricht:
- Template-Version
- Datenquelle
- Sprache
- Empfänger
- Evidence
- Versandstatus
- Dedup Key

KI-generierte/interaktive Oberflächen erfüllen die jeweils geltenden Transparenzpflichten. Seit 2. August 2026 gelten in der EU Transparenzpflichten für bestimmte interaktive KI-Systeme; deshalb muss ein kundenorientierter KI-Assistent klar als KI erkennbar sein.

---

## 13. Learning System

Der Learning Layer verändert niemals direkt Geld-/Haftungsregeln.

Er erzeugt:
- OBSERVED
- REPRODUCED
- VALIDATED
- PROMOTED
- SUPERSEDED / REJECTED

Metriken:
- delivery promise error
- carrier OTIF
- supplier confirmation time
- freight variance
- margin variance
- stockout rate
- emergency shipment rate
- customer reorder interval
- claim rate
- quote win/loss
- human intervention minutes

Promotion zu Policy/Rule nur mit:
- Quelle
- Zeitraum
- Stichprobe
- messbarem Effekt
- Regressionstest
- Rollback

---

## 14. Human Intervention Elimination Loop

Jeder manuelle Eingriff wird geloggt:

- unavoidable_business_decision
- legal_decision
- budget_decision
- reputational_decision
- temporary_manual_step
- automation_candidate
- system_gap
- false_escalation

Ziel-KPI:
- initial < 30 Minuten/Kunde/Monat
- danach < 10 Minuten
- Zielzustand < 5 Minuten

Wenn derselbe manuelle Schritt wiederholt auftritt:
1. clustern
2. Ursache bestimmen
3. Risiko bestimmen
4. Automatisierungsvorschlag
5. Test
6. kontrollierter Rollout
7. Intervention erneut messen

---

## 15. Daily Owner Brief

Mobile Startseite:

- Gesamtstatus GREEN / DEGRADED / RED
- Umsatz heute / Woche / Monat
- Auftragseingang
- erwarteter Deckungsbeitrag
- echte Marge nach Fracht
- offene Forderungen
- überfällige Forderungen
- offene Lieferungen
- gefährdete Lieferungen
- Bestandsrisiken
- Claims
- DLQ
- System incidents
- Owner approvals

Beispiel:

18 Aufträge automatisch verarbeitet  
41.280 € Auftragseingang  
13.740 € erwarteter Deckungsbeitrag  
7 Italien-Sendungen gebucht  
2 Aufträge gebündelt / 286 € Fracht gespart  
0 kritische Lieferverzüge  
1 Owner-Entscheidung erforderlich

Owner sieht keine normale Aufgabenliste, sondern nur Ausnahmen.

---

## 16. Security & Compliance Baseline

Pflicht:

- tenant isolation
- RLS für exponierte Postgres-Tabellen
- least privilege
- keine service_role/Secret Keys im Frontend
- Secret Vault
- MFA für privilegierte Nutzer
- immutable/audit-capable event log
- encrypted transport
- encrypted backups
- backup + real restore test
- retention policy
- data export / deletion workflows
- webhook signature validation
- connector credential rotation
- rate limiting
- anomaly detection
- kill switch
- per-capability feature flags
- dependency pinning
- SBOM/Dependency Scan soweit praktikabel

EU AI Act:
- interaktive KI klar als KI kennzeichnen, soweit einschlägig
- use-case risk assessment pro Vertical Pack
- keine stille Ausweitung in Hochrisiko-Anwendungsfälle

E-Rechnung Deutschland:
- EN-16931-kompatibler Output
- XRechnung / ZUGFeRD mindestens unterstützen
- Validator in der Pipeline
- Originalformat archivieren

---

## 17. Reliability Requirements

Hard Requirements:

- 0 Doppelrechnungen aus identischem Business Event
- 0 Doppelbestellungen aus Retry/Doppelklick
- 0 Cross-Tenant Leakage
- 0 still verlorene Aufträge
- 0 stille Preisüberschreibung
- 0 nicht nachvollziehbare Freigabe
- 0 autonome Aktion mit fehlender Pflicht-Evidence
- 0 automatische Bankdatenänderung aus externer Nachricht
- 0 autonome globale Preisänderung

Technische Muster:
- idempotency keys
- transactional outbox
- inbox dedup
- optimistic locking
- immutable snapshots
- retries with backoff
- circuit breakers
- DLQ
- reconciliation jobs
- health probes
- replayable events where safe

---

## 18. Observability

Jeder Dienst liefert:
- health
- readiness
- dependency health
- queue depth
- DLQ depth
- error rate
- latency
- last successful sync
- data freshness
- last reconciliation
- version

Business observability:
- order stuck time
- shipment risk
- payment risk
- invoice validation failures
- inventory risk
- margin drift
- connector failures
- human intervention KPI

---

## 19. WXK Productization

### Shared Core

Immer gleich:
- Identity/Tenant
- Audit
- Events/Jobs
- Policy
- Document
- Invoice
- CRM primitives
- Order primitives
- Notification
- Connector framework
- Hermes bridge
- Observability
- Learning framework

### Vertical Packs

**Distribution & Logistics Pack**
- Procurement
- Supplier management
- Logistics
- Inventory
- freight optimization
- Verbundwerk reference

Weitere Packs später:
- Trades/Service
- Appointment/Field Service
- Property/Facility
- Hospitality
- Lead-to-Project

Neue Packs dürfen Shared Core nicht forken.

### Tenant Configuration

Kundenspezifisch:
- branding
- roles
- products/services
- price policy
- margin policy
- approval limits
- notification templates
- connectors
- SLA
- business hours
- workflow toggles

---

## 20. Produktstufen

### STANDARD
- CRM
- Angebote
- Aufträge
- Rechnungen
- Standard-Automation
- Owner Daily Brief
- Basis-Policies
- begrenzte Connectoren

### PREMIUM
Alles aus Standard plus:
- Inventory
- Logistics routing
- Customer Portal
- Reorder
- Claims
- erweiterte Analytics
- mehr Connectoren
- individuelle Workflows innerhalb Shared Core

### ENTERPRISE
Alles aus Premium plus:
- mehrere Standorte/Unternehmen
- komplexe Lieferanten-/Carrier-Anbindungen
- EDI
- erweiterte Policy Engine
- dedizierte Datenplane optional
- erweiterte Audit-/Compliance-Anforderungen
- kundenspezifische SLA
- Advanced Routing/Forecasting
- Enterprise Support/Change Governance

Wichtig: Dies sind Funktionsstufen, keine drei unabhängigen Codebasen.

---

## 21. Deployment Target

Empfohlenes Zielbild:

- Postgres/Supabase für zentrale operative Daten
- RLS + serverseitige Authorisierung
- durable queue für Business Jobs
- Cron/Scheduler für Reconciliation, Dunning, Reorder, Health
- API Service für deterministische Python Engines
- Web/Mobile responsive Frontend
- Object Storage für Belege
- Vault für Secrets
- Hermes Bridge als orchestrierter Service
- Connector Worker für externe APIs/EDI/Mail
- CI/CD mit migrations- und regressionsgesicherten Releases

Supabase Queues kann durable Postgres-native Jobs mit garantierter Zustellung bereitstellen; Supabase Cron kann wiederkehrende Jobs bzw. Edge Functions terminieren. Vor Implementierung müssen aktuelle Docs/Changelog geprüft werden.

---

## 22. No-Go Architecture

Verboten:

- kundenindividueller Core-Fork
- Preislogik im Frontend
- LLM berechnet steuerliche/rechnerische Wahrheit frei
- Excel als produktive Preis-SSOT
- Rechnungsnummern clientseitig
- Carrier Credentials im Frontend
- service_role im Browser
- direkte externe Aktion ohne Audit/Evidence
- „sent“ ohne externen Nachweis
- automatischer Retry ohne Idempotenz
- Business Events nur in Logtexten
- unversionierte Policies
- stille Änderung bestehender Angebote
- automatische Änderung von Bankdaten aus E-Mail/PDF
- autonome Haftungsanerkennung
- autonome globale Preisänderung
- automatische Selbstfreigabe nach fehlgeschlagenem Gate

---

## 23. Definition of Golden Target

WXK Business Copilot ist als Produktarchitektur GOLDEN TARGET, wenn:

1. Shared Core unabhängig von Verbundwerk deploybar ist.
2. Verbundwerk nur über Vertical Pack + Tenant Config angebunden ist.
3. Ein zweiter Demo-/Pilot-Tenant ohne Code-Fork konfiguriert werden kann.
4. Alle Geld-/Bestands-/Lieferentscheidungen deterministisch reproduzierbar sind.
5. Hermes ausschließlich routet/orchestriert und keine SSOT ersetzt.
6. E2E Order-to-Cash und Procure-to-Deliver funktionieren.
7. Invoice Pipeline validiert E-Rechnungen.
8. Shipment Pipeline kann mindestens einen echten Carrier quote/book/track.
9. Supplier Pipeline kann einen echten externen Auftrag mit ACK verarbeiten.
10. Payment Reconciliation funktioniert.
11. Inventory/Reorder lernt aus realen Bewegungen.
12. Owner Daily Brief zeigt ausschließlich Evidence-basierte Werte.
13. Human Intervention wird gemessen und sinkt.
14. Backup/Restore real bewiesen ist.
15. Chaos-/Retry-/Idempotency-/Security-/Tenant Tests grün sind.
16. Rollback/Kill-Switch für neue Capabilities vorhanden ist.
17. keine P0/P1 bekannte Regression offen ist.
18. Verbundwerk im Pilotbetrieb über einen definierten Zeitraum ohne manuelle Schattenprozesse arbeitet.

---

## 24. Offizielle technische/regulatorische Referenzen

- BMF E-Rechnung FAQ: https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html
- EU AI Act Transparenzleitlinien: https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act
- Supabase Queues: https://supabase.com/docs/guides/queues
- Supabase Cron: https://supabase.com/docs/guides/cron
- DHL Freight APIs: https://developer.dhl.com/dhl-freight
- Raben digitale Logistik/myRaben: https://deutschland.raben-group.com/it-loesungen

---

## 25. Kanonische Architekturentscheidung

**WXK Business Copilot ist das Produkt.**

**wxk-enterprise-core ist der Shared Core.**

**Verbundwerk Deutschland ist die erste produktive Referenzimplementierung des Distribution & Logistics Vertical Pack.**

**Hermes ist der Orchestrator über dem Shared Core.**

Neue Branchen, Kunden und Produkte werden über Vertical Packs, Policies, Konfiguration und Adapter angebunden — nicht durch neue parallele Cores.
