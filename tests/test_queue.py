"""Test cho hàng đợi bền vững — lease, retry, idempotency."""

from __future__ import annotations

import time

import pytest

from labs.buoi_09.store import JobStore


@pytest.fixture
def store(tmp_path):
    store = JobStore(tmp_path / "jobs.db", lease_seconds=0.2, max_attempts=3)
    yield store
    store.close()


def enqueue(store: JobStore, key: str | None = None) -> str:
    return store.enqueue(
        "Đơn A1001 bao giờ tới?",
        user_id="u-1",
        session_id="s-1",
        idempotency_key=key,
    )


def test_idempotency_key_khong_tao_job_trung(store):
    first = enqueue(store, key="click-1")
    second = enqueue(store, key="click-1")

    assert first == second
    assert store.stats()["queued"] == 1


def test_claim_roi_complete(store):
    job_id = enqueue(store)

    job = store.claim("worker-a")
    assert job is not None
    assert job.id == job_id
    assert job.status == "running"
    assert job.attempts == 1

    store.complete(job.id, "đơn đang giao")

    done = store.get(job_id)
    assert done is not None
    assert done.status == "done"
    assert done.answer == "đơn đang giao"


def test_claim_khi_hang_doi_rong(store):
    assert store.claim("worker-a") is None


def test_lease_chua_het_thi_khong_nhan_lai(store):
    enqueue(store)
    assert store.claim("worker-a") is not None
    assert store.claim("worker-b") is None


def test_lease_het_thi_worker_khac_nhan_lai(store):
    job_id = enqueue(store)
    assert store.claim("worker-a") is not None

    time.sleep(0.25)

    reclaimed = store.claim("worker-b")
    assert reclaimed is not None
    assert reclaimed.id == job_id
    assert reclaimed.attempts == 2


def test_retry_qua_so_lan_thi_dead(store):
    job_id = enqueue(store)

    for _ in range(3):
        job = store.claim("worker-a")
        assert job is not None
        status = store.fail(job.id, "upstream timeout")

    assert status == "dead"
    final = store.get(job_id)
    assert final is not None
    assert final.status == "dead"
    assert final.error == "upstream timeout"


def test_max_attempts_khong_lap_vo_han(store):
    # Job chết liên tục (crash trước khi complete) không được thử mãi.
    enqueue(store)
    for _ in range(3):
        job = store.claim("worker-a")
        assert job is not None
        time.sleep(0.25)

    # Lần claim thứ tư đánh dấu dead thay vì nhận lại.
    assert store.claim("worker-a") is None
    assert store.stats()["dead"] == 1
