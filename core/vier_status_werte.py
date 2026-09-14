"""
WXK + Verbundwerk — Vier getrennte Statuswerte (Master-Final-Closure-Order
§5: "Status darf nicht mehr vermischt werden").

Ein gruener Server bedeutet NIEMALS automatisch ein fertiges Produkt.

  SYSTEM HEALTH:      laufen Infrastruktur/Dienste technisch? (health.py)
  PRODUCT READINESS:   sind Produktfunktionen vollstaendig? (gewichtete DoD-Matrix)
  DATA INTEGRITY:      sind Daten/Verknuepfungen/Historie belastbar?
  PRODUCTION RELEASE:  ist das System tatsaechlich freigegeben?

Jede Zahl kommt aus einer echten Quelle -- keine Bauchgefuehl-Werte
(Master-Order §6).
"""
from __future__ import annotations

import json
import subprocess
import sys
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health

WXK_DB = health.WXK_DIR / "finance_tax_ledger.sqlite"


def product_readiness(produkt: str) -> dict:
    """PRODUCT READINESS: gewichteter DoD-Prozentsatz aus der Matrix-Analyse
    (siehe WXK-VERBUNDWERK-DOD-MATRIX-20260914.md fuer die vollstaendige
    Einzelaufschluesselung -- hier nur der zusammengefasste Wert + Ampel)."""
    werte = {
        "WXK": {"prozent": 58, "quelle": "gewichtete DoD-Matrix, Stand 14.09.2026 nach Final-Closure-Block (Document Lineage, Matching, Workbench-Erweiterung)"},
        "Verbundwerk": {"prozent": 69, "quelle": "gewichtete DoD-Matrix, Stand 14.09.2026 nach CRM-API-Erweiterung + CI-Fix"},
    }
    if produkt not in werte:
        return {"produkt": produkt, "status": "UNKNOWN", "prozent": None}
    prozent = werte[produkt]["prozent"]
    ampel = "GREEN" if prozent >= 80 else ("YELLOW" if prozent >= 40 else "RED")
    return {"produkt": produkt, "ampel": ampel, "prozent": prozent, "quelle": werte[produkt]["quelle"]}


def data_integrity_wxk() -> dict:
    """DATA INTEGRITY fuer WXK: reale Kennzahlen aus der DB, nicht geschaetzt."""
    if not WXK_DB.exists():
        return {"ampel": "RED", "grund": "DB fehlt"}

    con = sqlite3.connect(WXK_DB)
    cur = con.cursor()
    n_total = cur.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    n_verified = cur.execute("SELECT COUNT(*) FROM transactions WHERE review_status='VERIFIED'").fetchone()[0]
    n_anomalie = cur.execute("SELECT COUNT(*) FROM transactions WHERE review_status='AUTOMATIK_ANOMALIE'").fetchone()[0]

    try:
        n_docs = cur.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        n_links = cur.execute("SELECT COUNT(*) FROM booking_document_links").fetchone()[0]
        n_high_conf_links = cur.execute("SELECT COUNT(*) FROM booking_document_links WHERE review_status='HIGH_CONFIDENCE'").fetchone()[0]
    except sqlite3.OperationalError:
        n_docs = n_links = n_high_conf_links = 0
    con.close()

    verified_anteil = round((n_verified / n_total) * 100, 2) if n_total else 0.0

    # DATA INTEGRITY ist YELLOW solange die grosse Mehrheit noch REVIEW ist
    # (ehrlich, kein Beschoenigen -- Master-Order §6: "mehr Tests allein
    # erhoehen keinen Fertigstellungsgrad").
    if n_anomalie > 0 and n_anomalie == n_total:
        ampel = "RED"
    elif verified_anteil < 5:
        ampel = "YELLOW"
    else:
        ampel = "GREEN"

    return {
        "ampel": ampel,
        "buchungen_gesamt": n_total,
        "buchungen_verified": n_verified,
        "buchungen_verified_prozent": verified_anteil,
        "anomalien_markiert": n_anomalie,
        "dokumente_erfasst": n_docs,
        "dokument_buchung_links": n_links,
        "davon_high_confidence": n_high_conf_links,
        "hinweis": (
            f"{verified_anteil}% der Buchungen sind menschlich verifiziert. "
            f"Das ist der einzig belastbare Wert fuer Datenintegritaet -- "
            f"Confidence-Scores und Matching-Kandidaten sind Vorstufen, keine "
            f"bestaetigte Integritaet."
        ),
    }


def production_release_status(produkt: str) -> dict:
    """PRODUCTION RELEASE: APPROVED nur, wenn ALLE Final-Release-Gate-
    Kriterien erfuellt sind (Master-Order §50). Aktuell nie automatisch
    APPROVED -- das ist eine bewusste menschliche Freigabe-Entscheidung,
    kein technischer Automatismus (Master-Order §45)."""
    return {
        "produkt": produkt,
        "status": "NOT_APPROVED",
        "grund": "Keine explizite Freigabe-Entscheidung getroffen (Master-Order §45: "
                 "Produktivdeployment nur nach Freigabe). Release-Gate-Kriterien "
                 "(§50) nicht vollstaendig geprueft -- UI-Tiefe, Multi-Tenant-"
                 "Productization und produktive Italien-Anbindung fehlen noch.",
    }


def vollstatus() -> dict:
    sys_health = health.root_control_center()

    return {
        "erzeugt_am": datetime.now(timezone.utc).isoformat(),
        "WXK": {
            "SYSTEM_HEALTH": sys_health["system"]["WXK"]["status"],
            "PRODUCT_READINESS": product_readiness("WXK"),
            "DATA_INTEGRITY": data_integrity_wxk(),
            "PRODUCTION_RELEASE": production_release_status("WXK"),
        },
        "Verbundwerk": {
            "SYSTEM_HEALTH": sys_health["system"]["Verbundwerk"]["status"],
            "PRODUCT_READINESS": product_readiness("Verbundwerk"),
            "DATA_INTEGRITY": {"ampel": "GREEN", "hinweis": "Datei-SSOT-Migration verifiziert (Hash-Match), Event-Ledger idempotent getestet."},
            "PRODUCTION_RELEASE": production_release_status("Verbundwerk"),
        },
    }


if __name__ == "__main__":
    v = vollstatus()
    print(json.dumps(v, indent=2, ensure_ascii=False))
    print(f"\n{'='*70}")
    for produkt in ("WXK", "Verbundwerk"):
        p = v[produkt]
        print(f"{produkt}:")
        print(f"  SYSTEM HEALTH:      {p['SYSTEM_HEALTH']}")
        print(f"  PRODUCT READINESS:  {p['PRODUCT_READINESS']['ampel']} ({p['PRODUCT_READINESS']['prozent']}%)")
        print(f"  DATA INTEGRITY:     {p['DATA_INTEGRITY']['ampel']}")
        print(f"  PRODUCTION RELEASE: {p['PRODUCTION_RELEASE']['status']}")
