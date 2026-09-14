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
    """BREAK-artiger Test: nicht-existente Datenbank muss RED liefern,
    nicht stillschweigend als OK durchgehen."""
    monkeypatch.setattr(health, "WXK_DIR", tmp_path / "nicht_existent")
    status = health.wxk_status()
    assert status["status"] == "RED"
    assert any("fehlt" in g.lower() for g in status["gruende"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
