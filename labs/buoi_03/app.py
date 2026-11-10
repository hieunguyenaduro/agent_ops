"""Buổi 3 — Agent API đã sẵn sàng để đóng gói bằng Docker.

So với buổi 2, file này thêm hai thứ mà một container cần:

1. Ghi lịch sử request vào SQLite ở đường dẫn cấu hình được (`DB_PATH`).
   Container có thể bị xoá bất cứ lúc nào, nên dữ liệu phải nằm ngoài
   filesystem của container — ta mount một volume vào `/data`.
2. Vòng đời ứng dụng (lifespan): chuẩn bị database lúc khởi động và log
   lúc tắt, để biết container đã shutdown sạch hay bị kill.

Chạy local (không Docker):

    DB_PATH=data/agent.db uvicorn labs.buoi_03.app:app --port 8000
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langfuse import get_client
from pydantic import BaseModel, Field

from labs.common.agent import stream
from labs.common.config import settings
from labs.common.streaming import preserve_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("agent.api")

# Trong container, compose đặt biến này thành /data/agent.db và mount
# volume vào /data. Chạy local thì dùng thư mục data/ của repo.
DB_PATH = os.getenv("DB_PATH", "data/agent.db")


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                session_id  TEXT NOT NULL,
                question    TEXT NOT NULL,
                answer      TEXT NOT NULL,
                latency_ms  INTEGER NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_run(
    *,
    request_id: str,
    user_id: str,
    session_id: str,
    question: str,
    answer: str,
    latency_ms: int,
) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO runs "
            "(id, user_id, session_id, question, answer, latency_ms) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (request_id, user_id, session_id, question, answer, latency_ms),
        )
        conn.commit()
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Chạy một lần khi container start và một lần khi start shutdown."""
    init_db()
    log.info(
        json.dumps(
            {
                "event": "app.start",
                "version": settings.app_version,
                "db_path": DB_PATH,
                "offline": settings.offline,
            }
        )
    )
    yield
    # Uvicorn nhận SIGTERM, ngừng nhận request mới, đợi request đang chạy
    # xong (tối đa --timeout-graceful-shutdown), rồi mới tới đây.
    # Flush trace lần cuối: nếu không, các span của vài giây cuối có thể
    # bị mất khi container bị xoá.
    get_client().flush()
    log.info(json.dumps({"event": "app.stop", "version": settings.app_version}))


app = FastAPI(title="Support Agent API", version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: đổi thành domain frontend thật.
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    user_id: str = Field(default="anonymous", min_length=1, max_length=200)
    session_id: str | None = Field(default=None, max_length=200)


class HealthResponse(BaseModel):
    status: str
    version: str
    model: str
    tracing: bool
    offline: bool
    database: str


def sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """Health check chạm nhẹ vào DB để chắc chắn volume còn ghi được."""
    database = "ok"
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        database = "error"

    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        version=settings.app_version,
        model=settings.openai_model,
        tracing=settings.tracing_enabled,
        offline=settings.offline,
        database=database,
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "support-agent",
        "version": settings.app_version,
        "docs": "/docs",
        "chat": "POST /chat (SSE)",
        "history": "SELECT * FROM runs; (SQLite)",
    }


@app.post("/chat")
def chat(payload: ChatRequest) -> StreamingResponse:
    request_id = uuid.uuid4().hex[:12]
    session_id = payload.session_id or f"sess-{request_id}"
    started = time.perf_counter()

    log.info(
        json.dumps(
            {
                "event": "chat.start",
                "request_id": request_id,
                "user_id": payload.user_id,
                "session_id": session_id,
                "question_length": len(payload.question),
            },
            ensure_ascii=False,
        )
    )

    def events():
        trace_id = None
        latency_ms = 0
        answer_parts: list[str] = []

        try:
            yield sse(
                "start",
                {
                    "request_id": request_id,
                    "session_id": session_id,
                    "version": settings.app_version,
                },
            )

            for event_type, data in stream(
                payload.question,
                user_id=payload.user_id,
                session_id=session_id,
                chunk_delay=0.02,
            ):
                if event_type == "delta":
                    answer_parts.append(data["text"])
                elif event_type == "done":
                    trace_id = data.get("trace_id")
                    latency_ms = data.get("latency_ms", 0)
                yield sse(event_type, data)

        except Exception:
            log.exception("chat.failed request_id=%s", request_id)
            yield sse(
                "error",
                {
                    "request_id": request_id,
                    "message": "Agent đang gặp sự cố. Vui lòng thử lại sau ít phút.",
                },
            )
        finally:
            # Ngay cả khi agent lỗi, vẫn ghi lại request để còn điều tra.
            try:
                save_run(
                    request_id=request_id,
                    user_id=payload.user_id,
                    session_id=session_id,
                    question=payload.question,
                    answer="".join(answer_parts).strip(),
                    latency_ms=latency_ms,
                )
            except sqlite3.Error:
                # Ghi log nhưng không làm hỏng response của người dùng.
                log.exception("db.write_failed request_id=%s", request_id)

            duration_ms = int((time.perf_counter() - started) * 1000)
            log.info(
                json.dumps(
                    {
                        "event": "chat.end",
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "duration_ms": duration_ms,
                    },
                    ensure_ascii=False,
                )
            )

    return StreamingResponse(
        preserve_context(events()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
