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
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent
WXK_DIR = Path.home() / "OneDrive" / "Desktop" / "Steuererklärung" / "Steuervorbereitung" / "_SYSTEM"
VW_DIR = Path.home() / "OneDrive" / "Desktop" / "Verbundwerk_Deutschland_Vertriebsaufbau"


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
    finance_db = WXK_DIR / "finance_tax_ledger.sqlite"
    besitzer_file = WXK_DIR / "wxk_datenbesitzer_tenant.txt"

    finance_check = _sqlite_healthcheck(finance_db)
    core_check = _sqlite_healthcheck(core_db)

    n_transactions = None
    n_verified = None
    if finance_check["status"] == "GREEN":
        con = sqlite3.connect(finance_db)
        n_transactions = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        n_verified = con.execute("SELECT COUNT(*) FROM transactions WHERE review_status='VERIFIED'").fetchone()[0]
        con.close()

    tenant_isolation_ok = besitzer_file.exists()

    status = "GREEN"
    gruende = []
    if finance_check["status"] != "GREEN":
        status = "RED"
        gruende.append(f"finance_tax_ledger.sqlite: {finance_check['grund']}")
    if not tenant_isolation_ok:
        status = "RED" if status == "GREEN" else status
        gruende.append("Datenbesitzer-Tenant-Datei fehlt -- SEV-0-Zugriffsschutz nicht aktiv")

    return {
        "produkt": "WXK",
        "status": status,
        "gruende": gruende or ["Alle Checks bestanden"],
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

    status = "GREEN"
    gruende = []
    if vw_check["status"] != "GREEN":
        status = "RED"
        gruende.append(f"verbundwerk_core.sqlite: {vw_check['grund']}")
    if not tenant_isolation_ok:
        status = "RED" if status == "GREEN" else status
        gruende.append("Datenbesitzer-Tenant-Datei fehlt -- SEV-0-Zugriffsschutz nicht aktiv")

    return {
        "produkt": "Verbundwerk",
        "status": status,
        "gruende": gruende or ["Alle Checks bestanden"],
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


def root_control_center() -> dict:
    """Master-Prompt §34: 'Eduard soll mit einem Blick erkennen koennen:
    Laeuft alles oder muss ich etwas entscheiden?'"""
    wxk = wxk_status()
    vw = verbundwerk_status()

    gesamtstatus = "GREEN"
    if "RED" in (wxk["status"], vw["status"]):
        gesamtstatus = "RED"
    elif "DEGRADED" in (wxk["status"], vw["status"]):
        gesamtstatus = "DEGRADED"

    return {
        "erzeugt_am": datetime.now(timezone.utc).isoformat(),
        "gesamtstatus": gesamtstatus,
        "system": {"WXK": wxk, "Verbundwerk": vw},
        "muss_eduard_entscheiden": gesamtstatus != "GREEN",
    }


if __name__ == "__main__":
    rcc = root_control_center()
    print(json.dumps(rcc, ensure_ascii=False, indent=2))
    print(f"\n{'='*60}")
    print(f"GESAMTSTATUS: {rcc['gesamtstatus']}")
    print(f"Eduard muss entscheiden: {'JA' if rcc['muss_eduard_entscheiden'] else 'NEIN'}")
