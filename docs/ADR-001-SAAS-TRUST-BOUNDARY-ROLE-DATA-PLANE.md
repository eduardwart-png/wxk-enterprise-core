# ADR-001 — SaaS TRUST BOUNDARY, ROLE MODEL & DATA PLANE

**Status:** ACCEPTED — GOLDEN MASTER  
**Datum:** 2026-09-29  
**Betrifft:** wxk-enterprise-core, alle Vertical Packs und Tenants

---

## Kontext

Der heutige lokale Shared Core wurde ursprünglich als gemeinsame technische Basis für WXK und Verbundwerk entwickelt. Er verwendet SQLite, lokale Pfade und eine Rolle `OWNER`, die mandantenübergreifend zugreifen darf.

Für einen verkaufbaren WXK Business Copilot ist diese Semantik nicht ausreichend. Ein Kunden-Owner darf niemals automatisch Plattform-Root sein.

---

## Entscheidung 1 — Platform Identity und Tenant Identity werden getrennt

### Platform Rollen

- PLATFORM_ROOT
- PLATFORM_ADMIN
- PLATFORM_SUPPORT
- PLATFORM_AUDITOR

### Tenant Rollen

- TENANT_OWNER
- TENANT_ADMIN
- TENANT_REVIEWER
- TENANT_OPERATOR
- TENANT_FINANCE
- TENANT_SALES
- TENANT_VIEWER

Ein Tenant-Role-Token verleiht niemals mandantenübergreifende Rechte.

Cross-Tenant-Zugriff ist ausschließlich über explizite Platform-Rollen möglich.

---

## Entscheidung 2 — Platform Support ist nicht automatisch Datenzugriff

PLATFORM_SUPPORT erhält standardmäßig keinen Inhaltseinblick in Tenant-Geschäftsdaten.

Wenn Support-Zugriff notwendig ist:
- expliziter Case
- begrenzter Scope
- zeitlich begrenzter Grant
- Reason
- Actor
- Audit
- optional Tenant Approval je Vertrag/Plan
- automatisches Expiry

Break-glass Zugriff:
- ausschließlich für definierte Incidents
- besonders protokolliert
- nachträgliche Review Pflicht

---

## Entscheidung 3 — Aktuelle OWNER-Semantik ist Legacy Foundation

Die derzeitige `OWNER`-Rolle im Python/SQLite-Core wird für die SaaS-Zielarchitektur als **LEGACY_FOUNDATION_ONLY** klassifiziert.

Vor Multi-Tenant-Production muss:
- OWNER in Platform/Tenant Roles aufgeteilt werden
- jede API den effektiven Tenant-Kontext erzwingen
- Cross-Tenant Red-Team erneut bestanden werden

Kein externer Kunde darf die heutige mandantenübergreifende OWNER-Semantik erhalten.

---

## Entscheidung 4 — Persistence Target

Produktionsziel:
- PostgreSQL-basierte zentrale Data Plane
- tenant_id auf allen Shared-Tenant-Tabellen
- RLS + serverseitige Authorization
- dedizierte Data Plane optional für Enterprise

SQLite bleibt erlaubt für:
- lokale Entwicklung
- Unit/Integration Tests
- Offline Fixtures
- kontrollierte Migrationstools

SQLite ist nicht die produktive SaaS-System-of-Record-Zielarchitektur.

---

## Entscheidung 5 — Keine hart codierten lokalen Pfade

Produktionscode darf keine Nutzer-/Gerätepfade wie `C:/Users/.../OneDrive/...` oder `Path.home()/...` als kanonische Datenquelle voraussetzen.

Pflicht:
- Configuration/Environment
- Tenant Registry
- Connector Registry
- Storage IDs/URLs
- Secret References

Lokale Pfade dürfen nur Development-/Migration-Adapter sein.

---

## Entscheidung 6 — Auth Target

Für Cloud Production:
- zentraler Identity Provider / geeignete Auth-Schicht
- MFA für privilegierte Rollen
- Session Revocation
- Device/Session Visibility soweit erforderlich
- service identities getrennt
- scoped tokens
- keine secrets im Client

Die heutige lokale PBKDF2-Auth bleibt Foundation/Testbestand, nicht zwingend finales SaaS-Identity-System.

---

## Entscheidung 7 — Health Architecture

`core/health.py` darf langfristig nicht direkt lokale Verbundwerk-/WXK-Dateipfade kennen.

Ziel:
- Health Provider Interface
- Tenant/Product Adapter
- dependency probes
- normalized health events
- kein Cross-Product-Datenzugriff ohne Capability/Permission

---

## Konsequenz

Diese ADR supersediert ausschließlich die produktstrategische Interpretation älterer Kommentare, wonach SQLite und eine mandantenübergreifende OWNER-Rolle für kleine Installationen als Endzustand ausreichend wären.

Sie erklärt den heutigen Code nicht für falsch; sie klassifiziert ihn als Foundation, die vor SaaS-Production migriert werden muss.
