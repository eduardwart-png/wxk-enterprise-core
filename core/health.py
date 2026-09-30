"""
Enterprise Core — Health/Observability (Master-Prompt §34/§37/§38,
Continuation-Order §26 Root Control Center).

Aggregiert reale Zustandsdaten aus beiden Produkten (WXK + Verbundwerk) zu
einem einzigen GREEN/DEGRADED/RED-Status mit nachvollziehbarer Ursache --
KEIN erfundener Wert, jede Zahl kommt aus einer echten Quelle (DB-Abfrage,
Dateisystem-Check, Testlauf-Ergebnis).
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from health_interface import (
    ProductHealthAdapter,
    aggregate_status,
    get_registered_adapters,
    make_dependency,
    register_adapter,
)

CORE_DIR = Path(__file__).resolve().parent


def _resolve_wxk_dir() -> Path:
    """Root-Cause-Fix (30.09.2026): Pfad war hartcodiert auf einen Ordner
    ohne ENV-Override -- Golden Master Execution Plan Phase 1.3
    ('Configuration Abstraction: Local Path -> Config/Registry, keine
    Nutzerpfade als Produktionsannahme'). ENV-Override analog zu
    backup_restore.WXK_CORE_DB_PATH. Gilt weiterhin fuer wxk_core.sqlite
    und wxk_datenbesitzer_tenant.txt -- NICHT fuer finance_tax_ledger.sqlite,
    siehe _resolve_finance_ledger_path() (DEC-20260930-01 Migration weg von
    der falschen OneDrive-Pfad-Annahme)."""
    override = os.environ.get("WXK_SYSTEM_DIR")
    if override:
        return Path(override)
    return Path.home() / "OneDrive" / "Desktop" / "Steuererklärung" / "Steuervorbereitung" / "_SYSTEM"


def _resolve_finance_ledger_path() -> Path:
    """DEC-20260930-01 Migration (30.09.2026): finance_tax_ledger.sqlite lag
    zuvor unter WXK_DIR (~/OneDrive/Desktop/...), obwohl auf diesem Mac kein
    echter OneDrive-Client installiert ist -- der Pfad war nur ein
    zufaelliger lokaler Ordner gleichen Namens, keine echte Cloud-Anbindung.
    Eigener ENV-Override (FINANCE_TAX_LEDGER_PATH), damit die Finanz-DB
    unabhaengig vom WXK_SYSTEM_DIR-Pfad auf einem stabilen, nicht
    cloud-suggerierenden lokalen Systempfad liegen kann. Kanonischer
    Default: ~/Projekte-Mac/_DATA/WXK_TAX/finance_tax_ledger.sqlite."""
    override = os.environ.get("FINANCE_TAX_LEDGER_PATH")
    if override:
        return Path(override)
    return Path.home() / "Projekte-Mac" / "_DATA" / "WXK_TAX" / "finance_tax_ledger.sqlite"


def _resolve_vw_dir() -> Path:
    """Root-Cause-Fund (30.09.2026): dieser Pfad zeigte auf
    ~/OneDrive/Desktop/Verbundwerk_Deutschland_Vertriebsaufbau, das nach dem
    Umzug ins Projekte-Mac-Schema NIE existiert hat -- verbundwerk_status()
    meldete deshalb IMMER RED, unabhaengig vom echten Systemzustand (durch
    echten Lauf am 30.09.2026 bestaetigt: GESAMTSTATUS RED trotz 164/164
    gruener Tests im echten Projekt). ENV-Override + korrigierter Default."""
    override = os.environ.get("VERBUNDWERK_PROJECT_DIR")
    if override:
        return Path(override)
    return (Path.home() / "Projekte-Mac" /
            "OneDrive__Desktop__Verbundwerk_Deutschland_Vertriebsaufbau")


WXK_DIR = _resolve_wxk_dir()
FINANCE_DB_PATH = _resolve_finance_ledger_path()
VW_DIR = _resolve_vw_dir()


def _sqlite_healthcheck(db_path: Path) -> dict:
    if not db_path.exists():
        return {"status": "RED", "grund": f"Datei fehlt: {db_path}"}
    try:
        con = sqlite3.connect(db_path, timeout=2)
        con.execute("SELECT 1")
        con.close()
        return {"status": "GREEN", "grund": "Verbindung erfolgreich"}
    except Exception as e:
        return {"status": "RED", "grund": str(e)}


def wxk_status() -> dict:
    core_db = WXK_DIR / "wxk_core.sqlite"
    finance_db = FINANCE_DB_PATH

    finance_check = _sqlite_healthcheck(finance_db)
    core_check = _sqlite_healthcheck(core_db)

    n_transactions = None
    n_verified = None
    if finance_check["status"] == "GREEN":
        con = sqlite3.connect(finance_db)
        n_transactions = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        n_verified = con.execute("SELECT COUNT(*) FROM transactions WHERE review_status='VERIFIED'").fetchone()[0]
        con.close()

    # Root-Cause-Fix (30.09.2026, DEC-20260930-01 TEIL 5/6): vorher wurde
    # nur geprueft, ob eine separate Datei wxk_datenbesitzer_tenant.txt
    # existiert -- diese Datei wurde NIE erzeugt und war ein reiner
    # Datei-Existenz-Marker ohne eigenen Informationsgehalt (eine zweite,
    # redundante SSOT waere gewesen, sie kuenstlich anzulegen). Die echte
    # kanonische Tenant-Ownership-Information existiert bereits in
    # wxk_core.sqlite (Tabelle `tenants`, Status ACTIVE) -- der Check liest
    # jetzt DIREKT aus der echten Quelle, keine Dummy-Datei mehr noetig.
    tenant_isolation_ok = False
    tenant_name = None
    if core_check["status"] == "GREEN":
        con = sqlite3.connect(core_db)
        row = con.execute(
            "SELECT tenant_id, name FROM tenants WHERE status='ACTIVE' "
            "AND name LIKE '%Eduard%' LIMIT 1"
        ).fetchone()
        con.close()
        if row:
            tenant_isolation_ok = True
            tenant_name = row[1]

    # Strukturierte Dependency-Checks statt einer Freitext-Gründeliste
    # (Phase 1.4: "dependency checks"). Jede Abhängigkeit ist einzeln
    # unterscheidbar mit eigenem Status und Kritikalität.
    dependencies = [
        # Kritisch: ohne erreichbare Finanz-DB ist WXK unbrauchbar -> RED.
        make_dependency(
            "finance_db_erreichbar",
            finance_check["status"],
            f"finance_tax_ledger.sqlite: {finance_check['grund']}",
            kritisch=True,
        ),
        # Bewusste Entscheidung (Phase 1.4, kein stiller Verhaltenswechsel):
        # Die Tenant-Ownership ist ein Sicherheits-Kontrollpunkt, NICHT die
        # Datenverfügbarkeit. Fehlt der ACTIVE-Tenant-Eintrag, während die
        # Finanz-DB erreichbar ist, sind die Daten lesbar, aber ein
        # Kontrollpunkt fehlt -- das ist ehrlicher als hartes RED. Darum
        # kritisch=False: der Fall zieht das Produkt auf DEGRADED, nicht
        # auf RED. Nur wenn zusätzlich die kritische DB fällt, wird das
        # Gesamtprodukt RED.
        make_dependency(
            "tenant_isolation_datei",
            "GREEN" if tenant_isolation_ok else "RED",
            (f"Tenant-Ownership aktiv: {tenant_name}" if tenant_isolation_ok
             else "Kein ACTIVE-Tenant-Eintrag fuer Eduard in wxk_core.sqlite "
                  "gefunden -- Sicherheits-Kontrollpunkt nicht aktiv "
                  "(DB lesbar, daher DEGRADED statt RED)"),
            kritisch=False,
        ),
    ]
    status = aggregate_status(dependencies)
    gruende = [d["grund"] for d in dependencies if d["status"] != "GREEN"]

    return {
        "produkt": "WXK",
        "status": status,
        "gruende": gruende or ["Alle Checks bestanden"],
        "dependencies": dependencies,
        "transaktionen_gesamt": n_transactions,
        "transaktionen_verified": n_verified,
        "tenant_isolation_aktiv": tenant_isolation_ok,
        "finance_db": finance_check,
        "core_db": core_check,
    }


def verbundwerk_status() -> dict:
    vw_db = VW_DIR / "08_AUTOMATION" / "DB_MIGRATION" / "verbundwerk_core.sqlite"
    core_db = VW_DIR / "08_AUTOMATION" / "CRM_API" / "vw_core.sqlite"
    besitzer_file = VW_DIR / "08_AUTOMATION" / "CRM_API" / "vw_datenbesitzer_tenant.txt"
    event_ledger = VW_DIR / "08_AUTOMATION" / "EVENT_LEDGER" / "event_ledger.jsonl"

    vw_check = _sqlite_healthcheck(vw_db)
    n_kunden = None
    if vw_check["status"] == "GREEN":
        con = sqlite3.connect(vw_db)
        n_kunden = con.execute("SELECT COUNT(*) FROM kunden").fetchone()[0]
        con.close()

    n_events = 0
    if event_ledger.exists():
        n_events = len([l for l in event_ledger.read_text(encoding="utf-8").strip().splitlines() if l])

    tenant_isolation_ok = besitzer_file.exists()

    dependencies = [
        # Kritisch: ohne erreichbare Verbundwerk-DB ist das Produkt unbrauchbar.
        make_dependency(
            "verbundwerk_db_erreichbar",
            vw_check["status"],
            f"verbundwerk_core.sqlite: {vw_check['grund']}",
            kritisch=True,
        ),
        # Analog zu WXK: fehlender Sicherheits-Kontrollpunkt -> DEGRADED,
        # nicht RED, solange die DB erreichbar ist (bewusste Entscheidung).
        make_dependency(
            "tenant_isolation_datei",
            "GREEN" if tenant_isolation_ok else "RED",
            "Datenbesitzer-Tenant-Datei fehlt -- Sicherheits-Kontrollpunkt "
            "nicht aktiv (DB lesbar, daher DEGRADED statt RED)",
            kritisch=False,
        ),
    ]
    status = aggregate_status(dependencies)
    gruende = [d["grund"] for d in dependencies if d["status"] != "GREEN"]

    return {
        "produkt": "Verbundwerk",
        "status": status,
        "gruende": gruende or ["Alle Checks bestanden"],
        "dependencies": dependencies,
        "kunden_gesamt": n_kunden,
        "event_ledger_eintraege": n_events,
        "tenant_isolation_aktiv": tenant_isolation_ok,
        "verbundwerk_db": vw_check,
    }


def run_pytest_summary(test_dir: Path) -> dict:
    """Fuehrt die echte Testsuite aus und liefert das reale Ergebnis --
    kein gecachter/behaupteter Wert."""
    if not test_dir.exists():
        return {"status": "RED", "grund": "Testverzeichnis fehlt"}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_dir), "-q", "--tb=no"],
        capture_output=True, text=True, timeout=120,
    )
    letzte_zeile = [l for l in result.stdout.strip().splitlines() if l][-1] if result.stdout.strip() else ""
    return {
        "status": "GREEN" if result.returncode == 0 else "RED",
        "zusammenfassung": letzte_zeile,
        "exit_code": result.returncode,
    }


class WXKHealthAdapter(ProductHealthAdapter):
    """Konkreter Adapter für WXK. status() delegiert bewusst an die
    Modul-Funktion wxk_status(), damit bestehende Tests, die
    monkeypatch.setattr(health, 'wxk_status', ...) nutzen, weiter greifen und
    die abwärtskompatible Rückgabe-Struktur (transaktionen_gesamt etc.)
    erhalten bleibt."""

    product_name = "WXK"

    def check_dependencies(self) -> list[dict]:
        return wxk_status()["dependencies"]

    def status(self) -> dict:
        return wxk_status()


class VerbundwerkHealthAdapter(ProductHealthAdapter):
    """Konkreter Adapter für Verbundwerk -- analog zu WXKHealthAdapter."""

    product_name = "Verbundwerk"

    def check_dependencies(self) -> list[dict]:
        return verbundwerk_status()["dependencies"]

    def status(self) -> dict:
        return verbundwerk_status()


def root_control_center() -> dict:
    """Master-Prompt §34: 'Eduard soll mit einem Blick erkennen koennen:
    Laeuft alles oder muss ich etwas entscheiden?'

    Phase 1.4: Aggregation läuft jetzt über die Adapter-Registry statt über
    hartcodierte Produktaufrufe. Ein drittes Produkt, das sich per
    register_adapter(...) anmeldet, erscheint hier automatisch -- ohne dass
    diese Funktion geändert werden muss."""
    system: dict = {}
    einzelstatus: list[str] = []
    for adapter in get_registered_adapters():
        produkt_status = adapter.status()
        system[adapter.product_name] = produkt_status
        einzelstatus.append(produkt_status["status"])

    gesamtstatus = "GREEN"
    if "RED" in einzelstatus:
        gesamtstatus = "RED"
    elif "DEGRADED" in einzelstatus:
        gesamtstatus = "DEGRADED"

    return {
        "erzeugt_am": datetime.now(timezone.utc).isoformat(),
        "gesamtstatus": gesamtstatus,
        "system": system,
        "muss_eduard_entscheiden": gesamtstatus != "GREEN",
    }


# --- Automatische Adapter-Registrierung beim Modul-Import --------------------
# WXK und Verbundwerk melden sich selbst an; root_control_center() findet sie
# über die Registry. Ein drittes Produkt fügt hier NICHTS hinzu -- es ruft
# einfach register_adapter(...) mit seinem eigenen Adapter auf.
register_adapter(WXKHealthAdapter())
register_adapter(VerbundwerkHealthAdapter())


if __name__ == "__main__":
    rcc = root_control_center()
    print(json.dumps(rcc, ensure_ascii=False, indent=2))
    print(f"\n{'='*60}")
    print(f"GESAMTSTATUS: {rcc['gesamtstatus']}")
    print(f"Eduard muss entscheiden: {'JA' if rcc['muss_eduard_entscheiden'] else 'NEIN'}")
