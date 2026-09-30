# WXK Business Copilot

**Produktname:** WXK Business Copilot  
**Repo-Rolle:** gemeinsamer technischer Kern (Shared Core)  
**Erste Referenzimplementierung:** Verbundwerk Deutschland  
**Orchestrierung:** Hermes

Dieses Repository ist **kein separates Produkt mit dem Namen „Golden Master“**.

„Golden Master“ bezeichnet intern ausschließlich den Freigabestatus der aktuell verbindlichen Architektur.

## Für die tägliche Orientierung

Wenn du wissen willst, **was dieses Repo ist**:

> WXK Business Copilot — gemeinsamer Kern für automatisierte Geschäftsprozesse.

Wenn du wissen willst, **wofür Verbundwerk es benutzt**:

> Verbundwerk Deutschland nutzt den WXK Business Copilot als operative Softwarebasis für Angebot, Auftrag, Preis/Marge, Logistik, Bestand, Lieferantenbestellung, Rechnung, Zahlung, Reklamation und Lernen.

## Startpunkte

- Produkt-/Architekturübersicht: `docs/WXK_BUSINESS_COPILOT_MASTER_BLUEPRINT_LIMIT.md`
- Verbundwerk-Umsetzung: `docs/VERBUNDWERK_REFERENCE_IMPLEMENTATION_BLUEPRINT.md`
- Harte Abnahmekriterien: `docs/WXK_BUSINESS_COPILOT_LIMIT_ACCEPTANCE_MATRIX.md`
- Umsetzungsreihenfolge: `docs/WXK_BUSINESS_COPILOT_GOLDEN_MASTER_EXECUTION_PLAN.md`
- Interner Architekturstatus: `docs/WXK_BUSINESS_COPILOT_GOLDEN_MASTER_MANIFEST.md`

## Konfigurierbare Datenpfade (ENV-Overrides, `core/health.py`/`core/backup_restore.py`)

Kein Datenpfad ist hartcodiert produktionsannahmefähig — jeder hat einen
ENV-Override und einen lokalen, nicht-cloud-suggerierenden Default:

| ENV-Variable | Zweck | Default |
|---|---|---|
| `WXK_SYSTEM_DIR` | Ordner für `wxk_core.sqlite` (Tenant/Auth/RBAC) | `~/OneDrive/Desktop/Steuererklärung/Steuervorbereitung/_SYSTEM` |
| `FINANCE_TAX_LEDGER_PATH` | vollständiger Pfad zur produktiven Finanz-DB | `~/Projekte-Mac/_DATA/WXK_TAX/finance_tax_ledger.sqlite` (seit `DEC-20260930-01`, 30.09.2026 — vorher fälschlich unter `WXK_SYSTEM_DIR`, obwohl kein echter OneDrive-Client installiert ist) |
| `WXK_CORE_DB_PATH` | Backup/Restore-Zielpfad für `wxk_core.sqlite` | analog `WXK_SYSTEM_DIR` |
| `VERBUNDWERK_PROJECT_DIR` | Verbundwerk-Projektwurzel | `~/Projekte-Mac/OneDrive__Desktop__Verbundwerk_Deutschland_Vertriebsaufbau` |

## Namensregel

Sichtbare Bezeichnungen für Menschen, Vertrieb und Projektarbeit:

- **WXK Business Copilot**
- **Verbundwerk Copilot** = Verbundwerk-Implementierung

Interne Statusbegriffe wie `GOLDEN MASTER`, `PRODUCTION_READY`, `FOUNDATION` oder `VERIFIED` sind Zustände, keine Produktnamen.

## Architekturregel

- ein Shared Core
- keine Kunden-Forks
- Branchenlogik über Vertical Packs
- Kundenspezifika über Tenant Configuration
- Hermes orchestriert
- deterministische Engines führen Geld-, Preis-, Steuer-, Bestands-, Rechnungs- und Logikentscheidungen aus

## Status

**Architektur:** freigegeben  
**Umsetzungsplan:** freigegeben  
**Gesamtes Produktivsystem:** noch im Aufbau

Keine Dokumentation in diesem Repo darf aus dem Architekturstatus ableiten, dass ein noch nicht gebautes Modul bereits produktiv ist.
