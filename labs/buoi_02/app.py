"""Buổi 2 — Agent API bằng FastAPI, trả kết quả qua SSE.

Chạy từ thư mục gốc repo:

    uvicorn labs.buoi_02.app:app --reload

Hai endpoint:
    GET  /healthz  — để load balancer biết service còn sống.
    POST /chat     — nhận câu hỏi, trả về một dòng sự kiện (SSE).

Vì sao SSE? Agent chạy vài giây đến vài chục giây. Nếu trả JSON một lần,
người dùng chỉ thấy màn hình trắng rồi đột ngột có kết quả. SSE gửi từng
sự kiện ngay khi có: đang tìm đơn → đã tìm thấy → đang soạn câu trả lời →
từng cụm từ của câu trả lời.
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from labs.common.agent import stream
from labs.common.config import settings
from labs.common.streaming import preserve_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("agent.api")

app = FastAPI(title="Support Agent API", version=settings.app_version)

# Lab cho phép mọi origin để mở giao diện từ file HTML local.
# Production: thay "*" bằng đúng domain của frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Dữ liệu đầu vào. Pydantic tự kiểm tra và trả lỗi 422 nếu sai."""

    question: str = Field(min_length=1, max_length=2_000)
    user_id: str = Field(default="anonymous", min_length=1, max_length=200)
    session_id: str | None = Field(default=None, max_length=200)


class HealthResponse(BaseModel):
    status: str
    version: str
    model: str
    tracing: bool
    offline: bool


def sse(event: str, data: dict) -> str:
    """Đóng gói một sự kiện theo định dạng Server-Sent Events.

    Định dạng rất đơn giản: một dòng `event:`, một dòng `data:`, rồi
    một dòng trống. Trình duyệt và httpx đều hiểu định dạng này.
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """Health check phải nhẹ: không gọi model, không truy vấn database."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        model=settings.openai_model,
        tracing=settings.tracing_enabled,
        offline=settings.offline,
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "support-agent",
        "version": settings.app_version,
        "docs": "/docs",
        "chat": "POST /chat (SSE)",
    }


@app.post("/chat")
def chat(payload: ChatRequest) -> StreamingResponse:
    """Nhận câu hỏi và stream tiến trình về cho client.

    Hàm này là `def` (đồng bộ) có chủ đích: Starlette sẽ chạy generator
    trong threadpool, nên lời gọi OpenAI đồng bộ không chặn event loop.
    """
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
        """Sinh chuỗi sự kiện. Không có biến toàn cục nào ở đây.

        Mỗi request có closure riêng, nên hai người dùng đồng thời không
        thể nhìn thấy dữ liệu của nhau.
        """
        trace_id = None
        try:
            # Cho client biết request đã được nhận trước khi agent kịp chạy.
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
                if event_type == "done":
                    trace_id = data.get("trace_id")
                yield sse(event_type, data)

        except Exception:
            # SSE đã trả 200 từ trước, không đổi được status code nữa.
            # Cách đúng: gửi một event `error` để client biết mà xử lý.
            log.exception("chat.failed request_id=%s", request_id)
            yield sse(
                "error",
                {
                    "request_id": request_id,
                    "message": "Agent đang gặp sự cố. Vui lòng thử lại sau ít phút.",
                },
            )
        finally:
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
            # Tắt cache và tắt buffer của proxy, nếu không sự kiện bị giữ
            # lại đến cuối và SSE mất hết ý nghĩa.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
