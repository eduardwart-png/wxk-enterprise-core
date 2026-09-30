"""
Tests fuer Root Control Center / Health (Master-Order §26).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import pytest
import health


def test_root_control_center_liefert_struktur():
    rcc = health.root_control_center()
    assert rcc["gesamtstatus"] in ("GREEN", "DEGRADED", "RED")
    assert "WXK" in rcc["system"]
    assert "Verbundwerk" in rcc["system"]
    assert isinstance(rcc["muss_eduard_entscheiden"], bool)


def test_gesamtstatus_ist_rot_wenn_ein_produkt_rot(monkeypatch):
    """Struktureller Test: wenn EIN Produkt RED meldet, muss der
    Gesamtstatus RED sein, nie stillschweigend uebertuencht werden."""
    monkeypatch.setattr(health, "wxk_status", lambda: {"status": "RED", "gruende": ["Test-RED"]})
    monkeypatch.setattr(health, "verbundwerk_status", lambda: {"status": "GREEN", "gruende": []})
    rcc = health.root_control_center()
    assert rcc["gesamtstatus"] == "RED"
    assert rcc["muss_eduard_entscheiden"] is True


def test_gesamtstatus_gruen_nur_wenn_beide_gruen(monkeypatch):
    monkeypatch.setattr(health, "wxk_status", lambda: {"status": "GREEN", "gruende": []})
    monkeypatch.setattr(health, "verbundwerk_status", lambda: {"status": "GREEN", "gruende": []})
    rcc = health.root_control_center()
    assert rcc["gesamtstatus"] == "GREEN"
    assert rcc["muss_eduard_entscheiden"] is False


def test_fehlende_db_wird_als_red_erkannt(tmp_path, monkeypatch):
    """BREAK-artiger Test: nicht-existente Finanz-Datenbank muss RED liefern,
    nicht stillschweigend als OK durchgehen. Seit DEC-20260930-01 (30.09.2026)
    ist FINANCE_DB_PATH unabhaengig von WXK_DIR (Entkopplung vom frueheren
    OneDrive-Scheinpfad) -- der Test patcht deshalb gezielt FINANCE_DB_PATH,
    nicht mehr WXK_DIR."""
    monkeypatch.setattr(health, "FINANCE_DB_PATH", tmp_path / "nicht_existent" / "finance_tax_ledger.sqlite")
    status = health.wxk_status()
    assert status["status"] == "RED"
    assert any("fehlt" in g.lower() for g in status["gruende"])


def test_tenant_ownership_liest_aus_wxk_core_nicht_aus_dummy_datei(tmp_path, monkeypatch):
    """Root-Cause-Fix (DEC-20260930-01 TEIL 5/6, 30.09.2026): der
    Tenant-Kontrollpunkt darf NICHT von einer separaten, nie erzeugten
    Datei (wxk_datenbesitzer_tenant.txt) abhaengen -- das waere entweder
    dauerhaft RED oder eine kuenstliche Dummy-Datei (verboten). Stattdessen
    liest er direkt aus der echten SSOT (wxk_core.sqlite Tabelle `tenants`).
    Test baut eine isolierte core_db ohne ACTIVE-Eduard-Tenant und prueft,
    dass der Kontrollpunkt dann korrekt RED meldet (DEGRADED, nicht GREEN)."""
    import sqlite3
    core_db = tmp_path / "wxk_core.sqlite"
    con = sqlite3.connect(core_db)
    con.execute("CREATE TABLE tenants (tenant_id TEXT, name TEXT, status TEXT)")
    con.execute("INSERT INTO tenants VALUES ('T-fremd', 'Fremdmandant GmbH', 'ACTIVE')")
    con.commit()
    con.close()

    finance_db = tmp_path / "finance_tax_ledger.sqlite"
    con2 = sqlite3.connect(finance_db)
    con2.execute("CREATE TABLE transactions (review_status TEXT)")
    con2.commit()
    con2.close()

    monkeypatch.setattr(health, "WXK_DIR", tmp_path)
    monkeypatch.setattr(health, "FINANCE_DB_PATH", finance_db)
    status = health.wxk_status()
    assert status["dependencies"][1]["status"] == "RED"
    assert status["status"] == "DEGRADED"
    assert status["tenant_isolation_aktiv"] is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
