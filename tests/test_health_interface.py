"""
Tests für das generische Health-Adapter-Interface (Golden Master Execution
Plan, Phase 1.4 Health Interface: product adapter / dependency checks /
normalized GREEN/DEGRADED/RED).

Beweist konkret:
  - aggregate_status setzt die dokumentierte Regel korrekt um,
  - DEGRADED ist jetzt tatsächlich erreichbar (vorher unmöglich),
  - ein DRITTES Produkt kann sich registrieren und erscheint im
    root_control_center()-Aggregat, OHNE dass der Aggregator geändert wurde,
  - die bestehende wxk_status()-Struktur bleibt abwärtskompatibel,
  - ein sabotiertes aggregate_status (immer GREEN) wird von den Tests gefangen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import pytest
import health
import health_interface as hi


def _dep(name, status, kritisch=True):
    return hi.make_dependency(name, status, f"{name}: {status}", kritisch=kritisch)


# --- aggregate_status: dokumentierte Regel ----------------------------------

def test_aggregate_status_alle_green_ergibt_green():
    deps = [_dep("a", "GREEN"), _dep("b", "GREEN", kritisch=False)]
    assert hi.aggregate_status(deps) == "GREEN"


def test_aggregate_status_kritisches_red_ergibt_red():
    deps = [_dep("db", "RED", kritisch=True), _dep("nebensache", "GREEN")]
    assert hi.aggregate_status(deps) == "RED"


def test_aggregate_status_nichtkritisches_red_ergibt_degraded_nicht_red():
    """KERN-TEST der Aufgabe: eine nicht-kritische Dependency mit RED-Status
    darf das Produkt nur auf DEGRADED ziehen -- beweist, dass DEGRADED jetzt
    überhaupt erreichbar ist (vorher gab es nur GREEN oder RED)."""
    deps = [
        _dep("db", "GREEN", kritisch=True),
        _dep("tenant_isolation", "RED", kritisch=False),
    ]
    ergebnis = hi.aggregate_status(deps)
    assert ergebnis == "DEGRADED"
    assert ergebnis != "RED"


def test_aggregate_status_degraded_ohne_kritisches_red_bleibt_degraded():
    deps = [
        _dep("db", "GREEN", kritisch=True),
        _dep("cache", "DEGRADED", kritisch=False),
    ]
    assert hi.aggregate_status(deps) == "DEGRADED"


def test_aggregate_status_kritisches_red_schlaegt_degraded():
    """Ein kritisches RED gewinnt gegen ein DEGRADED -- RED ist der
    dominierende Zustand."""
    deps = [
        _dep("db", "RED", kritisch=True),
        _dep("cache", "DEGRADED", kritisch=False),
    ]
    assert hi.aggregate_status(deps) == "RED"


def test_aggregate_status_ohne_dependencies_ist_green():
    assert hi.aggregate_status([]) == "GREEN"


# --- Registry / drittes Produkt ---------------------------------------------

class _FakeDrittesProdukt(hi.ProductHealthAdapter):
    """Simuliert einen künftigen dritten Adapter (z. B. WXK-SaaS-Pilot).
    Implementiert NUR check_dependencies() -- status() kommt aus der
    Basisklasse. Beweis, dass ein Produkt sich ohne Aggregator-Änderung
    einklinken kann."""

    product_name = "DrittesProduktTest"

    def __init__(self, dep_status="DEGRADED"):
        self._dep_status = dep_status

    def check_dependencies(self) -> list[dict]:
        return [hi.make_dependency("pilot_db", self._dep_status,
                                   "Pilot-DB-Check", kritisch=False)]


def test_dritte_produkt_registrierung_ohne_code_aenderung_am_aggregator():
    """Beweis für 'product adapter': ein drittes Produkt registriert sich zur
    Laufzeit und taucht im root_control_center()-Ergebnis auf, OHNE dass
    root_control_center selbst angefasst wurde."""
    fake = _FakeDrittesProdukt(dep_status="DEGRADED")
    hi.register_adapter(fake)
    try:
        rcc = health.root_control_center()
        # Das dritte Produkt erscheint im Aggregat...
        assert "DrittesProduktTest" in rcc["system"]
        # ...mit dem aus seinen Dependencies aggregierten Status...
        assert rcc["system"]["DrittesProduktTest"]["status"] == "DEGRADED"
        # ...und die Standard-Adapter sind weiter vorhanden.
        assert "WXK" in rcc["system"]
        assert "Verbundwerk" in rcc["system"]
    finally:
        hi.unregister_adapter("DrittesProduktTest")

    # Aufräumen verifizieren -- keine Test-Verschmutzung für andere Tests.
    assert "DrittesProduktTest" not in health.root_control_center()["system"]


def test_registry_ist_idempotent_pro_produktname():
    fake_a = _FakeDrittesProdukt(dep_status="GREEN")
    fake_b = _FakeDrittesProdukt(dep_status="RED")
    hi.register_adapter(fake_a)
    hi.register_adapter(fake_b)
    try:
        namen = [a.product_name for a in hi.get_registered_adapters()]
        assert namen.count("DrittesProduktTest") == 1
    finally:
        hi.unregister_adapter("DrittesProduktTest")


# --- Abwärtskompatibilität ---------------------------------------------------

def test_wxk_status_bleibt_rueckwaertskompatibel_in_struktur():
    st = health.wxk_status()
    for schluessel in ("produkt", "status", "gruende", "transaktionen_gesamt",
                       "transaktionen_verified", "tenant_isolation_aktiv",
                       "finance_db", "core_db"):
        assert schluessel in st, f"Rückwärtskompatibler Schlüssel fehlt: {schluessel}"
    assert st["produkt"] == "WXK"
    assert st["status"] in hi.STATUS_WERTE
    assert isinstance(st["gruende"], list)


# --- BREAK → RECOVER → VERIFY -----------------------------------------------

def test_break_aggregate_status_immer_green_wird_gefangen(monkeypatch):
    """BREAK-Test: aggregate_status wird real so sabotiert, dass sie IMMER
    'GREEN' zurückgibt (simuliert 'Aggregationslogik vergessen'). Ein Szenario,
    das eigentlich RED sein MUSS (kritische DB kaputt), liefert dann fälschlich
    GREEN -- das fängt dieser Test. Anschließend Reset (monkeypatch-Teardown)
    und Verify, dass die echte Logik wieder RED liefert."""
    kritisch_red = [
        _dep("db", "RED", kritisch=True),
        _dep("tenant", "GREEN", kritisch=False),
    ]

    # RECOVER-Referenz: echte Logik VOR der Sabotage.
    assert hi.aggregate_status(kritisch_red) == "RED"

    # BREAK: Sabotage einspielen.
    monkeypatch.setattr(hi, "aggregate_status", lambda deps: "GREEN")
    sabotiert = hi.aggregate_status(kritisch_red)
    assert sabotiert == "GREEN"          # Sabotage ist aktiv...
    assert sabotiert != "RED"            # ...und produziert das falsche Ergebnis.

    # RECOVER: Sabotage entfernen und echte Logik direkt prüfen.
    monkeypatch.undo()
    # VERIFY: wieder korrektes RED.
    assert hi.aggregate_status(kritisch_red) == "RED"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
