"""Buổi 9 — hàng đợi bền vững trên SQLite.

Vì sao cần hàng đợi? Vì một request agent có thể mất 10–30 giây. Nếu giữ
request HTTP mở suốt thời gian đó, người dùng dễ gặp timeout, và khi
container restart thì việc đang làm bị mất.

Mô hình tối thiểu nhưng đúng:

    enqueue  →  queued  →  worker claim  →  running  →  done
                             │                 │
                             │                 ├─ lỗi tạm thời → queued (retry)
                             │                 └─ quá số lần thử → dead
                             └─ crash/restart → lease hết hạn → worker khác nhận

Ba khái niệm quan trọng:

1. **Lease**: worker "thuê" job trong một khoảng thời gian. Nếu worker chết,
   lease hết hạn và job được nhận lại. Không cần ai dọn tay.
2. **At-least-once**: job được xử lý ít nhất một lần, có thể hai lần nếu
   worker chết sau khi làm xong nhưng trước khi ghi kết quả. Vì vậy thao
   tác phụ (gửi email, trừ tiền) phải **idempotent**.
3. **Idempotency key**: khóa do client gửi. Hai lần bấm nút chỉ tạo một job.

SQLite đủ cho lab và cho nhiều hệ thống nhỏ. Khi cần nhiều máy cùng lúc,
thay bằng Postgres/Redis/SQS — nhưng **hợp đồng** (status, lease, attempts)
giữ nguyên.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    idempotency_key TEXT UNIQUE,
    question        TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued',
    attempts        INTEGER NOT NULL DEFAULT 0,
    answer          TEXT,
    error           TEXT,
    worker_id       TEXT,
    lease_until     REAL,
    created_at      REAL NOT NULL,
    updated_at      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_created
    ON jobs (status, created_at);
"""


@dataclass
class Job:
    id: str
    question: str
    user_id: str
    session_id: str
    status: str
    attempts: int
    answer: str | None
    error: str | None
    worker_id: str | None
    lease_until: float | None
    created_at: float
    updated_at: float


class JobStore:
    def __init__(
        self,
        path: str | Path = ":memory:",
        *,
        lease_seconds: float = 30.0,
        max_attempts: int = 3,
    ) -> None:
        self.path = str(path)
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # -- hạ tầng ---------------------------------------------------------

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        """BEGIN IMMEDIATE: khóa ghi ngay từ đầu, tránh hai worker cùng nhận
        một job. Với SQLite, đây là điểm quan trọng nhất của cả file."""
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            question=row["question"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            status=row["status"],
            attempts=row["attempts"],
            answer=row["answer"],
            error=row["error"],
            worker_id=row["worker_id"],
            lease_until=row["lease_until"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # -- API cho producer ------------------------------------------------

    def enqueue(
        self,
        question: str,
        *,
        user_id: str,
        session_id: str,
        idempotency_key: str | None = None,
    ) -> str:
        """Thêm job. Nếu key đã tồn tại, trả về id cũ — không tạo job mới."""
        job_id = uuid.uuid4().hex[:12]
        now = time.time()
        try:
            self._conn.execute(
                """INSERT INTO jobs
                   (id, idempotency_key, question, user_id, session_id,
                    status, attempts, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'queued', 0, ?, ?)""",
                (job_id, idempotency_key, question, user_id, session_id, now, now),
            )
            self._conn.commit()
            return job_id
        except sqlite3.IntegrityError:
            # INSERT lỗi đã mở một transaction ngầm. Phải rollback trước khi
            # đọc, nếu không transaction này sẽ treo và làm `claim` sau đó
            # không thể BEGIN IMMEDIATE.
            self._conn.rollback()
            row = self._conn.execute(
                "SELECT id FROM jobs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is None:
                raise
            return row["id"]

    # -- API cho worker --------------------------------------------------

    def claim(self, worker_id: str) -> Job | None:
        """Nhận job kế tiếp, kể cả job có lease đã hết hạn.

        Trả về None khi hàng đợi rỗng. Job vượt quá max_attempts bị đánh
        dấu `dead` thay vì lặp vô hạn.
        """
        now = time.time()
        with self._transaction():
            while True:
                row = self._conn.execute(
                    """SELECT * FROM jobs
                       WHERE status = 'queued'
                          OR (status = 'running' AND lease_until IS NOT NULL
                              AND lease_until < ?)
                       ORDER BY created_at ASC, id ASC
                       LIMIT 1""",
                    (now,),
                ).fetchone()
                if row is None:
                    return None

                if row["attempts"] >= self.max_attempts:
                    self._conn.execute(
                        """UPDATE jobs
                           SET status = 'dead',
                               error = COALESCE(error, 'vượt quá số lần thử'),
                               lease_until = NULL,
                               updated_at = ?
                           WHERE id = ?""",
                        (now, row["id"]),
                    )
                    continue

                self._conn.execute(
                    """UPDATE jobs
                       SET status = 'running',
                           attempts = attempts + 1,
                           worker_id = ?,
                           lease_until = ?,
                           updated_at = ?
                       WHERE id = ?""",
                    (worker_id, now + self.lease_seconds, now, row["id"]),
                )
                claimed = self._conn.execute(
                    "SELECT * FROM jobs WHERE id = ?", (row["id"],)
                ).fetchone()
                # Thoát vòng lặp sau khi đã nhận job. Nếu không, vòng lặp
                # chạy tiếp, không còn job nào và trả về None — job đã bị
                # đánh dấu running nhưng không ai xử lý.
                break

        return self._row_to_job(claimed)

    def complete(self, job_id: str, answer: str) -> None:
        now = time.time()
        with self._transaction():
            self._conn.execute(
                """UPDATE jobs
                   SET status = 'done', answer = ?, error = NULL,
                       lease_until = NULL, updated_at = ?
                   WHERE id = ?""",
                (answer, now, job_id),
            )

    def fail(self, job_id: str, error: str) -> str:
        """Ghi lỗi. Còn lượt thì đưa về queued, hết lượt thì dead.

        Trả về status mới để worker/demo in ra.
        """
        now = time.time()
        with self._transaction():
            row = self._conn.execute(
                "SELECT attempts FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise KeyError(job_id)

            status = "dead" if row["attempts"] >= self.max_attempts else "queued"
            self._conn.execute(
                """UPDATE jobs
                   SET status = ?, error = ?,
                       lease_until = NULL, worker_id = NULL, updated_at = ?
                   WHERE id = ?""",
                (status, error, now, job_id),
            )
        return status

    # -- truy vấn --------------------------------------------------------

    def get(self, job_id: str) -> Job | None:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return self._row_to_job(row) if row else None

    def all_jobs(self) -> list[Job]:
        rows = self._conn.execute(
            "SELECT * FROM jobs ORDER BY created_at ASC, id ASC"
        ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def stats(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) AS n FROM jobs GROUP BY status"
        ).fetchall()
        counts = {row["status"]: row["n"] for row in rows}
        for status in ("queued", "running", "done", "dead"):
            counts.setdefault(status, 0)
        return counts

    def close(self) -> None:
        self._conn.close()
