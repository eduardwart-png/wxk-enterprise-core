"""
Tests fuer vier getrennte Statuswerte (Master-Final-Closure-Order §5).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import pytest
import vier_status_werte as vsw


def test_vier_statuswerte_getrennt_vorhanden():
    v = vsw.vollstatus()
    for produkt in ("WXK", "Verbundwerk"):
        for feld in ("SYSTEM_HEALTH", "PRODUCT_READINESS", "DATA_INTEGRITY", "PRODUCTION_RELEASE"):
            assert feld in v[produkt], f"{produkt} fehlt Statuswert {feld}"


def test_production_release_nie_automatisch_approved():
    """Master-Order §45: kein automatisches Produktivdeployment ohne
    explizite Freigabe -- struktureller Test, der das Verhalten fixiert."""
    for produkt in ("WXK", "Verbundwerk"):
        status = vsw.production_release_status(produkt)
        assert status["status"] == "NOT_APPROVED"


def test_system_health_gruen_bedeutet_nicht_produkt_fertig():
    """Kernaussage aus §5: 'Ein gruener Server bedeutet niemals automatisch
    ein fertiges Produkt.'"""
    v = vsw.vollstatus()
    for produkt in ("WXK", "Verbundwerk"):
        p = v[produkt]
        if p["SYSTEM_HEALTH"] == "GREEN":
            # SYSTEM_HEALTH gruen darf NICHT automatisch PRODUCT_READINESS=100% bedeuten
            assert p["PRODUCT_READINESS"]["prozent"] < 100


def test_product_readiness_nur_aus_echter_quelle():
    r = vsw.product_readiness("WXK")
    assert "quelle" in r
    assert isinstance(r["prozent"], int)
    assert 0 <= r["prozent"] <= 100


def test_data_integrity_wxk_liefert_echte_db_zahlen(monkeypatch):
    """BREAK-artiger Test: bei fehlender DB muss RED zurueckkommen, nicht
    stillschweigend ein optimistischer Default."""
    monkeypatch.setattr(vsw, "WXK_DB", Path("/nicht/existent.sqlite"))
    r = vsw.data_integrity_wxk()
    assert r["ampel"] == "RED"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
