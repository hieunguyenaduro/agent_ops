"""Buổi 9 — demo crash, phục hồi lease và retry.

Chạy:

    python -m labs.buoi_09.demo

Kịch bản:

1. Enqueue 5 câu hỏi; bấm nút hai lần (idempotency key) chỉ tạo 1 job.
2. Worker A xử lý 2 job, rồi "chết" ở job thứ 3 (trước khi ghi kết quả).
3. Job thứ 3 vẫn `running` với lease. Sau khi lease hết hạn, worker B
   nhận lại và hoàn tất.
4. Job lỗi được thử lại; quá số lần thử thì vào `dead`.

Không có bước nào cần key thật: agent chạy ở chế độ offline.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from .store import JobStore
from .worker import SimulatedCrash, run_until_empty

QUESTIONS = [
    "Đơn A1001 bao giờ tới?",
    "Đơn A1002 đã giao chưa?",
    "Đơn A1003 đang xử lý à?",
    "Tổng tiền đơn A1001 là bao nhiêu?",
    "Đơn A1002 giao lúc nào?",
]


def show_stats(store: JobStore, label: str) -> None:
    counts = store.stats()
    line = " | ".join(f"{name}={counts[name]}" for name in ("queued", "running", "done", "dead"))
    print(f"  {label:<28}{line}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "jobs.db"
        store = JobStore(db_path, lease_seconds=0.5, max_attempts=3)

        print("=== 1. Enqueue ===")
        ids = []
        for index, question in enumerate(QUESTIONS):
            job_id = store.enqueue(
                question,
                user_id=f"u-{index}",
                session_id=f"s-{index}",
                # Client gửi cùng key khi retry → không tạo job trùng.
                idempotency_key=f"click-{index}",
            )
            ids.append(job_id)

        duplicate = store.enqueue(
            QUESTIONS[0],
            user_id="u-0",
            session_id="s-0",
            idempotency_key="click-0",
        )
        print(f"  5 câu hỏi → {len(ids)} job")
        print(f"  Bấm lại cùng key → id {'giống' if duplicate == ids[0] else 'KHÁC'}: {duplicate}")
        show_stats(store, "ban đầu")

        print("\n=== 2. Worker A chết giữa chừng ===")
        try:
            run_until_empty(store, "worker-a", crash_after_jobs=2)
        except SimulatedCrash as exc:
            print(f"  💥 {exc}")
            print("  Job đang chạy vẫn ở trạng thái running, lease chưa hết.")
        show_stats(store, "sau crash")

        print("\n=== 3. Chờ lease hết hạn, worker B tiếp quản ===")
        time.sleep(0.7)
        run_until_empty(store, "worker-b")
        show_stats(store, "sau khi worker B chạy")

        print("\n=== 4. Kết quả ===")
        jobs = store.all_jobs()
        for job in jobs:
            short = (job.answer or "").replace("\n", " ")[:58]
            print(f"  {job.id}  attempts={job.attempts}  {short}…")

        reclaimed = [job for job in jobs if job.attempts > 1]
        print(
            f"\n  Có {len(reclaimed)} job được nhận lại sau crash "
            f"(attempts > 1). Điều này bình thường với at-least-once."
        )
        print(
            "  Vì vậy tác dụng phụ (gửi email, trừ tiền) phải idempotent —\n"
            "  dùng chính job.id làm khóa ở hệ thống downstream."
        )

        print("\n=== 5. Retry và dead letter ===")
        failing = store.enqueue(
            "Đơn A9999 ở đâu?",
            user_id="u-x",
            session_id="s-x",
            idempotency_key="fail-demo",
        )
        for attempt in range(1, 4):
            job = store.claim("worker-c")
            assert job is not None
            status = store.fail(job.id, "upstream timeout")
            print(f"  lần {attempt}: status={status}")

        final = store.get(failing)
        assert final is not None
        print(f"  Job {final.id} kết thúc ở status={final.status}, error={final.error}")
        print(
            "\n  `dead` không phải thùng rác: đó là hàng đợi cần người xem.\n"
            "  Alert khi dead > 0, và có lệnh requeue sau khi sửa nguyên nhân."
        )

        store.close()
        print(f"\nDB tạm đã xoá cùng thư mục: {db_path}")


if __name__ == "__main__":
    main()
