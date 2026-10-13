"""Enterprise Core — Release Certification Tests (CRITICAL LESSON
INDIVIDUAL_FILE_CERTIFICATION_IS_A_SEPARATE_GATE, Order-Pflichttests)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import pytest

from release_certification import (
    FileCertifier, certify_release, FinalReleaseVerification,
    IndividualFileCertificationReport, PerFileCertification,
)


def _mk(base: Path, rel: str, content: bytes = b"x") -> Path:
    full = base / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(content)
    return full


class AlwaysValidCertifier(FileCertifier):
    """Testfixture: alles gueltig ausser explizit ueberschrieben."""
    def check_ownership(self, rel_path): return True
    def check_tax_relevance(self, rel_path): return True
    def check_tax_entity(self, rel_path): return True
    def check_tax_year(self, rel_path): return "2021" not in rel_path and "2026" not in rel_path
    def check_document_type(self, rel_path): return True
    def check_folder_placement(self, rel_path):
        if "wrong_entity_marker" in rel_path:
            return False, "01_PRIVAT", "02_KSZ"
        return True, "correct", "correct"
    def check_scope(self, rel_path): return "out_of_scope" not in rel_path
    def check_sensitivity(self, rel_path): return "ausweis" not in rel_path.lower()
    def check_manifest(self, rel_path): return "unmanifested" not in rel_path


@pytest.fixture
def tmp_release():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def test_manifest_parity_does_not_imply_certification(tmp_release):
    """Kernbeweis der Lesson: MANIFEST_PARITY=True allein macht
    final_verified NICHT True, wenn die Individual-File-Certification
    fehlschlaegt."""
    _mk(tmp_release, "2023/unmanifested_file.pdf")
    report = certify_release(str(tmp_release), AlwaysValidCertifier())
    assert report.all_certified is False  # MANIFEST_VALID=False fuer diese Datei

    verification = FinalReleaseVerification(
        manifest_parity=True,  # Gate A besteht technisch
        individual_file_certification=report,
        privacy_safe=True, tax_complete=True,
        folder_structure_verified=True, zip_parity=True,
    )
    assert verification.final_verified is False


def test_duplicate_can_be_manifested_but_rejected(tmp_release):
    """Zwei byte-identische Dateien unter verschiedenen Pfaden: beide
    koennten technisch 'manifestiert' sein, aber nur der kanonische
    Vertreter darf CERTIFIED_CORRECT werden."""
    _mk(tmp_release, "2023/a_prefix1/rechnung.pdf", b"identical content")
    _mk(tmp_release, "2023/z_prefix2/rechnung.pdf", b"identical content")
    report = certify_release(str(tmp_release), AlwaysValidCertifier())
    statuses = {f.rel_path: f.certified_correct for f in report.per_file}
    n_certified = sum(1 for ok in statuses.values() if ok)
    assert n_certified == 1, "Genau 1 der 2 Duplikate darf CERTIFIED_CORRECT sein"
    assert report.all_certified is False  # der zweite bleibt DUPLICATE_STATUS_VALID=False


def test_out_of_scope_year_rejected_after_manifest(tmp_release):
    _mk(tmp_release, "01_PRIVAT/out_of_scope_2021_beleg.pdf")
    report = certify_release(str(tmp_release), AlwaysValidCertifier())
    f = report.per_file[0]
    assert f.scope_valid is False
    assert f.certified_correct is False


def test_wrong_tax_entity_rejected_after_manifest(tmp_release):
    _mk(tmp_release, "01_PRIVAT/wrong_entity_marker_ksz_beschluss.pdf")
    report = certify_release(str(tmp_release), AlwaysValidCertifier())
    f = report.per_file[0]
    assert f.folder_placement_valid is False
    assert f.actual_folder != f.expected_folder
    assert f.certified_correct is False


def test_wrong_folder_rejected_after_manifest(tmp_release):
    """Wie test_wrong_tax_entity, aber als eigener Order-Pflichttest:
    beweist die generische FOLDER_PLACEMENT_VALID-Pruefung unabhaengig
    von der Tax-Entity-Semantik."""
    _mk(tmp_release, "01_PRIVAT/wrong_entity_marker_x.pdf")
    report = certify_release(str(tmp_release), AlwaysValidCertifier())
    assert report.per_file[0].folder_placement_valid is False


def test_individual_certification_reads_physical_release(tmp_release):
    """INDEPENDENCE RULE: certify_release() liest den physischen Ordner
    direkt (os.walk), nicht aus einem vom Aufrufer vorgegebenen Manifest-
    Cache -- beweisen, indem eine Datei NACH einer ersten Zertifizierung
    physisch hinzugefuegt wird und in einem zweiten Lauf real erscheint."""
    _mk(tmp_release, "2023/erste_datei.pdf")
    report1 = certify_release(str(tmp_release), AlwaysValidCertifier())
    assert report1.total_files == 1

    _mk(tmp_release, "2023/zweite_datei_nachtraeglich.pdf")
    report2 = certify_release(str(tmp_release), AlwaysValidCertifier())
    assert report2.total_files == 2, "Zweiter Lauf muss die physisch neue Datei real sehen"


def test_only_certified_correct_files_survive_final_release(tmp_release):
    """HARD RULE: nur CERTIFIED_CORRECT darf im finalen Release verbleiben
    -- dieser Test beweist, dass die Unterscheidung CERTIFIED_CORRECT vs.
    alles-andere fuer eine gemischte Menge korrekt funktioniert."""
    _mk(tmp_release, "2023/gueltige_datei.pdf")
    _mk(tmp_release, "2023/out_of_scope_datei.pdf")
    _mk(tmp_release, "2023/unmanifested_datei.pdf")
    _mk(tmp_release, "2023/personalausweis_kopie.pdf")

    report = certify_release(str(tmp_release), AlwaysValidCertifier())
    survivors = [f.rel_path for f in report.per_file if f.certified_correct]
    rejected = [f.rel_path for f in report.per_file if not f.certified_correct]

    assert survivors == ["2023/gueltige_datei.pdf"]
    assert len(rejected) == 3
    assert report.all_certified is False


def test_file_certifier_is_abstract_cannot_be_instantiated():
    """Beweist, dass kein Produkt certify_release() ohne eigene
    Implementierung aller 8 abstrakten Pruefungen nutzen kann."""
    with pytest.raises(TypeError):
        FileCertifier()


def test_final_verified_requires_all_six_gates(tmp_release):
    """Kombinatorischer Beweis: jedes einzelne der 6 Gates blockiert
    final_verified allein, wenn es False ist -- auch wenn die anderen 5
    True sind."""
    _mk(tmp_release, "2023/ok.pdf")
    good_report = certify_release(str(tmp_release), AlwaysValidCertifier())
    assert good_report.all_certified is True

    base_kwargs = dict(
        manifest_parity=True, individual_file_certification=good_report,
        privacy_safe=True, tax_complete=True,
        folder_structure_verified=True, zip_parity=True,
    )
    # Baseline: alles True -> final_verified True
    assert FinalReleaseVerification(**base_kwargs).final_verified is True

    for flag in ("manifest_parity", "privacy_safe", "tax_complete",
                  "folder_structure_verified", "zip_parity"):
        broken = dict(base_kwargs)
        broken[flag] = False
        assert FinalReleaseVerification(**broken).final_verified is False, \
            f"final_verified muesste False sein wenn {flag}=False"
