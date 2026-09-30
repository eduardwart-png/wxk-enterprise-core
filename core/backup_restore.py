"""
Enterprise Core — Backup + Restore Validierung (WXK.TAX Spec §43/§44/PHASE 25).

Backup allein zaehlt nicht -- Restore muss real getestet werden. Prueft:
BACKUP -> ISOLATED RESTORE -> ROW COUNTS -> HASH CHECK -> TENANT-DATEN LESBAR.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent


def _resolve_core_db_path() -> Path:
    """Produktions-DB-Pfad ueber ENV konfigurierbar (WXK_CORE_DB_PATH),
    Default bleibt Eddys lokaler Pfad. Root-Cause-Fix (30.09.2026, CI-Fund):
    ein hartcodierter Nutzerpfad ohne Fallback liess dieses Gate auf jedem
    frischen Klon (CI, Zweitrechner) durchfallen -- verletzte die Golden-
    Master-Regel 'keine hardcoded Production Paths' (Execution Plan Phase
    1.3, Acceptance Matrix §3.1)."""
    override = os.environ.get("WXK_CORE_DB_PATH")
    if override:
        return Path(override)
    return Path.home() / "OneDrive" / "Desktop" / "Steuererklärung" / "Steuervorbereitung" / "_SYSTEM" / "wxk_core.sqlite"


CORE_DB_PATH = _resolve_core_db_path()


def _build_synthetic_test_db(dest_dir: Path) -> Path:
    """Fallback-Fixture, wenn keine echte Produktions-DB lokal existiert
    (CI, frischer Klon, Zweitrechner). Nutzt das ECHTE Schema/die echten
    Core-Funktionen (kein Mock) -- der Wiederherstellungsmechanismus wird
    damit weiterhin real gepruft, nur mit synthetischen statt echten Daten."""
    import sys
    sys.path.insert(0, str(CORE_DIR))
    from db import init_schema
    from auth import create_tenant, register_user
    from rbac import log_audit

    db_path = dest_dir / "synthetic_core_ci.sqlite"
    init_schema(db_path)
    tenant_id = create_tenant(db_path, "CI-Synthetic-Tenant")
    register_user(db_path, tenant_id, "ci-synthetic@example.invalid",
                  "synthetisches-ci-passwort-000", role="ADMIN")
    log_audit(db_path, tenant_id, actor="ci-synthetic",
              action="SYNTHETIC_SEED_FOR_RECOVERY_GATE", quelle="backup_restore_test")
    return db_path


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

    synthetic_dir = None
    quelle_db = CORE_DB_PATH
    if not quelle_db.exists():
        # Fallback statt Fehlschlag: kein lokaler Produktionszustand ist
        # keine Aussage ueber die Recovery-Mechanik. Root-Cause-Fund
        # 30.09.2026: dieser Test schlug auf jedem frischen Klon (CI,
        # Zweitrechner) fehl, weil er zwingend Eddys lokale Datei brauchte --
        # Mechanik selbst war nie kaputt, nur die Testbarkeit.
        synthetic_dir = tempfile.TemporaryDirectory()
        quelle_db = _build_synthetic_test_db(Path(synthetic_dir.name))
        ergebnis["db_quelle"] = (
            "SYNTHETISCH (keine lokale Produktions-DB gefunden -- CI/frischer "
            "Klon; Backup/Restore-Mechanik dennoch real mit echtem Schema "
            "gepruft, siehe _build_synthetic_test_db)"
        )
    else:
        ergebnis["db_quelle"] = str(quelle_db)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            # 1. BACKUP
            backup_path = tmp_path / "wxk_core_backup.sqlite"
            shutil.copy2(quelle_db, backup_path)
            ergebnis["schritte"]["backup_erstellt"] = backup_path.exists()

            # 2. ISOLATED RESTORE (separate Kopie, Original nie angefasst)
            restored_path = tmp_path / "wxk_core_restored.sqlite"
            shutil.copy2(backup_path, restored_path)
            ergebnis["schritte"]["restore_kopiert"] = restored_path.exists()

            # 3. HASH CHECK
            hash_original = _hash_file(quelle_db)
            hash_backup = _hash_file(backup_path)
            hash_restored = _hash_file(restored_path)
            ergebnis["hash_original"] = hash_original[:16]
            ergebnis["hash_backup"] = hash_backup[:16]
            ergebnis["hash_restored"] = hash_restored[:16]
            ergebnis["schritte"]["hashes_identisch"] = (hash_original == hash_backup == hash_restored)

            # 4. ROW COUNTS
            counts_original = _row_counts(quelle_db)
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

        # Produktions-/Quell-DB darf durch diesen Test NIE veraendert worden sein
        hash_original_nachher = _hash_file(quelle_db)
        ergebnis["produktions_db_unveraendert"] = (hash_original_nachher == hash_original)
    finally:
        if synthetic_dir is not None:
            synthetic_dir.cleanup()

    return ergebnis


if __name__ == "__main__":
    import json
    print(json.dumps(backup_restore_test(), indent=2, ensure_ascii=False))
