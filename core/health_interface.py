"""
Enterprise Core — generisches Health-Adapter-Interface (Golden Master
Execution Plan, Phase 1 Shared Core Hardening, Punkt 1.4 Health Interface:
"product adapter / dependency checks / normalized GREEN/DEGRADED/RED").

Additiv zu core/health.py: dieses Modul liefert NUR das produktneutrale
Gerüst (Adapter-Basisklasse, Dependency-Aggregation, Registry). Die konkreten
produktspezifischen Adapter (WXK, Verbundwerk) leben weiter in health.py und
bauen auf diesem Interface auf.

Kernidee: ein DRITTES Produkt (z. B. ein künftiger WXK-SaaS-Pilot-Tenant)
kann sich über register_adapter(...) selbst anmelden und taucht dann im
root_control_center()-Aggregat auf, OHNE dass der Aggregator angefasst werden
muss. Vorher war jedes neue Produkt ein Code-Change am Aggregator.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

STATUS_WERTE = ("GREEN", "DEGRADED", "RED")


def make_dependency(
    name: str,
    status: str,
    grund: str,
    kritisch: bool = True,
) -> dict:
    """Baut ein normalisiertes Dependency-Dict.

    kritisch=True (Default) bewahrt das bisherige Verhalten: eine fehlgeschlagene
    kritische Dependency (RED) zieht das gesamte Produkt auf RED. Eine als
    kritisch=False markierte Dependency mit RED-Status zieht das Produkt nur auf
    DEGRADED -- der ehrlichere Zwischenzustand, wenn ein Kontrollpunkt fehlt,
    das Produkt aber grundsätzlich benutzbar bleibt.
    """
    if status not in STATUS_WERTE:
        raise ValueError(
            f"Ungültiger Dependency-Status {status!r}, erlaubt: {STATUS_WERTE}"
        )
    return {"name": name, "status": status, "grund": grund, "kritisch": kritisch}


def aggregate_status(dependencies: list[dict]) -> str:
    """Berechnet EINEN normalisierten Produktstatus aus einer Liste von
    Dependency-Status. Dokumentierte, bewusst einfache Regel:

      - alle GREEN                                            -> GREEN
      - mindestens 1 RED bei einer kritischen Dependency      -> RED
      - mindestens 1 DEGRADED ODER 1 nicht-kritisches RED,
        aber KEINE kritische RED                              -> DEGRADED

    Eine nicht-kritische Dependency mit RED-Status darf ein Produkt also nur
    auf DEGRADED, niemals auf hartes RED ziehen. Ohne Dependencies gilt GREEN
    (nichts zu prüfen = nichts kaputt).
    """
    if not dependencies:
        return "GREEN"

    hat_kritisches_red = any(
        d["status"] == "RED" and d.get("kritisch", True) for d in dependencies
    )
    if hat_kritisches_red:
        return "RED"

    hat_degraded = any(
        d["status"] == "DEGRADED"
        or (d["status"] == "RED" and not d.get("kritisch", True))
        for d in dependencies
    )
    if hat_degraded:
        return "DEGRADED"

    return "GREEN"


class ProductHealthAdapter(ABC):
    """Abstrakte Basisklasse für produktspezifische Health-Adapter.

    Ein Adapter muss nur zwei Dinge liefern:
      - product_name: der Schlüssel, unter dem das Produkt im
        root_control_center()-Aggregat erscheint.
      - check_dependencies(): die Liste der geprüften Abhängigkeiten (jede über
        make_dependency() bzw. gleiches Schema).

    status() ist bereits fertig implementiert und aggregiert generisch über
    aggregate_status(). Produkte mit zusätzlichen Kennzahlen (WXK, Verbundwerk)
    dürfen status() überschreiben, um ihr reichhaltiges, abwärtskompatibles
    Rückgabe-Dict zu liefern -- müssen aber intern check_dependencies() +
    aggregate_status() nutzen.
    """

    product_name: str = "UNBENANNT"

    @abstractmethod
    def check_dependencies(self) -> list[dict]:
        raise NotImplementedError

    def status(self) -> dict:
        deps = self.check_dependencies()
        gesamt = aggregate_status(deps)
        gruende = [d["grund"] for d in deps if d["status"] != "GREEN"]
        return {
            "produkt": self.product_name,
            "status": gesamt,
            "gruende": gruende or ["Alle Checks bestanden"],
            "dependencies": deps,
        }


# --- Modul-Level-Registry (bewusst minimal, kein Overengineering) ------------

_REGISTRY: list[ProductHealthAdapter] = []


def register_adapter(adapter: ProductHealthAdapter) -> None:
    """Registriert einen Adapter. Idempotent pro product_name: erneute
    Registrierung mit gleichem Namen ersetzt den bestehenden Eintrag (verhindert
    Doppel-Einträge bei Re-Import) statt zu duplizieren."""
    for i, vorhanden in enumerate(_REGISTRY):
        if vorhanden.product_name == adapter.product_name:
            _REGISTRY[i] = adapter
            return
    _REGISTRY.append(adapter)


def unregister_adapter(product_name: str) -> None:
    """Entfernt einen Adapter wieder (v. a. für saubere Laufzeit-Tests, die
    testweise ein drittes Produkt registrieren)."""
    _REGISTRY[:] = [a for a in _REGISTRY if a.product_name != product_name]


def get_registered_adapters() -> list[ProductHealthAdapter]:
    """Liefert eine Kopie der registrierten Adapter (Aufrufer darf iterieren,
    ohne die Registry versehentlich zu mutieren)."""
    return list(_REGISTRY)
