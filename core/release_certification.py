"""Enterprise Core — Release Certification Pipeline (CRITICAL LESSON
INDIVIDUAL_FILE_CERTIFICATION_IS_A_SEPARATE_GATE, Eddy-Direktive 18.09.2026).

GOLDEN_CASE_001 bewies: ein Release kann `MANIFEST = FOLDER = ZIP` (Gate A,
STRUCTURAL/TECHNICAL PARITY) technisch vollstaendig bestehen und trotzdem
407 physische Duplikate, 18 Scope-Verstoesse und 1 fachlich falsch
einsortiertes Dokument enthalten. Gate A beweist nur: "ist technisch exakt
ausgeliefert worden, was das Manifest erlaubt?" -- es beweist NICHT, dass
diese Erlaubnis selbst fachlich richtig war.

PARITY PROVES CONSISTENCY. CERTIFICATION PROVES CORRECTNESS. BOTH ARE
REQUIRED.

Dieses Modul macht die Trennung zu einer TECHNISCHEN Kontrolle, nicht nur
einer dokumentierten Konvention: `FinalReleaseVerification.final_verified`
ist eine berechnete Property, die niemals True werden kann, ohne dass ein
vollstaendiger `IndividualFileCertificationReport` mit `all_certified=True`
vorliegt -- es gibt keinen Codepfad, der Gate B uebersprint.

INDEPENDENCE RULE: der Zertifizierungsprozess liest den PHYSISCHEN Bestand
unabhaengig neu (os.walk auf der Platte, eigener Content-Hash), er
wiederholt NIEMALS nur die Entscheidung des Package Builders/Manifests.
"""
from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


def _lp(p: str) -> str:
    p = os.path.abspath(p)
    prefix = "\\\\?\\"
    if os.name == "nt" and not p.startswith(prefix):
        return prefix + p
    return p


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(_lp(path), "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass
class PerFileCertification:
    """Pflichtpruefung pro Datei (Order 'PFLICHTPRUEFUNG PRO DATEI') -- alle
    10 Felder muessen TRUE sein, bevor final_status CERTIFIED_CORRECT wird.
    Nicht ausreichend: nur MANIFEST_VALID, nur HASH_VALID, nur FOLDER_ZIP_
    PARITY, nur PRIVACY_SCAN_PASS (Order 'HARD RULE')."""
    rel_path: str
    ownership_valid: bool
    tax_relevance_valid: bool
    tax_entity_valid: bool
    tax_year_valid: bool
    document_type_valid: bool
    folder_placement_valid: bool
    scope_valid: bool
    duplicate_status_valid: bool
    sensitivity_valid: bool
    manifest_valid: bool
    actual_folder: str = ""
    expected_folder: str = ""
    failed_checks: tuple[str, ...] = field(default_factory=tuple)

    @property
    def certified_correct(self) -> bool:
        return (
            self.ownership_valid and self.tax_relevance_valid and
            self.tax_entity_valid and self.tax_year_valid and
            self.document_type_valid and self.folder_placement_valid and
            self.scope_valid and self.duplicate_status_valid and
            self.sensitivity_valid and self.manifest_valid
        )

    @property
    def final_status(self) -> str:
        return "CERTIFIED_CORRECT" if self.certified_correct else (
            self.failed_checks[0] if self.failed_checks else "UNKNOWN_DEFECT"
        )


@dataclass
class IndividualFileCertificationReport:
    per_file: list[PerFileCertification]

    @property
    def all_certified(self) -> bool:
        return len(self.per_file) > 0 and all(f.certified_correct for f in self.per_file)

    @property
    def certified_correct_count(self) -> int:
        return sum(1 for f in self.per_file if f.certified_correct)

    @property
    def total_files(self) -> int:
        return len(self.per_file)

    def counts_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.per_file:
            counts[f.final_status] = counts.get(f.final_status, 0) + 1
        return counts


class FileCertifier(ABC):
    """Produktspezifische Implementierung dieser abstrakten 8 Pruefungen
    (Duplicate-Check ist generisch/produktunabhaengig und bereits im
    Engine-Code unten implementiert, kein abstrakter Methodenaufruf
    noetig). Jedes Produkt (WXK, Verbundwerk, ein zukuenftiges Produkt)
    MUSS diese Klasse implementieren, um certify_release() zu nutzen --
    es gibt keine Default-Passthrough-Implementierung, die eine Pruefung
    versehentlich immer TRUE zurueckgibt."""

    @abstractmethod
    def check_ownership(self, rel_path: str) -> bool: ...

    @abstractmethod
    def check_tax_relevance(self, rel_path: str) -> bool: ...

    @abstractmethod
    def check_tax_entity(self, rel_path: str) -> bool: ...

    @abstractmethod
    def check_tax_year(self, rel_path: str) -> bool: ...

    @abstractmethod
    def check_document_type(self, rel_path: str) -> bool: ...

    @abstractmethod
    def check_folder_placement(self, rel_path: str) -> tuple[bool, str, str]:
        """Gibt (valid, actual_folder, expected_folder) zurueck."""

    @abstractmethod
    def check_scope(self, rel_path: str) -> bool: ...

    @abstractmethod
    def check_sensitivity(self, rel_path: str) -> bool: ...

    @abstractmethod
    def check_manifest(self, rel_path: str) -> bool:
        """MANIFEST_VALID -- eigene, unabhaengige Pruefung, ob ein
        Manifest-Eintrag fuer diesen physischen Pfad existiert UND korrekt
        ist. Wird NIE aus einem bereits gecachten Builder-Ergebnis
        uebernommen, sondern hier je Aufruf frisch nachgeschlagen."""


def certify_release(final_folder: str, certifier: FileCertifier) -> IndividualFileCertificationReport:
    """INDEPENDENCE RULE: liest den PHYSISCHEN Ordner unabhaengig neu
    (os.walk direkt auf der Platte) -- wiederholt NIEMALS nur die
    Manifest-/Builder-Entscheidung. Duplicate-Check ist generisch: volle
    SHA256-Content-Hash-Gruppierung ueber den GANZEN physischen Bestand,
    unabhaengig davon was das Manifest je Datei behauptet."""
    all_files: list[tuple[str, str]] = []  # (rel_path, abs_path)
    hash_by_rel: dict[str, str] = {}
    hash_groups: dict[str, list[str]] = {}

    for root, dirs, files in os.walk(_lp(final_folder)):
        for fn in files:
            abs_path = os.path.join(root, fn)
            rel = os.path.relpath(abs_path, _lp(final_folder)).replace(os.sep, "/")
            all_files.append((rel, abs_path))
            file_hash = _sha256(abs_path)
            hash_by_rel[rel] = file_hash
            hash_groups.setdefault(file_hash, []).append(rel)

    per_file: list[PerFileCertification] = []
    for rel, abs_path in sorted(all_files):
        ownership_valid = certifier.check_ownership(rel)
        tax_relevance_valid = certifier.check_tax_relevance(rel)
        tax_entity_valid = certifier.check_tax_entity(rel)
        tax_year_valid = certifier.check_tax_year(rel)
        document_type_valid = certifier.check_document_type(rel)
        folder_valid, actual_folder, expected_folder = certifier.check_folder_placement(rel)
        scope_valid = certifier.check_scope(rel)
        sensitivity_valid = certifier.check_sensitivity(rel)
        manifest_valid = certifier.check_manifest(rel)

        # Generischer, produktunabhaengiger Duplicate-Check: dieser Pfad
        # ist genau dann CANONICAL_ARTIFACT (duplicate_status_valid=True),
        # wenn er entweder alleine in seiner Hash-Gruppe steht, ODER der
        # deterministisch kanonische Vertreter (kuerzester Pfad) der
        # Gruppe ist -- alle anderen Gruppenmitglieder sind
        # DUPLICATE_REFERENCE_ONLY und damit NICHT certified_correct.
        group = hash_groups[hash_by_rel[rel]]
        if len(group) == 1:
            duplicate_status_valid = True
        else:
            canonical = sorted(group, key=lambda p: (len(p), p))[0]
            duplicate_status_valid = (rel == canonical)

        checks = {
            "OWNERSHIP_VALID": ownership_valid,
            "TAX_RELEVANCE_VALID": tax_relevance_valid,
            "TAX_ENTITY_VALID": tax_entity_valid,
            "TAX_YEAR_VALID": tax_year_valid,
            "DOCUMENT_TYPE_VALID": document_type_valid,
            "FOLDER_PLACEMENT_VALID": folder_valid,
            "SCOPE_VALID": scope_valid,
            "DUPLICATE_STATUS_VALID": duplicate_status_valid,
            "SENSITIVITY_VALID": sensitivity_valid,
            "MANIFEST_VALID": manifest_valid,
        }
        failed = tuple(name for name, ok in checks.items() if not ok)

        per_file.append(PerFileCertification(
            rel_path=rel,
            ownership_valid=ownership_valid,
            tax_relevance_valid=tax_relevance_valid,
            tax_entity_valid=tax_entity_valid,
            tax_year_valid=tax_year_valid,
            document_type_valid=document_type_valid,
            folder_placement_valid=folder_valid,
            scope_valid=scope_valid,
            duplicate_status_valid=duplicate_status_valid,
            sensitivity_valid=sensitivity_valid,
            manifest_valid=manifest_valid,
            actual_folder=actual_folder,
            expected_folder=expected_folder,
            failed_checks=failed,
        ))

    return IndividualFileCertificationReport(per_file=per_file)


@dataclass
class FinalReleaseVerification:
    """FINAL RELEASE FORMULA (Order): final_verified ist NUR True, wenn
    ALLE sechs Gates TRUE sind -- inkl. individual_file_certification.
    all_certified. Dies ist eine berechnete Property (kein settable Feld),
    daher strukturell unmoeglich, Gate B zu umgehen, indem man einfach
    final_verified=True setzt."""
    manifest_parity: bool
    individual_file_certification: IndividualFileCertificationReport
    privacy_safe: bool
    tax_complete: bool
    folder_structure_verified: bool
    zip_parity: bool

    @property
    def final_verified(self) -> bool:
        return (
            self.manifest_parity and
            self.individual_file_certification.all_certified and
            self.privacy_safe and
            self.tax_complete and
            self.folder_structure_verified and
            self.zip_parity
        )

    def gate_report(self) -> dict:
        return {
            "MANIFEST_PARITY": self.manifest_parity,
            "INDIVIDUAL_FILE_CERTIFICATION": self.individual_file_certification.all_certified,
            "INDIVIDUAL_FILE_CERTIFICATION_DETAIL": (
                f"{self.individual_file_certification.certified_correct_count}/"
                f"{self.individual_file_certification.total_files} CERTIFIED_CORRECT"
            ),
            "PRIVACY_SAFE": self.privacy_safe,
            "TAX_COMPLETE": self.tax_complete,
            "FOLDER_STRUCTURE_VERIFIED": self.folder_structure_verified,
            "ZIP_PARITY": self.zip_parity,
            "FINAL_VERIFIED": self.final_verified,
        }
