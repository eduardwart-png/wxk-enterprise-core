"""
Enterprise Core — Tests fuer Jobs (Retry/DLQ/Idempotency) und Feature Flags.
Continuation-Order §10: BUILD->TEST->BREAK->RECOVER->VERIFY je Block.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

import pytest
from db import init_schema
from auth import create_tenant
from jobs import enqueue, run_job, get_dlq, get_job_status
from feature_flags import set_flag, is_enabled


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "core_test.sqlite"
    init_schema(db_path)
    return db_path


@pytest.fixture
def tenant(db):
    return create_tenant(db, "Test Tenant")


# --------------------------------------------------------------- Jobs -----

def test_job_erfolgreich(db, tenant):
    job_id = enqueue(db, tenant, "TEST_JOB", {"wert": 42})
    status = run_job(db, job_id, handler=lambda p: None)
    assert status == "SUCCESS"
    assert get_job_status(db, tenant, job_id)["status"] == "SUCCESS"


def test_job_idempotenz_gleicher_key_kein_zweiter_job(db, tenant):
    id1 = enqueue(db, tenant, "TEST_JOB", {"a": 1}, idempotency_key="FIXED-KEY")
    id2 = enqueue(db, tenant, "TEST_JOB", {"a": 1}, idempotency_key="FIXED-KEY")
    assert id1 == id2


def test_job_retry_dann_dlq(db, tenant):
    """BREAK: Handler wirft IMMER -- Job muss nach max_versuche in FAILED_DLQ
    landen, nicht endlos retrien und nicht verschwinden."""
    job_id = enqueue(db, tenant, "KAPUTTER_JOB", {}, max_versuche=3)

    def kaputter_handler(payload):
        raise RuntimeError("simulierter Fehler")

    r1 = run_job(db, job_id, kaputter_handler)
    assert r1 == "RETRYING"
    r2 = run_job(db, job_id, kaputter_handler)
    assert r2 == "RETRYING"
    r3 = run_job(db, job_id, kaputter_handler)
    assert r3 == "FAILED_DLQ"

    # VERIFY: Job ist NICHT verschwunden, sondern sichtbar in der DLQ
    dlq = get_dlq(db, tenant)
    assert any(j["job_id"] == job_id for j in dlq)
    assert "simulierter Fehler" in dlq[0]["letzter_fehler"]


def test_job_cross_tenant_dlq_isolation(db):
    """SEV-0-Pflichttest: DLQ-Eintraege eines Tenants duerfen bei einem
    anderen Tenant NICHT sichtbar sein."""
    tenant_a = create_tenant(db, "A")
    tenant_b = create_tenant(db, "B")
    job_id = enqueue(db, tenant_a, "JOB", {}, max_versuche=1)
    run_job(db, job_id, handler=lambda p: (_ for _ in ()).throw(RuntimeError("x")))

    dlq_a = get_dlq(db, tenant_a)
    dlq_b = get_dlq(db, tenant_b)
    assert len(dlq_a) == 1
    assert len(dlq_b) == 0


# ------------------------------------------------------- Feature Flags ---

def test_flag_default_aus(db, tenant):
    assert is_enabled(db, "unbekanntes_flag", tenant) is False


def test_flag_global_an(db, tenant):
    set_flag(db, "global_flag", enabled=True, tenant_id=None)
    assert is_enabled(db, "global_flag", tenant) is True


def test_flag_tenant_override_hat_vorrang(db, tenant):
    set_flag(db, "test_flag", enabled=True, tenant_id=None)
    set_flag(db, "test_flag", enabled=False, tenant_id=tenant)
    assert is_enabled(db, "test_flag", tenant) is False


def test_flag_rollout_deterministisch(db, tenant):
    """Gleicher Tenant + Flag liefert bei mehreren Aufrufen IMMER dasselbe
    Ergebnis (kein Zufall) -- wichtig fuer Canary/Shadow-Reproduzierbarkeit."""
    set_flag(db, "rollout_flag", enabled=True, tenant_id=None, rollout_prozent=50)
    ergebnisse = {is_enabled(db, "rollout_flag", tenant) for _ in range(20)}
    assert len(ergebnisse) == 1  # immer dasselbe Ergebnis
