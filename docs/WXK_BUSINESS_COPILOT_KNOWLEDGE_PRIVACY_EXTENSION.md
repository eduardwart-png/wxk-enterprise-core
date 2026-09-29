# WXK BUSINESS COPILOT — KNOWLEDGE & PRIVACY EXTENSION

**Status:** GOLDEN MASTER EXTENSION  
**Datum:** 2026-09-29  
**Geltung:** Kanonischer Bestandteil des WXK Business Copilot

---

## 1. Tenant Knowledge Layer

Ein echter Copilot benötigt neben Transaktionsdaten eine kontrollierte Wissensschicht.

Quellen können sein:
- Verträge
- Preislisten
- Produktdatenblätter
- Zertifikate
- SOPs
- Sales Playbooks
- E-Mails
- Kunden-/Lieferantenvereinbarungen
- FAQs
- technische Dokumente
- freigegebene externe Quellen

### Knowledge Object

Jedes Wissensobjekt besitzt:
- tenant_id
- document_id
- version
- source
- owner
- access_scope
- document_type
- effective_from
- effective_until
- public/internal/confidential class
- verification_status
- supersedes
- checksum/hash
- ingestion_timestamp

---

## 2. Retrieval Rules

Hermes/AI darf Wissen nur verwenden, wenn:
- Tenant Scope passt
- User/Capability Berechtigung passt
- Quelle nicht BLOCKED ist
- Version gültig ist
- Sensitivity Policy erfüllt ist

Priorität:
1. Owner/explicit locked decision
2. signed/current contract
3. verified operational SSOT
4. verified current document
5. internal guidance
6. historical/archive

Widersprüche erzeugen CONFLICT_DETECTED statt stiller Auswahl.

---

## 3. Citation / Evidence Contract

Geschäftskritische KI-Antworten benötigen Evidence.

Beispiele:
- Preis → Price Version / SKU
- Lieferzeit → Carrier/Supplier Evidence
- Zertifikat → Certificate Record
- Vertrag → Contract Version
- Zahlung → Bank Transaction
- Rechnung → Invoice Record
- technische Produkteigenschaft → approved technical source

Keine Evidence:
→ keine harte Zusage.

---

## 4. RAG / Search

Vector Search kann als Retrieval-Hilfe eingesetzt werden, ist aber niemals die Wahrheitsschicht.

Regeln:
- Embedding Index ist abgeleitet
- Originalquelle bleibt authoritative
- Löschung/Permission Change muss Index propagieren
- Tenant Isolation bis in Vector Retrieval
- Filter vor Similarity Search, nicht erst nach Retrieval
- Version/Supersede berücksichtigen
- stale index sichtbar

---

## 5. Prompt Injection / Untrusted Content

Dokumente, E-Mails, PDFs, Webseiten, Supplier Payloads und Kundentexte gelten als untrusted input.

Instruktionen innerhalb solcher Inhalte dürfen niemals:
- System-/Policy-Regeln überschreiben
- Secrets anfordern
- Bankdaten ändern
- Zahlungen auslösen
- Preise ändern
- Berechtigungen erweitern
- externe Aktionen ohne Capability Policy anstoßen

Content wird als Dateninhalt behandelt, nicht als Systemanweisung.

---

## 6. Knowledge Ingestion Pipeline

INGEST
→ MALWARE/FILE VALIDATION soweit relevant
→ CLASSIFY
→ EXTRACT
→ SOURCE IDENTIFY
→ TENANT/PERMISSION ASSIGN
→ VERSION CHECK
→ CONFLICT CHECK
→ INDEX
→ VERIFY
→ PUBLISH

Status:
- DRAFT
- UNVERIFIED
- VERIFIED_INTERNAL
- APPROVED_OPERATIONAL
- APPROVED_PUBLIC
- BLOCKED
- SUPERSEDED
- EXPIRED

---

## 7. Privacy Operations

WXK als SaaS-Anbieter benötigt eine operative Datenschutzschicht.

Pflichtbausteine:
- data classification
- purpose registry
- retention policy
- access logging
- tenant export
- deletion/anonymization workflow
- legal hold / retention hold
- subprocessor registry
- data-location registry
- DPA/AVV references
- breach/incident workflow
- DSAR workflow soweit einschlägig
- consent/preference handling soweit erforderlich

---

## 8. Subprocessor Governance

Jeder externe Dienst erhält:
- vendor
- purpose
- data categories
- regions
- contract/DPA status
- criticality
- retention
- deletion method
- security status
- exit path

Neue Subprozessoren werden nicht still eingeführt, wenn Vertrag/Datenschutz eine Information oder Freigabe verlangt.

---

## 9. Sensitive Data Routing

AI/Connector Routing berücksichtigt Datenklasse.

Beispielklassen:
- PUBLIC
- INTERNAL
- CONFIDENTIAL
- PERSONAL
- FINANCIAL
- LEGAL
- SECRET

Provider/Connector Capability Registry definiert erlaubte Klassen.

Hermes darf eine Aufgabe nicht an einen Provider routen, dessen Sensitivity Policy die Datenklasse nicht erlaubt.

---

## 10. Data Minimization

Der Copilot übergibt extern nur die für die konkrete Capability benötigten Daten.

Beispiel:
Carrier braucht Lieferadresse und Packdaten, aber keine interne Marge.

LLM für Übersetzung braucht den zu übersetzenden Text, nicht die gesamte Kundendatenbank.

---

## 11. Knowledge Continuity

Desktop, Mobile, Hermes und produktive Agents greifen auf dieselbe kanonische Tenant Knowledge Layer zu.

Keine getrennten Wissensstände pro Gerät/Agent.

Caches sind ableitbar und invalidierbar.

---

## 12. Acceptance Gate

KNOWLEDGE_PRODUCTION_READY nur wenn:
- Tenant Isolation im Retrieval getestet
- Permission Filter getestet
- Superseded Source wird nicht als aktuell verwendet
- Prompt Injection Test bestanden
- Evidence/Citation Contract funktioniert
- Index Delete/Permission Propagation funktioniert
- sensitive Provider Routing getestet
- source freshness sichtbar
- conflict detection funktioniert
- Backup/Restore Knowledge + Metadata getestet

PRIVACY_OPERATIONS_READY nur wenn:
- Data Inventory vorhanden
- Retention Regeln versioniert
- Export getestet
- Delete/Anonymize getestet
- Subprocessor Registry vorhanden
- Incident Workflow vorhanden
- Zugriff auditierbar
- Tenant Offboarding vollständig
