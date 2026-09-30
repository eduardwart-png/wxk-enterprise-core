# VERBUNDWERK — REFERENCE IMPLEMENTATION BLUEPRINT

**Status:** CANONICAL IMPLEMENTATION PLAN  
**Datum:** 2026-09-29  
**Produkt:** WXK Business Copilot  
**Vertical Pack:** Distribution & Logistics  
**Tenant:** Verbundwerk Deutschland  
**Ziel:** Verbundwerk aus dem heutigen Co-Pilot-/Automation-Stand in eine produktive, weitgehend autonome Order-to-Cash- und Procure-to-Deliver-Referenzimplementierung überführen.

---

## 1. Ausgangslage

Verbundwerk ist kein Greenfield-Projekt. Folgende Bausteine existieren bereits und werden weiterverwendet:

| Bereich | Bestehender Baustein | Status |
|---|---|---|
| Order Lifecycle | 08_AUTOMATION/ORDER_ENGINE/order_state_machine.py | FOUNDATION_VERIFIED |
| Marge | 08_AUTOMATION/MARGIN_GUARD/margin_engine.py | FOUNDATION_VERIFIED |
| Angebot | 08_AUTOMATION/OFFER_ENGINE/offer_engine.py | FOUNDATION_VERIFIED |
| Reorder | 08_AUTOMATION/REORDER_ENGINE | FOUNDATION_VERIFIED |
| Policy | 08_AUTOMATION/POLICY_ENGINE | FOUNDATION_VERIFIED |
| Event Ledger | 08_AUTOMATION/EVENT_LEDGER | FOUNDATION_VERIFIED |
| Human Intervention | 08_AUTOMATION/HUMAN_INTERVENTION | FOUNDATION_VERIFIED |
| Reklamation | 08_AUTOMATION/CLAIM_ENGINE | FOUNDATION_VERIFIED |
| Resilience | 08_AUTOMATION/RESILIENCE | FOUNDATION_VERIFIED |
| Notifications | 08_AUTOMATION/NOTIFICATIONS | FOUNDATION_VERIFIED |
| CRM API | 08_AUTOMATION/CRM_API | FOUNDATION_VERIFIED |
| Italien Workflow | 08_AUTOMATION/ITALIEN_WORKFLOW | PARTIAL |
| Healthchecks | 08_AUTOMATION/HEALTHCHECKS | FOUNDATION_VERIFIED |
| Shared Auth/RBAC/Jobs | wxk-enterprise-core/core | FOUNDATION_VERIFIED |

Wichtige reale Grenzen heute:
- operative Daten liegen noch stark in SQLite/XLSX/JSONL
- Italien-Workflow erzeugt strukturierte Bestellungen, externer Versand ist aber nicht produktiv angebunden
- Angebote enden grundsätzlich bei READY_FOR_APPROVAL/BLOCKED, nicht bei vollständig policy-gesteuertem externem Versand
- keine produktive Invoice-/E-Rechnung-Engine
- keine Bank-/Payment-Reconciliation
- keine produktive Carrier-Quote/Booking/Tracking-Abstraktion
- keine durchgängige Inventory-SSOT für Italien + Deutschland
- Produktphysik/Verpackungsdaten je SKU noch nicht vollständig
- aktuelle Policies enthalten bewusst konservative manuelle Sperren

---

## 2. Zielzustand für Verbundwerk

Ein Standardauftrag soll ohne Eddy/René durchlaufen:

Kunde bestellt
→ Kunde/Kredit/Terms prüfen
→ Produkt- und Preisstatus prüfen
→ Bestand/Verfügbarkeit ermitteln
→ beste Fulfillment-Quelle bestimmen
→ Frachtoptionen bewerten
→ finale Marge prüfen
→ Auftrag bestätigen
→ Lieferantenbestellung erzeugen/übermitteln
→ Carrier buchen
→ Kunde informieren
→ Lieferung verfolgen
→ POD übernehmen
→ Rechnung erzeugen/validieren/versenden
→ Zahlung zuordnen
→ ggf. mahnen
→ Auftrag schließen
→ Planned-vs-Actual lernen

Nur echte Owner-Ausnahmen werden eskaliert.

---

## 3. Verbundwerk Domain Model

Zusätzlich zum Shared Core braucht das Distribution-&-Logistics-Pack:

### Produkte
- sku_id
- interne Artikelnummer
- supplier_sku
- system/familie
- dimension
- variante
- presskontur
- material
- unit_of_measure
- sales_pack
- weight_net
- weight_gross
- length_cm
- width_cm
- height_cm
- volume_m3
- pallet_qty
- pallet_height
- stackable
- long_goods
- hazard_class nullable
- manufacturer
- manufacturing_plant
- country_of_origin
- certificate_status
- sale_status

### Lieferanten
- supplier_id
- contracting_entity
- invoice_entity
- dispatch_location
- currency
- payment_terms
- standard_lead_time
- cutoff_time
- minimum_order
- price_notice_days
- contract_status
- group_affiliates
- escalation_contacts

### Preis
- supplier_price_version
- basis_ek
- volume_ek
- project_ek
- strategic_ek
- valid_from
- valid_until
- freight_included
- incoterm
- evidence_document
- approval_status

### Logistik
- origin
- destination
- service
- carrier
- weight
- volume
- loading_meters
- pieces
- pallets
- quote
- surcharges
- pickup_date
- promised_delivery
- actual_delivery
- tracking_id
- pod
- freight_invoice
- variance

### Bestand
- location: ITALY_CENTRAL / DE_EMERGENCY / CUSTOMER_RESERVED
- on_hand
- reserved
- available
- inbound
- damaged
- blocked
- safety_stock
- reorder_point
- max_stock
- last_count_at

---

## 4. Preis- und Margenlogik

### 4.1 Eine Preisquelle

Die heutige XLSX wird als Übergangsquelle genutzt, aber nicht als endgültige Produkt-SSOT.

Ziel:
- Preisversionen in Postgres
- importierbare Supplier Price Lists
- jede Preisänderung versioniert
- bestehende Angebote behalten ihren Snapshot
- neue Angebote greifen auf gültige Version zurück

### 4.2 Guard Rails

Für Verbundwerk zunächst:

- Standardrohre/Systeme: Zielmarge 35 % auf True Landed Cost
- Fittings/Zubehör: Zielmarge 40 %
- gesicherte Volumen-/Rahmenkunden: 30–35 % blended möglich
- 25–30 % nur policy-gesteuerte Ausnahme
- < 20 % Hard Block
- kein Supplier-EK → kein autonomes Angebot
- kein freigegebener Produktstatus → kein autonomes Angebot
- unbestätigte Fracht → keine harte Liefer-/Margenzusage

Diese Werte bleiben Policy und können später datenbasiert geändert werden.

### 4.3 True Landed Cost

Hersteller-EK
+ tatsächliche/zugeordnete Fracht
+ Handling/Verpackung
+ Zahlungs-/Transaktionskosten
+ Versicherungs-/Schadenreserve
+ Fulfillment
+ relevante Import-/Zollkosten falls Verbundwerk sie tatsächlich trägt
= True Landed Cost

---

## 5. Verbundwerk Logistics Engine

### 5.1 Liefermodi

**DE_EMERGENCY**
- nur definierte A-SKUs
- Notfall/Nachbestellung
- sehr kurze Lieferzeit
- höherer Lagerkapitalanteil

**IT_STANDARD**
- Standard-Sammelgut
- planbare Aufträge
- kostenoptimiert

**IT_PRIORITY**
- schnellere Stückgutoption
- nur wenn Kunden-SLA es verlangt

**IT_EXPRESS**
- Kleinteile/zeitkritisch
- höhere Kosten
- Freight Guard zwingend

**IT_PTL_FTL**
- größere Projekte
- Teilladung/Komplettladung
- projektbezogene Route

### 5.2 Auswahlregel

Die Engine entscheidet anhand:
- Lieferdatum
- tatsächlicher Lagerverfügbarkeit
- Warenwert
- Frachtquote
- Marge nach Fracht
- Produktphysik
- Carrier-Angebot
- historische Termintreue
- Kundentyp
- Baustellenanforderungen

### 5.3 Baustellenpflichtfelder

Vor Buchung:
- genaue Adresse
- Ansprechpartner
- Mobilnummer
- Liefertag/Terminbedarf
- Zufahrt
- Hebebühne
- Stapler
- Langgut
- Zeitfenster
- Abladehinweise
- gewünschte Teillieferungsregel

Fehlende kritische Felder → HOLD statt Blindbuchung.

---

## 6. Lieferzusage

Kundenversprechen wird berechnet aus:

order_received_at
+ order_cutoff_effect
+ supplier_pick_pack_time
+ carrier_pickup
+ carrier_transit_distribution
+ destination/service buffer
= promised_delivery_date

Das System speichert:
- predicted p50
- predicted p90
- promised date
- actual date

Öffentliche Lieferzeit wird nicht auf Marketing-Wunsch, sondern auf reale p90/p95-Leistung gestützt.

---

## 7. Carrier Integration Roadmap

### Phase 1 — Contract Matrix
Reale Frachttabellen einpflegen:
- Paket
- Palette
- Mehrpaletten
- Langgut/LDM
- PTL
- FTL
- Express
- Hebebühne
- Avis
- Insel/Remote
- Maut/Treibstoff
- Fehlzustellung

### Phase 2 — Live Quote
Mindestens ein Carrier-Adapter mit quote().

DHL Freight ist technisch geeignet, da offizielle APIs für europäische palettierte Straßenfracht Preisabfrage und Shipment Booking anbieten, wenn ein Geschäftskundenvertrag vorliegt.

### Phase 3 — Booking
book() + Label/CMR + Referenzen.

### Phase 4 — Tracking
track() + event normalization.

### Phase 5 — ETA/POD
ETA, POD, Dokumente und automatische Kundeninformation.

### Phase 6 — Reconciliation
quoted_cost vs actual_carrier_invoice.

Raben wird als möglicher strategischer Carrier separat geprüft:
- myOrder
- myOffer
- Track & Trace
- ETA
- Dokumente
- EDI/Systemintegration bei ausreichendem Volumen

---

## 8. Inventory Strategy

### 8.1 Start

Kein großes Deutschlandlager.

Zunächst:
- Italienlager als Hauptquelle
- Deutschland-Notfalllager nur für datenbasiert identifizierte A-SKUs

### 8.2 Aufnahme ins Deutschlandlager

Ein SKU wird vorgeschlagen, wenn mehrere Faktoren erfüllt sind:
- hohe Bestellfrequenz
- hohe Notfallquote
- hoher Stillstands-/Servicewert
- überschaubares Kapital
- stabile Nachfrage
- kritische Italienlaufzeit
- wirtschaftliche Lagerreichweite

### 8.3 Auto-Reorder

reorder_point =
expected_demand_during_lead_time
+ safety_stock

Automatische Bestellung nur innerhalb:
- freigegebener Lieferant
- freigegebener Preisversion
- Bestellbudget
- Max-Stock
- Cashflow-Policy
- kein offener Qualitäts-/Recall-Block

---

## 9. Invoice Engine für Verbundwerk

### Pflichtfunktionen
- fortlaufende Rechnungsnummer
- Kundendaten-Snapshot
- Order-/Delivery-Snapshot
- Umsatzsteuerlogik
- Zahlungsziel
- Bankdaten aus Owner-locked Stammsatz
- PDF
- ZUGFeRD
- XRechnung bei Bedarf
- EN-16931-Validierung
- revisionssicherer Originalspeicher
- Storno/Korrektur/Gutschrift
- Audit

### Autonomie

Standardrechnung nach DELIVERED bzw. definierter vertraglicher Rechnungsregel:
A3/A4-fähig nach Abnahme.

Neue Steuerkonstellation oder unbekannter grenzüberschreitender Sonderfall:
MANUAL_REVIEW.

---

## 10. Payment & Dunning

### Eingang
- Banktransaktionen importieren
- Referenz/IBAN/Betrag/Kunde matchen
- vollständige Zahlung automatisch schließen
- Teilzahlung offen halten
- Überzahlung markieren
- unklare Zahlung REVIEW

### Mahnung
Policy:
- friendly reminder
- Mahnung 1
- Mahnung 2
- Eskalation

Keine aggressive Kommunikation ohne definierte Policy.

Owner sieht nur:
- große/ungeklärte Forderung
- Rechts-/Inkassoentscheidung
- außergewöhnlicher Kreditstopp

---

## 11. Procurement / Italien Workflow

Der heutige ITALIEN_WORKFLOW wird nicht ersetzt, sondern zum Supplier Adapter weiterentwickelt.

### Aktuell
- validiert Pflichtfelder
- erzeugt strukturiertes Bestelldokument
- bildet Payload Hash
- loggt Status
- blockiert realen Versand ohne Freigabe

### Ziel
- SupplierPurchaseOrder Aggregate
- maschinenlesbares + menschenlesbares PO
- controlled send
- delivery acknowledgement
- supplier confirmation parse
- quantity/price/date reconciliation
- retry/DLQ
- cancellation/change handling
- supplier performance metrics

Transport:
- bevorzugt API/EDI
- fallback strukturierte E-Mail
- kein „SENT“ ohne Versandnachweis
- kein „CONFIRMED“ ohne Supplier ACK

---

## 12. Customer Portal

Kunde sieht:
- Angebotsstatus
- Auftrag
- bestätigtes Lieferdatum
- Live-Tracking/ETA soweit vorhanden
- Rechnung
- Dokumente
- Wiederbestellung
- Reklamation
- Projektübersicht

Kunde sieht nicht:
- Supplier EK
- interne Marge
- interne Risk Scores
- andere Kunden
- vertrauliche Lieferantendaten

---

## 13. Owner Cockpit Verbundwerk

### Top Cards
- Auftragseingang
- Umsatz
- DB
- Cash In
- offene Forderungen
- gefährdete Lieferungen
- offene Claims
- Stockouts
- Systemstatus

### „Du musst entscheiden“
Nur:
- Hard Floor Preis
- außergewöhnliche Gutschrift
- Bankdatenänderung
- neues Supplier/Carrier Commitment
- Vertragsentscheidung
- Rechtsfall
- große Budgetabweichung
- Steuer-/Gesellschaftsstammdaten
- systemweiter Kill-Switch

### Automatisch erledigt
- Standardangebote
- Standardaufträge
- Buchung nach Policy
- Rechnung
- Tracking-Mails
- Standardmahnung
- Reorder
- Standardclaim innerhalb Policy

---

## 14. Learning Loop

Nach jedem Auftrag:

### Sales
- quote value
- won/lost
- discount
- margin

### Logistics
- promised
- actual
- freight planned
- freight actual
- damage
- attempts

### Inventory
- stockout
- emergency shipment
- reorder accuracy

### Customer
- reorder interval
- basket size
- product mix
- urgency pattern

### Supplier
- confirmation time
- fill rate
- price variance
- delivery variance
- claim rate

### Human
- Intervention minutes
- reason
- automation candidate

Keine Policy ändert sich ungeprüft. Der Learning Layer macht Promotion-Vorschläge mit Evidence.

---

## 15. Datenmigration

### Schritt 1
Bestandsquellen inventarisieren:
- RIETTI_DE_VERTRIEBSMASTER_v1.xlsx
- SQLite
- CRM CSV/SSOT
- Event Ledger
- Order Status
- Price/Negotiation docs

### Schritt 2
Canonical IDs definieren und Mapping sichern.

### Schritt 3
Postgres Schema erzeugen.

### Schritt 4
Dry-run Import mit Counts/Hashes.

### Schritt 5
Reconciliation:
- Anzahl Datensätze
- IDs
- Preise
- Kunden
- Order status
- Events

### Schritt 6
Read-only Shadow Mode.

### Schritt 7
Dual-read verification, KEIN unkontrolliertes Dual-write.

### Schritt 8
Cutover per Feature Flag.

### Schritt 9
SQLite/XLSX auf Read-only/Archive-Rolle reduzieren.

---

## 16. Rollout Phasen

### V0 — Architecture Lock
- Shared Core/Vertical Pack Entscheidung
- Datenmodell
- Interfaces
- Autonomieklassen
- No-Go Regeln

### V1 — Cloud Foundation
- Postgres
- Auth/RLS
- Audit
- Queue
- Storage
- Vault
- Health

### V2 — Core Data Migration
- Produkte
- Kunden
- Preise
- Policies

### V3 — Quote/Order
- Quote Engine
- Order State Machine
- Margin Guard
- Snapshotting
- idempotency

### V4 — Logistics Planning
- Product physical data
- freight matrix
- route engine
- planned delivery

### V5 — Supplier Procurement
- Italy Adapter
- ACK/Reconciliation

### V6 — Carrier Live
- quote/book/track/POD

### V7 — Invoice
- E-Rechnung
- validation
- immutable archive

### V8 — Payment/Dunning
- bank reconciliation
- open items
- reminders

### V9 — Inventory
- Italy availability
- DE emergency stock
- reorder

### V10 — Customer Portal
- self-service
- tracking
- docs
- reorder

### V11 — Learning
- planned vs actual
- scoring
- intervention elimination

### V12 — Controlled Autonomy
- Shadow
- A2
- A3
- A4 per capability

---

## 17. Pilot Abnahme

Ein echter Verbundwerk-Pilot ist erst bestanden, wenn:

- 0 doppelte Aufträge
- 0 doppelte Rechnungen
- 0 falsche Tenant-Zugriffe
- 0 verlorene Jobs
- 100 % Rechnungen technisch validiert
- 100 % Lieferanten-POs mit Evidence
- 100 % Carrier Bookings mit Referenz
- Payment Matching sauber
- Owner kann jeden Betrag rekonstruieren
- jedes Lieferdatum hat Quelle/Modell
- jede Preisversion ist rekonstruierbar
- jede Gutschrift hat Grund/Freigabe
- Restore-Test bestanden
- Kill-Switch funktioniert
- mindestens ein kompletter Auftrag ohne manuellen Schattenprozess durchgelaufen
- wiederholter Lauf mit identischem Event erzeugt keine zweite externe Wirkung

---

## 18. Referenzrolle für WXK

Verbundwerk ist nicht Sondercode.

Alle Verbundwerk-spezifischen Elemente müssen in eine dieser Kategorien fallen:

1. Shared Core Feature
2. Distribution & Logistics Vertical Pack
3. Verbundwerk Tenant Configuration
4. Verbundwerk Connector Configuration
5. Verbundwerk Data

Wenn ein Entwickler einen Sonderfall außerhalb dieser fünf Kategorien anlegen will, ist zuerst zu prüfen, ob ein Architekturproblem vorliegt.

Das ist die zentrale Produktisierungsregel.
