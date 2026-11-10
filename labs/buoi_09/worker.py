"""Buổi 9 — worker lấy job từ hàng đợi và chạy agent.

Worker cố tình viết đơn giản: một vòng lặp, một job một lúc. Điều quan
trọng không nằm ở vòng lặp, mà ở **thứ tự ba bước**:

    claim → làm việc → complete

Nếu chết ở giữa, job vẫn ở trạng thái `running` với lease. Hết lease,
worker khác nhận lại. Đây là điều làm hệ thống "bền" (durable) hơn một
`asyncio.create_task` trong RAM.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from labs.common.agent import run

from .store import Job, JobStore


class SimulatedCrash(RuntimeError):
    """Dùng trong demo: chết sau khi đã làm xong, trước khi ghi kết quả."""


@dataclass
class Processed:
    job: Job
    ok: bool
    detail: str


def process_one(
    store: JobStore,
    worker_id: str,
    *,
    crash_before_complete: bool = False,
) -> Processed | None:
    """Nhận và xử lý đúng một job. Trả None nếu hàng đợi rỗng."""
    job = store.claim(worker_id)
    if job is None:
        return None

    try:
        result = run(
            job.question,
            user_id=job.user_id,
            session_id=job.session_id,
        )
    except Exception as exc:  # noqa: BLE001 - lỗi của job, không phải của worker
        status = store.fail(job.id, f"{type(exc).__name__}: {exc}")
        return Processed(job=job, ok=False, detail=f"lỗi → {status}")

    if crash_before_complete:
        # Mô phỏng container bị kill ngay sau khi model trả lời.
        # Chưa ghi `complete`, nên lease vẫn còn và job vẫn `running`.
        raise SimulatedCrash(f"worker {worker_id} chết khi đang xử lý {job.id}")

    store.complete(job.id, result.answer)
    return Processed(
        job=job,
        ok=True,
        detail=f"xong sau {result.latency_ms}ms (lần thử {job.attempts})",
    )


def run_until_empty(
    store: JobStore,
    worker_id: str,
    *,
    max_jobs: int = 100,
    crash_after_jobs: int | None = None,
) -> list[Processed]:
    """Chạy tới khi hàng đợi rỗng hoặc đã xử lý `max_jobs`.

    `crash_after_jobs`: sau khi xong N job, cố tình chết ở job kế tiếp.
    Dùng để demo khả năng phục hồi mà không cần kill process thật.
    """
    processed: list[Processed] = []

    while len(processed) < max_jobs:
        crash = crash_after_jobs is not None and len(processed) >= crash_after_jobs
        item = process_one(store, worker_id, crash_before_complete=crash)
        if item is None:
            break
        processed.append(item)
        print(
            f"  [{worker_id}] {item.job.id} "
            f"{'✅' if item.ok else '❌'} {item.detail}"
        )
        # Nghỉ một chút cho dễ đọc log; worker thật không cần dòng này.
        time.sleep(0.01)

    return processed
