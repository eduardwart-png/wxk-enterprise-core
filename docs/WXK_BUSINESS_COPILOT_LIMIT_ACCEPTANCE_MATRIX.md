# WXK BUSINESS COPILOT — LIMIT ACCEPTANCE MATRIX

**Status:** HARD GATE SPEC  
**Datum:** 2026-09-29  
**Zweck:** Verhindert Schein-Fertigmeldungen. Eine Capability gilt nur als autonom/verkaufsfähig, wenn die zugehörigen Gates mit realer Evidence bestanden sind.

---

## 1. Statuswerte

- NOT_STARTED
- FOUNDATION_ONLY
- IMPLEMENTED_UNVERIFIED
- VERIFIED_SHADOW
- VERIFIED_CONTROLLED
- PRODUCTION_READY
- DEGRADED
- BLOCKED
- SUPERSEDED

Kein „fertig“ ohne PRODUCTION_READY.

---

## 2. Globale Release Gates

Für jede Capability gelten immer:

| Gate | Muss erfüllt sein |
|---|---|
| Functional | Happy Path real funktioniert |
| Data | Eingaben/Outputs eindeutig, keine zweite SSOT |
| Idempotency | Retry/Doppelklick erzeugt keine Doppelwirkung |
| Failure | Timeout/Fehler landet sichtbar in Retry/DLQ |
| Security | Rollen/Tenant/Secrets korrekt |
| Audit | relevante Aktion nachvollziehbar |
| Evidence | externe Wirkungen haben Bestätigung/Referenz |
| Recovery | Fehler/Neustart kann sauber fortgesetzt werden |
| Regression | bestehende Funktionen bleiben grün |
| Observability | Health, Fehler, Queue, letzter Sync sichtbar |
| Rollback/Kill | Capability kontrolliert deaktivierbar |
| Documentation | Interface + Policy + Owner-Ausnahme dokumentiert |

---

## 3. Shared Core

### 3.1 Tenant/Auth/RBAC

PRODUCTION_READY nur wenn:
- Cross-Tenant-Leseversuch blockiert
- Cross-Tenant-Schreibversuch blockiert
- Owner/Admin/Reviewer/Viewer Grenzen getestet
- Session expiry/revoke getestet
- Service Accounts getrennt von Human Users
- Audit actor vorhanden
- Secret nicht im Browser
- RLS + serverseitige Prüfung bei Cloud-Datenbank

SEV-0:
- irgendein Cross-Tenant Leakage

### 3.2 Jobs/Events

PRODUCTION_READY nur wenn:
- gleiche idempotency_key → eine Wirkung
- Worker-Abbruch → Job bleibt
- Retry → keine Doppelwirkung
- Max retries → DLQ
- DLQ im Owner Cockpit sichtbar
- Event/Job correlation_id
- Replay nur für sichere Events
- Outbox/Inbox oder äquivalente atomare Zustellung

### 3.3 Audit

PRODUCTION_READY nur wenn:
- actor
- tenant
- entity
- action
- timestamp
- vorher/nachher wo sinnvoll
- source
- correlation
- keine normale Update/Delete-Route für Audit-Historie

---

## 4. Product & Pricing

PRODUCTION_READY nur wenn:
- jede verkaufbare SKU eindeutige ID
- Produktstatus freigegeben
- Maße/Einheit/Pack eindeutig
- Supplier SKU gemappt
- gültige Preisversion
- Quelle/Evidence
- Mindest-VK/Hard Floor
- Customer Price snapshot
- Angebot rekonstruierbar
- Preisänderung verändert alte Angebote nicht

Adversarial Tests:
- fehlender EK
- abgelaufener EK
- negative/0 Menge
- falsche Einheit
- doppelter Rabatt
- Rabatt + Projektpreis Doppelanwendung
- Freight zweimal eingerechnet
- alte Preisversion nachträglich überschrieben

---

## 5. Quote Engine

PRODUCTION_READY nur wenn:
- Produktstatus geprüft
- Preisstatus geprüft
- Margin Guard geprüft
- Kundenstatus geprüft
- Lieferstatus geprüft
- Gültigkeitsdatum
- vollständiger Snapshot
- Template versioniert
- externe Sendung dedupliziert
- Versandnachweis vorhanden

Automatisch erlaubt nur innerhalb Policy.

---

## 6. Order Engine

PRODUCTION_READY nur wenn:
- Zustandsautomat vollständig
- ungültige Übergänge blockiert
- ORDER_CREATED idempotent
- Storno vor irreversiblem Fulfillment funktioniert
- Storno danach Review
- Teilmengen/Backorder abbildbar
- Cancel/Return/Claim Pfade vorhanden
- jeder kritische Übergang Event + Audit
- Auftrags-Snapshot unveränderlich nachvollziehbar

---

## 7. Logistics Engine

### 7.1 Physical Data Gate

Kein Live-Routing ohne:
- weight
- package count
- dimensions oder belastbare pallet profile
- long-goods status
- pickup origin
- destination
- handling constraints

Fehlende Daten → REVIEW/Quote unavailable, nicht raten.

### 7.2 Quote Gate

PRODUCTION_READY wenn:
- mindestens ein echter Carrier live quoten kann
- Angebots-ID gespeichert
- Preis + Zuschläge gespeichert
- Service/Transit gespeichert
- Quote Ablauf berücksichtigt
- Fehlerpfad/Timeout funktioniert

### 7.3 Booking Gate

PRODUCTION_READY wenn:
- Booking API/EDI/MyOrder erfolgreich
- externe Shipment-ID
- Pickup/Delivery Daten
- Carrier confirmation
- Duplicate booking test bestanden
- Cancel/Change policy vorhanden

### 7.4 Tracking Gate

PRODUCTION_READY wenn:
- Carrier Events normalisiert
- ETA updates
- POD/document ingest
- Stale tracking erkannt
- relevante Verspätung löst Event aus

### 7.5 Freight Reconciliation

PRODUCTION_READY wenn:
- Quote ↔ Carrier invoice
- Zuschlagabweichung
- Toleranz
- Review außerhalb Toleranz
- Carrier score update

---

## 8. Supplier Procurement

PRODUCTION_READY wenn:
- Supplier PO aus freigegebenem Order Snapshot
- Supplier EK korrekt
- Lieferadresse korrekt
- neutraler Versandhinweis
- gewünschtes Datum
- Hash/Version
- externer Sendebeweis
- Supplier ACK
- Bestätigung wird gegen PO verglichen
- Abweichung Preis/Menge/Datum → HOLD
- Retry ohne Doppelbestellung

---

## 9. Inventory

PRODUCTION_READY wenn:
- on_hand
- reserved
- available
- inbound
- movement ledger
- atomare Reservierung
- negative available verhindert
- Reconciliation/physical count
- safety stock versioniert
- reorder point nachvollziehbar
- Auto-Reorder durch Budget/Preis/Qualität gegated

Adversarial:
- zwei Aufträge reservieren letzten Bestand gleichzeitig
- Lieferant verschiebt ETA
- Wareneingang teilweise
- beschädigte Ware
- Storno gibt Reservierung zurück

---

## 10. Invoice Engine

PRODUCTION_READY wenn:
- eindeutige Nummernvergabe serverseitig
- Parallelität erzeugt keine Duplikate
- Pflichtangaben
- Steuerlogik
- Order/Delivery Snapshot
- PDF
- ZUGFeRD/XRechnung
- EN-16931 Validator
- original immutable storage
- Versandnachweis
- Storno/Korrektur statt Überschreiben
- Gutschrift referenziert Ausgangsbeleg

Hard Block:
- fehlende Steuerregel
- fehlende rechtliche Entity
- unbekannte Bankdatenquelle
- unvollständige Rechnungsanschrift bei Pflichtfall

---

## 11. Payment/Reconciliation

PRODUCTION_READY wenn:
- Bankfeed/import
- exact match
- tolerant match
- partial payment
- overpayment
- unknown payment
- duplicate transaction
- reversal/chargeback falls relevant
- Audit
- offene Posten
- keine automatische Änderung von Bankstammdaten aus Zahlungsdaten

---

## 12. Dunning

PRODUCTION_READY wenn:
- Fälligkeit
- Grace period
- bereits bezahlt check
- disputed invoice check
- Reminder dedup
- template version
- Versandnachweis
- Eskalationsgrenze
- Kunden-/Projekt-Sonderregel

---

## 13. Claims/Returns

PRODUCTION_READY wenn:
- Claim class
- Evidence upload
- Shipment/Order linkage
- replacement/refund decision policy
- Gutschriftlimit
- Supplier/Carrier recourse
- status updates
- Abschluss + tatsächliche Kosten
- Learning update

Owner required:
- Haftungsanerkenntnis
- Rechtsstreit
- große Kulanz
- große Gutschrift über Limit

---

## 14. Customer Portal

PRODUCTION_READY wenn:
- tenant/customer isolation
- nur eigene Daten
- Order status
- invoices
- tracking
- documents
- reorder
- claim
- download authorization
- expired links
- mobile QA
- accessibility baseline
- AI disclosure falls Chat/AI integriert

---

## 15. Hermes Gate

Hermes darf eine Capability nur nutzen, wenn Registry zeigt:
- required capabilities vorhanden
- status >= geforderter Autonomielevel
- provider/connectors healthy
- auth valid
- quota okay
- policy erlaubt
- sensitivity fit
- evidence sink verfügbar

Hard Rule:
selected_provider == actual_executor

Hermes darf niemals:
- Rechnungsnummer frei erfinden
- Steuerregel frei erfinden
- Lagerbestand frei erfinden
- Carrier quote frei erfinden
- Lieferbestätigung frei erfinden
- Zertifikat frei erfinden
- Bankdaten aus Freitext übernehmen
- Hard Floor umgehen

---

## 16. Learning Gate

Learning Recommendation:
OBSERVED → REPRODUCED → VALIDATED → PROMOTED

PROMOTED nur wenn:
- Datenbasis genannt
- Zeitraum
- Effektgröße
- keine Datenlecks
- Business Guard überprüft
- Regressionstest
- Rollback

Learning darf keine Hard Policy selbstständig überschreiben.

---

## 17. Owner Intervention KPI

Jede Owner-/Human-Aktion wird gemessen.

Klassifikation:
- unavoidable_business_decision
- legal_decision
- budget_decision
- reputational_decision
- temporary_manual_step
- automation_candidate
- system_gap
- false_escalation

Produktziel:
- <30 Min/Kunde/Monat Pilot
- <10 Min/Kunde/Monat stabil
- <5 Min/Kunde/Monat reif

Wiederholte temporary_manual_step / system_gap:
→ automatischer Improvement Candidate.

---

## 18. Daily Brief Gate

Keine Kennzahl ohne Quelle.

Jede Kachel enthält intern:
- metric_id
- data_source
- calculation_version
- freshness
- timestamp
- status

Wenn Daten stale:
nicht grün anzeigen.

---

## 19. Disaster Recovery

PRODUCTION_READY nur wenn:
- automatisiertes Backup
- dokumentierte RPO/RTO
- isolierter Restore
- Hash/Count/Reconciliation
- App startet gegen Restore
- Auth funktioniert
- kritischer Order Flow lesbar
- Secrets separat wiederherstellbar
- mindestens quartalsweise Restore-Probe im reifen Betrieb

---

## 20. Security Red Team

Pflichtfälle:
- IDOR/Cross Tenant
- auth bypass
- expired/revoked session
- role escalation
- webhook spoof
- duplicate webhook
- secret exposure
- SQL injection
- unsafe file upload
- malicious PDF/text prompt injection darf Business Policy nicht überschreiben
- carrier/supplier payload mit manipulierten Instructions
- bank change request via email
- invoice destination tampering
- replay attack

P0/P1 offen → keine Produktionsfreigabe.

---

## 21. Controlled Autonomy Promotion

### A0 → A1
korrekte Datenlese-/Analyse.

### A1 → A2
Entwurf korrekt und reproduzierbar.

### A2 → A3
- mehrere erfolgreiche Shadow Runs
- Policy vollständig
- Retry/Idempotency
- Audit
- geringe Schadenswirkung
- Kill switch

### A3 → A4
- echte Produktionshistorie
- ausreichende Stichprobe
- Fehlerklasse verstanden
- external ACK
- reconciliation
- compensation/rollback
- Monitoring
- kein offenes P0/P1
- Owner explizit für Capability-Klasse freigegeben

Autonomie wird capability-spezifisch vergeben, nicht pauschal für „den Copilot“.

---

## 22. WXK Product Gate

WXK Business Copilot ist als verkaufbares Produkt freigabefähig, wenn:

1. Shared Core kann clean installiert werden.
2. Tenant kann ohne Codeänderung angelegt werden.
3. Branding/Policy/Module sind Konfiguration.
4. Zweiter Tenant beweist Isolation.
5. Verbundwerk-spezifischer Code lebt im Vertical Pack/Adapter, nicht im Core.
6. CI läuft aus frischem Clone.
7. Migrationspfad dokumentiert.
8. Backup/Restore real.
9. Kunden-Onboarding reproduzierbar.
10. Feature Flags ermöglichen stufenweisen Rollout.
11. Module können tenant-spezifisch aktiviert werden.
12. Support-/Incident-Evidence vorhanden.
13. Datenauskunft/Export/Löschung technisch abbildbar.
14. AI-Transparenz und Datenschutzkonzept pro Surface.
15. keine kundenspezifische Parallel-SSOT.

---

## 23. Verbundwerk Golden Pilot Gate

Mindestens folgende reale Fälle müssen erfolgreich sein:

- normaler Handwerkerauftrag
- kleine unwirtschaftliche Bestellung → sinnvolle Alternative
- Priority shipment
- großes Projekt / mehrere Paletten
- teilweise Nichtverfügbarkeit
- Lieferverzug
- Transportschaden
- Storno vor Fulfillment
- Storno nach Fulfillment
- Rechnung
- Teilzahlung
- verspätete Zahlung
- Gutschrift innerhalb Limit
- Gutschrift oberhalb Limit
- Reorder A-SKU
- Lieferantenpreisabweichung
- Carrier Preisabweichung
- Worker/Connector Ausfall
- Retry/Duplicate Event
- Backup Restore

Erst danach darf Verbundwerk als belastbare WXK-Referenzinstallation vermarktet werden.

---

## 24. Definition „LIMIT“

„LIMIT“ bedeutet in diesem Projekt nicht „für immer unveränderlich“.

Es bedeutet:

- keine erkennbare Architektur-Abkürzung
- kein absichtlich offener Kernprozess
- keine bekannte bessere realistische Grundstruktur ignoriert
- keine Fertigmeldung ohne Evidence
- Erweiterbarkeit ohne Rebuild
- Fehlerfälle genauso ernst behandelt wie Happy Paths
- Geld, Daten, Logistik und Compliance durch harte Gates geschützt

Neue reale Evidence darf den Bauplan verbessern. Sie darf ihn aber nicht stillschweigend schwächen.
