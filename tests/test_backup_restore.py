"""Tests fuer backup_restore.py -- RECOVERY GATE (WXK.TAX Spec §44/PHASE 25)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
import backup_restore  # noqa: E402


def test_backup_restore_vollstaendig_erfolgreich():
    ergebnis = backup_restore.backup_restore_test()
    assert ergebnis["GESAMTERGEBNIS"] == "RESTORE_ERFOLGREICH", ergebnis
    assert ergebnis["produktions_db_unveraendert"] is True


def test_hash_original_backup_restored_identisch():
    ergebnis = backup_restore.backup_restore_test()
    assert ergebnis["hash_original"] == ergebnis["hash_backup"] == ergebnis["hash_restored"]


def test_row_counts_identisch_nach_restore():
    ergebnis = backup_restore.backup_restore_test()
    assert ergebnis["row_counts_original"] == ergebnis["row_counts_restored"]


def test_tenant_daten_nach_restore_funktional_lesbar():
    ergebnis = backup_restore.backup_restore_test()
    assert ergebnis["tenants_lesbar"] > 0
    assert ergebnis["audit_log_lesbar"] > 0


def test_produktions_db_bleibt_waehrend_gesamtem_testlauf_unveraendert():
    """Prueft die reale Quelle (Produktions-DB ODER synthetischer CI-Fallback,
    siehe backup_restore._resolve_core_db_path), nicht blind CORE_DB_PATH --
    sonst schlaegt dieser Test auf jedem frischen Klon ohne lokale Produktions-
    DB fehl, obwohl die eigentliche Invariante (Quelle unveraendert) haelt."""
    ergebnis_vorher = backup_restore.backup_restore_test()
    quelle = ergebnis_vorher["db_quelle"]
    if quelle.startswith("SYNTHETISCH"):
        # Synthetische Quelle wird pro Aufruf frisch erzeugt und wieder
        # aufgeraeumt -- die Invariante ist stattdessen direkt am
        # zurueckgegebenen Flag pruefbar.
        assert ergebnis_vorher["produktions_db_unveraendert"] is True
        ergebnis_nochmal = backup_restore.backup_restore_test()
        assert ergebnis_nochmal["produktions_db_unveraendert"] is True
        return
    hash_vorher = backup_restore._hash_file(Path(quelle))
    backup_restore.backup_restore_test()
    backup_restore.backup_restore_test()  # zweimal, um Seiteneffekte auszuschliessen
    hash_nachher = backup_restore._hash_file(Path(quelle))
    assert hash_vorher == hash_nachher
