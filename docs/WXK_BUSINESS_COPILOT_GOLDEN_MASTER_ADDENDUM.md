# WXK BUSINESS COPILOT — GOLDEN MASTER ADDENDUM

**Status:** GOLDEN MASTER ADDENDUM  
**Datum:** 2026-09-29  
**Geltung:** Bestandteil der kanonischen WXK-Business-Copilot-Architektur  
**Priorität:** Ergänzt den Master Blueprint und die Acceptance Matrix; bei Lücken in älteren Architekturtexten gilt dieses Addendum.

---

## 1. Zweck

Dieses Addendum schließt die letzten in der adversarialen Gegenprüfung erkannten Unternehmens- und SaaS-Lücken. Es verändert nicht die Grundarchitektur `SHARED CORE + VERTICAL PACKS + TENANT CONFIGURATION`, sondern vervollständigt sie.

Zusätzliche Pflichtdomänen:

1. Legal Entity & Tax Master
2. Accounting/DATEV & Finance Integration
3. Treasury & Cashflow
4. Supplier Invoice / Accounts Payable
5. WXK SaaS Billing & Entitlements
6. Tenant Onboarding / Offboarding
7. Environment / Release / Migration Governance
8. AI Governance / Evals / Prompt Registry
9. Contract / Certificate / Insurance Lifecycle
10. Support / SLA / Incident Operations
11. Public API / Webhooks / Integration SDK
12. Data Lifecycle / Export / Retention / Portability
13. Multi-Currency / Locale / Timezone
14. Delegation of Authority
15. Master Data Governance
16. Cost & Unit-Economics Governance

---

## 2. Legal Entity & Tax Master

Der Business Copilot muss Gesellschaft, Marke und Mandant sauber trennen.

### Entitäten

- legal_entities
- establishments
- tax_profiles
- vat_ids
- bank_accounts
- invoice_number_sequences
- fiscal_periods
- currencies
- payment_terms
- company_addresses
- commercial_register_data
- beneficial/configuration ownership metadata soweit betrieblich erforderlich
- document_issuers

### Regeln

- jede Rechnung gehört exakt einer rechtlichen Einheit
- jede Bankverbindung gehört exakt einer rechtlichen Einheit
- Rechnungsnummernkreise werden je rechtlicher Einheit und Dokumenttyp serverseitig geführt
- Steuer-/Bank-/Gesellschaftsstammdaten sind Owner-locked
- Änderung erfordert starke Authentifizierung + Audit + Vier-Augen-Regel, sofern aktiviert
- externe E-Mail/PDF kann Bank-/Steuerstammdaten niemals selbstständig ändern
- Tenant darf mehrere Legal Entities besitzen, ohne Daten anderer Tenants zu vermischen

### Steuerprofil

Steuerlogik wird nicht in Freitext oder Prompt gehalten, sondern über versionierte tax_profiles und Tax Rules.

Mindestens:
- Inland B2B
- innergemeinschaftliche B2B-Fälle
- steuerfreie/sonderbehandelte Fälle nur nach expliziter Regel
- USt-ID Validierungsstatus
- Nachweiszeitpunkt
- Reverse-Charge Flag nur nach verifizierter Regel
- steuerlicher Review-Status

VIES-Validierungen werden mit Zeitpunkt und Ergebnis als Evidence gespeichert.

---

## 3. Accounting / DATEV / Finance Integration

Der Business Copilot ist nicht automatisch die Finanzbuchhaltung. Er muss jedoch vollständig buchhaltungsfähig und revisionsfähig übergeben können.

### Accounting Adapter Contract

- export_master_data()
- export_outgoing_invoices()
- export_incoming_invoices()
- export_credit_notes()
- export_payments()
- export_booking_proposals()
- attach_document_reference()
- reconcile_export_status()
- healthcheck()

### Pflichtdaten

- Kontierungsregel / booking_rule
- Erlöskonto
- Aufwandskonto
- Steuerkennzeichen
- Kostenstelle / Kostenträger optional
- Beleg-ID
- Kunden-/Lieferantenkonto
- Leistungs-/Belegdatum
- Währung
- Netto/Steuer/Brutto
- Zahlungsstatus

### Grundsatz

DATEV oder ein anderes Buchhaltungssystem wird als austauschbarer Adapter angebunden. Keine Kernlogik darf ausschließlich von einem Anbieter abhängen.

---

## 4. Accounts Payable / Supplier Invoice Engine

Eingangsrechnungen werden als eigener Prozess behandelt.

Flow:

SUPPLIER_INVOICE_RECEIVED
→ DOCUMENT_PARSED
→ SUPPLIER_IDENTIFIED
→ PO_MATCH
→ DELIVERY_MATCH
→ PRICE_QTY_TAX_CHECK
→ APPROVED_FOR_PAYMENT
→ PAYMENT_SCHEDULED
→ PAID
→ RECONCILED

### Three-way / Four-way Match

- Purchase Order
- Supplier Confirmation
- Fulfillment / Delivery Evidence
- Supplier Invoice

Bei Freight:
- Carrier Quote
- Shipment
- Carrier Invoice

### Hard Guards

- geänderte Bankdaten → OWNER/FINANCE REVIEW
- unbekannter Lieferant → REVIEW
- Betrag oberhalb Delegation → APPROVAL
- Dublette → BLOCK
- Rechnung ohne PO bei PO-pflichtigem Supplier → REVIEW
- Mengen-/Preisabweichung außerhalb Toleranz → HOLD

---

## 5. Treasury & Cashflow Engine

Marge allein reicht nicht. Das System muss Liquidität schützen.

### Daten

- current_cash
- expected_customer_receipts
- supplier_due_dates
- carrier_due_dates
- tax_reserves
- payroll/recurring obligations optional
- committed purchase orders
- credit limits
- upcoming refunds
- overdue receivables

### Outputs

- 7-Tage Cash Forecast
- 30-Tage Cash Forecast
- 90-Tage Cash Forecast
- Worst-Case / Base / Confirmed View
- freie Liquidität
- gebundene Liquidität
- fällige Verbindlichkeiten
- Cash Conversion Cycle
- Working Capital
- gefährdete Reorders

### Autonomie

Auto-Reorder darf nicht nur Lagerbedarf und Marge prüfen, sondern zusätzlich:
- Liquiditätsreserve
- bereits gebundene Bestellungen
- Zahlungsziel
- Kundenbonität/erwarteter Cash-In

Wenn Cash Policy verletzt:
→ Reorder vorbereiten, aber nicht auslösen.

---

## 6. WXK SaaS Billing & Entitlements

WXK Business Copilot selbst wird als Produkt betrieben.

### Subscription Model

- tenant_subscription
- plan
- modules
- seats
- usage_meter
- connector_entitlements
- AI_budget
- storage_quota
- support_tier
- billing_period
- status

### Entitlement Engine

Feature-Nutzung basiert auf:
- Plan
- Add-ons
- Tenant Feature Flags
- Vertragsstatus
- Zahlungsstatus
- Rollout Status

Keine Preis-/Planlogik hart im Frontend.

### Usage Metering

Messbar:
- aktive Nutzer
- Aufträge
- Rechnungen
- Speicher
- externe Connector Calls
- KI-Kosten
- Automationsjobs
- ggf. Carrier/Payment pass-through usage

Metering muss abrechenbar, auditierbar und tenant-isoliert sein.

---

## 7. Tenant Onboarding

Neuer Kunde muss ohne Code-Fork reproduzierbar angelegt werden.

Flow:

TENANT_CREATED
→ LEGAL_ENTITY_SETUP
→ USERS_ROLES
→ BRAND_CONFIG
→ MODULE_SELECTION
→ POLICY_TEMPLATE
→ DATA_IMPORT
→ CONNECTORS
→ VALIDATION
→ SHADOW_MODE
→ ACCEPTANCE
→ GO_LIVE

### Onboarding Wizard

Erfasst:
- Firma
- Rechtsform
- Rechnungs-/Steuerdaten
- Benutzer/Rollen
- Produkte/Leistungen
- Kunden/Lieferanten
- Preislogik
- Zahlungslogik
- Dokumentvorlagen
- Integrationen
- SLAs
- Autonomie-Level

### Import

- CSV/XLSX/API möglich
- Dry-run
- Mapping Preview
- Deduplizierung
- Validierung
- Fehlerreport
- Rollback vor Commit
- Import Audit

---

## 8. Tenant Offboarding / Portability

Ein Kunde darf nicht technisch gefangen sein.

Pflicht:
- vollständiger Datenexport
- Dokumentexport
- Rechnungs-/Auditexport soweit zulässig
- Connector-Revoke
- User disable
- Retention state
- Lösch-/Aufbewahrungsregeln
- Export Hash / Manifest
- Abschlussbestätigung

Daten mit gesetzlicher Aufbewahrungspflicht werden nicht unzulässig gelöscht, sondern korrekt gesperrt/retained.

---

## 9. Environment & Release Architecture

Mindestens:

- DEV
- STAGING
- PRODUCTION

### Regeln

- keine Entwicklung direkt in Produktion
- keine produktiven Kundendaten standardmäßig in DEV
- anonymisierte/synthetische Testdaten bevorzugen
- DB-Schemaänderungen versioniert
- Forward Migration + Rollback/Compensation Plan
- Preview/Shadow Tests
- Feature Flags
- Canary/Rollout pro Tenant
- Release Manifest
- Migration Evidence
- Rollback Trigger

### Tenant Rollout

Neue Capability kann:
1. intern
2. Verbundwerk Shadow
3. Verbundwerk Controlled
4. ausgewählte WXK Pilot-Tenants
5. allgemeine Freigabe

durchlaufen.

---

## 10. Configuration Registry

Konfiguration ist ein Produktbestandteil und wird wie Code behandelt.

Versioniert:
- tenant config
- policies
- templates
- connector mappings
- tax rules
- approval limits
- routing weights
- notification rules
- SLA
- prompt templates

Jede Änderung:
- version
- actor
- reason
- diff
- effective_from
- rollback_target

Keine stille Konfigurationsänderung.

---

## 11. AI Governance

### AI Registry

Für jede AI Capability:

- capability_id
- purpose
- permitted data classes
- prohibited data classes
- provider/model route
- fallback
- prompt/template version
- output schema
- confidence/evidence requirement
- human oversight rule
- evaluation suite
- cost ceiling
- latency target
- status

### Prompt Registry

Prompts gehören nicht unversioniert in Quellcode oder Chat-Historien.

Jeder produktive Prompt:
- ID
- Version
- Aufgabe
- Inputs
- Output Schema
- Policy Context
- Safety Constraints
- Testset
- Changelog

### Evaluation

Vor Promotion:
- Golden Test Set
- Regression Set
- adversarial inputs
- hallucination/evidence test
- schema compliance
- privacy test
- cost/latency test

### Provider Independence

Keine Business Capability hängt semantisch exklusiv an einem einzelnen KI-Modell.

Hermes routet über Capability Contracts.

---

## 12. AI Transparency

Kunden- oder Mitarbeiteroberflächen müssen erkennen lassen, wann eine Person direkt mit einem KI-System interagiert, soweit die geltenden Transparenzpflichten greifen.

Pflicht im Produkt:
- AI-interaction marker
- capability disclosure
- handoff to human where appropriate
- logging of AI-assisted vs deterministic action
- kein Vermischen von menschlicher und KI-Kommunikation ohne Kennzeichnung

Stand 2026 gelten die einschlägigen Transparenzpflichten des EU AI Act ab 2. August 2026.

---

## 13. Contract Lifecycle Management

Verträge sind aktive Geschäftsobjekte.

Daten:
- contract_id
- parties
- effective_from
- term
- notice_period
- renewal
- pricing_terms
- SLA
- liability limits
- exclusivity/customer protection
- insurance requirements
- document hash
- signed status
- owner
- obligations

Automationen:
- Kündigungsfristen
- Verlängerung
- Preisfenster
- Rebate Deadline
- SLA Reviews
- Nachweispflichten

Keine autonome Vertragsänderung.

---

## 14. Certificate / Compliance / Insurance Lifecycle

Je Dokument:
- type
- issuer
- holder
- scope/SKUs
- valid_from
- valid_until
- verification_status
- public_claim_status
- evidence source
- replacement document

Automationen:
- 180/90/60/30 Tage Ablaufwarnung
- block sales/public claim bei definierter Criticality
- neue Version erst nach Prüfung aktiv
- alte Version retained
- betroffene Angebote/Website/Produktdaten via Change Propagation markieren

Auch Versicherungsnachweise des Lieferanten/Carriers können so behandelt werden.

---

## 15. Delegation of Authority

Freigaben werden nicht nur über Rolle, sondern über Umfang gesteuert.

Beispiel:
- Mitarbeiter: Rabatt bis X innerhalb Margin Guard
- Vertrieb: Projektangebot bis Y
- Operations: Carrier Booking bis Z
- Finance: Gutschrift bis Limit
- Owner: systemweite Preise, Verträge, Bank-/Steuerstammdaten

Jede Delegation:
- tenant
- role/user
- action
- limit
- conditions
- validity
- approver
- version

---

## 16. Public API / Webhooks / Integration Framework

WXK Business Copilot braucht eine stabile externe Integrationsschicht.

### API Principles

- versioned endpoints
- tenant context
- scoped tokens
- rate limits
- idempotency keys
- request IDs
- pagination
- schema validation
- audit
- API deprecation policy

### Webhooks

- signed
- replay protection
- timestamp tolerance
- event ID dedup
- retry
- delivery log
- DLQ
- secret rotation

### Connector SDK

Jeder Adapter implementiert:
- authenticate()
- capabilities()
- healthcheck()
- read()
- execute()
- evidence()
- retry_classification()
- revoke()

---

## 17. Support & SLA Operations

WXK benötigt einen Produktbetrieb, nicht nur Code.

### Incident Severity

- SEV-0: Datenleck, falsche Geldbewegung, Cross-Tenant, systemische Doppelwirkung
- SEV-1: Bestell-/Rechnungs-/Lieferprozess breit blockiert
- SEV-2: Teilfunktion beeinträchtigt, Workaround vorhanden
- SEV-3: kosmetisch/gering

### Incident Lifecycle

DETECTED
→ CONTAINED
→ IMPACT_ASSESSED
→ MITIGATED
→ RECOVERED
→ ROOT_CAUSE
→ REGRESSION_TEST
→ LESSON_PROMOTED

### Kunden-SLA

Je Plan:
- Supportkanal
- Reaktionsziel
- Recovery-Ziel
- Wartungsfenster
- Statuskommunikation
- Datenexport
- Backup Level

Keine SLA-Versprechen, die technisch nicht gemessen werden.

---

## 18. Data Lifecycle & Retention

Für jede Datenklasse:
- purpose
- legal_basis/category where applicable
- retention
- archival
- delete/anonymize
- exportability
- sensitivity
- access policy

Dokumente mit Buchführungs-/Aufbewahrungspflicht werden entsprechend der geltenden Regeln aufbewahrt.

Bei E-Rechnungen ist insbesondere der strukturierte Originalteil relevant; Archivierung muss Unversehrtheit/Nachvollziehbarkeit sicherstellen.

---

## 19. Locale / Currency / Timezone

Core darf nicht still DE-only sein.

Pflichtfelder:
- tenant timezone
- document language
- currency
- decimal rules
- tax country
- locale

Geld:
- integer minor units oder geeigneter Decimal Type
- niemals binary float für Buchungswahrheit
- currency immer explizit
- FX Rate mit Quelle/Zeitpunkt, wenn benötigt

Zeit:
- intern UTC
- lokale Darstellung tenant-/event-spezifisch
- rechtliche Dokumentdaten lokal nachvollziehbar

---

## 20. Master Data Governance

Golden Records:
- Kunde
- Lieferant
- SKU
- Legal Entity
- Bankkonto
- Steuer-ID
- Carrier
- Vertrag

Pflicht:
- Duplicate Detection
- Merge mit Audit
- Source Priority
- Ownership
- Validation Status
- Effective Date

Keine automatische Zusammenführung hochkritischer Stammdaten ohne sichere Regeln.

---

## 21. Cost & Unit Economics

WXK muss die eigene Wirtschaftlichkeit je Tenant kennen.

Metriken:
- subscription revenue
- connector cost
- AI cost
- infrastructure cost
- support minutes
- storage
- payment cost
- gross margin per tenant
- automation savings estimate

Cost Governor:
- Monatsbudget pro Tenant
- Provider Budget
- Alert Threshold
- hard ceiling für nichtkritische KI-Aufgaben
- keine Abschaltung geschäftskritischer deterministischer Prozesse wegen AI-Budget

---

## 22. FinOps & Vendor Dependency

Jede externe Abhängigkeit besitzt:
- vendor
- service
- criticality
- data classes
- monthly cost
- contract/renewal
- exit plan
- backup provider/fallback
- health monitoring

Single Vendor Lock-in wird bei kritischen Pfaden vermieden, wo wirtschaftlich sinnvoll.

---

## 23. Golden Master Compliance Gates

Zusätzlich zu den bisherigen Acceptance Gates ist PRODUCTION_READY ausgeschlossen, wenn:

- keine eindeutige Legal Entity für Belege feststeht
- Rechnungsnummern-/Tax-Profile unklar sind
- kein Accounting Export/Adapterpfad vorhanden ist
- Bankdaten ungesperrt/still änderbar sind
- kein Tenant On-/Offboarding-Prozess existiert
- DEV/STAGING/PROD nicht getrennt sind
- produktive Prompts/AI Capabilities nicht versioniert/evaluiert sind
- Vertrags-/Zertifikatsabläufe unüberwacht sind
- SaaS Plan/Entitlement nicht serverseitig durchgesetzt wird
- kein Incident-/Supportprozess vorhanden ist
- kein Datenexport/Retention-Konzept vorhanden ist
- keine Cashflow-Grenze für automatische Beschaffung existiert
- keine reale Wiederherstellung getestet wurde

---

## 24. Regulatorische Referenzen, die in der Implementierung aktuell verifiziert werden müssen

- BMF FAQ zur E-Rechnung
- aktuelle GoBD/BMF-Schreiben zur elektronischen Aufbewahrung
- EU-Kommission VIES für USt-ID-Validierung
- EU AI Act Artikel 50 / aktuelle Transparenzleitlinien
- DSGVO / nationale Datenschutzanforderungen je Use Case
- produktspezifische regulatorische Anforderungen je Vertical Pack

Regulatorische Regeln werden als versionierte Compliance Profiles implementiert, nicht als dauerhaft unveränderliche Annahmen im Code.

---

## 25. Schlussregel

Der WXK Business Copilot ist erst dann wirklich ein Produkt, wenn er gleichzeitig:

- Geschäft ausführen kann
- Fehler kontrollieren kann
- Geld nachvollziehen kann
- Daten trennen kann
- einen Kunden sauber aufnehmen und verlassen lassen kann
- seine Kosten kennt
- sich aktualisieren kann
- externe Abhängigkeiten ersetzen kann
- KI-Ausgaben evaluieren kann
- Compliance-Evidence liefern kann
- und die Arbeitslast des Unternehmers messbar reduziert.

Dieses Addendum ist Bestandteil des Golden Master und darf nicht durch eine spätere Implementierung stillschweigend umgangen werden.
