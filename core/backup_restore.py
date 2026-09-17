"""
Enterprise Core — Backup + Restore Validierung (WXK.TAX Spec §43/§44/PHASE 25).

Backup allein zaehlt nicht -- Restore muss real getestet werden. Prueft:
BACKUP -> ISOLATED RESTORE -> ROW COUNTS -> HASH CHECK -> TENANT-DATEN LESBAR.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import tempfile
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent
CORE_DB_PATH = Path.home() / "OneDrive" / "Desktop" / "Steuererklärung" / "Steuervorbereitung" / "_SYSTEM" / "wxk_core.sqlite"


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _row_counts(db_path: Path) -> dict:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
    tables = [r[0] for r in cur.fetchall()]
    counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cur.fetchone()[0]
    con.close()
    return counts


def backup_restore_test() -> dict:
    ergebnis = {"schritte": {}}

    if not CORE_DB_PATH.exists():
        ergebnis["GESAMTERGEBNIS"] = "FEHLGESCHLAGEN"
        ergebnis["grund"] = f"Core-DB nicht gefunden: {CORE_DB_PATH}"
        return ergebnis

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1. BACKUP
        backup_path = tmp_path / "wxk_core_backup.sqlite"
        shutil.copy2(CORE_DB_PATH, backup_path)
        ergebnis["schritte"]["backup_erstellt"] = backup_path.exists()

        # 2. ISOLATED RESTORE (separate Kopie, Original nie angefasst)
        restored_path = tmp_path / "wxk_core_restored.sqlite"
        shutil.copy2(backup_path, restored_path)
        ergebnis["schritte"]["restore_kopiert"] = restored_path.exists()

        # 3. HASH CHECK
        hash_original = _hash_file(CORE_DB_PATH)
        hash_backup = _hash_file(backup_path)
        hash_restored = _hash_file(restored_path)
        ergebnis["hash_original"] = hash_original[:16]
        ergebnis["hash_backup"] = hash_backup[:16]
        ergebnis["hash_restored"] = hash_restored[:16]
        ergebnis["schritte"]["hashes_identisch"] = (hash_original == hash_backup == hash_restored)

        # 4. ROW COUNTS
        counts_original = _row_counts(CORE_DB_PATH)
        counts_restored = _row_counts(restored_path)
        ergebnis["row_counts_original"] = counts_original
        ergebnis["row_counts_restored"] = counts_restored
        ergebnis["schritte"]["row_counts_identisch"] = (counts_original == counts_restored)

        # 5. TENANT-DATEN LESBAR (funktionaler Nachweis, nicht nur Byte-Vergleich)
        con = sqlite3.connect(restored_path)
        cur = con.cursor()
        cur.execute("SELECT COUNT(DISTINCT tenant_id) FROM tenants")
        n_tenants = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM audit_log")
        n_audit = cur.fetchone()[0]
        con.close()
        ergebnis["tenants_lesbar"] = n_tenants
        ergebnis["audit_log_lesbar"] = n_audit
        ergebnis["schritte"]["tenant_daten_lesbar"] = n_tenants > 0

        alle_schritte_ok = all(ergebnis["schritte"].values())
        ergebnis["GESAMTERGEBNIS"] = "RESTORE_ERFOLGREICH" if alle_schritte_ok else "FEHLGESCHLAGEN"

    # Produktions-DB darf durch diesen Test NIE veraendert worden sein
    hash_original_nachher = _hash_file(CORE_DB_PATH)
    ergebnis["produktions_db_unveraendert"] = (hash_original_nachher == hash_original)

    return ergebnis


if __name__ == "__main__":
    import json
    print(json.dumps(backup_restore_test(), indent=2, ensure_ascii=False))
