"""Agent đồ chơi dùng chung cho cả 10 buổi.

Bài toán: trợ lý chăm sóc khách hàng của một cửa hàng online.

Agent cố tình viết thật đơn giản:
    1. Tìm mã đơn hàng trong câu hỏi (A1001, A1002, ...).
    2. Tra cứu đơn hàng bằng một "tool" nội bộ.
    3. Gọi model để soạn câu trả lời.

Các buổi sau chỉ bọc thêm hạ tầng (API, Docker, cloud, tracing, eval...)
quanh lõi này — không viết lại agent.

Điểm quan trọng: mọi bước đều được trace lên Langfuse theo cùng một cấu
trúc, nên khi sang các buổi sau ta luôn có dữ liệu để so sánh.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from typing import Any, Iterator

from langfuse import get_client, propagate_attributes

from .config import settings
from .llm import chat

# Mã đơn hàng có dạng A + 4 chữ số.
ORDER_PATTERN = re.compile(r"\bA\d{4}\b", re.IGNORECASE)

# Dữ liệu giả lập. Thay bằng database thật là bài tập của buổi sau.
ORDERS: dict[str, dict[str, Any]] = {
    "A1001": {"status": "đang giao", "eta": "2 ngày nữa", "total": 450_000},
    "A1002": {"status": "đã giao", "eta": "đã nhận hàng", "total": 1_290_000},
    "A1003": {"status": "đang xử lý", "eta": "3 ngày nữa", "total": 89_000},
}

SYSTEM_PROMPT = (
    "Bạn là trợ lý chăm sóc khách hàng của một cửa hàng online. "
    "Trả lời ngắn gọn, thân thiện, bằng tiếng Việt. "
    "Chỉ dùng thông tin trong phần 'Dữ liệu đơn hàng' được cung cấp; "
    "nếu không có dữ liệu, hãy nói rằng bạn chưa tra được và xin mã đơn."
)

# Tên các bước, dùng chung giữa code và bài giảng.
STEP_CLASSIFY = "step.find_order_id"
STEP_LOOKUP = "tool.lookup_order"
STEP_LLM = "llm.answer"


@dataclass
class AgentResult:
    """Kết quả cuối cùng của một lần chạy agent."""

    answer: str
    steps: list[dict[str, Any]]
    order_id: str | None
    trace_id: str | None
    trace_url: str | None
    latency_ms: int
    model: str
    prompt_fingerprint: str
    offline: bool


def prompt_fingerprint() -> str:
    """Dấu vân tay của "bộ não" agent tại thời điểm chạy.

    Chỉ cần đổi prompt, đổi model hoặc thêm tool là fingerprint đổi.
    Nhờ vậy khi chất lượng giảm, ta biết bản nào đã tạo ra kết quả đó.
    """
    raw = f"{settings.openai_model}|{SYSTEM_PROMPT}|{sorted(ORDERS)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def find_order_id(text: str) -> str | None:
    match = ORDER_PATTERN.search(text)
    return match.group(0).upper() if match else None


def lookup_order(order_id: str) -> dict[str, Any] | None:
    """Tool tra cứu đơn hàng, có span riêng trên Langfuse.

    Span `tool.lookup_order` giúp nhìn thấy ngay: agent gọi tool nào,
    với tham số gì, mất bao lâu, trả về gì.
    """
    order = ORDERS.get(order_id.upper())

    with get_client().start_as_current_observation(
        as_type="tool",
        name=STEP_LOOKUP,
        input={"order_id": order_id},
        output=order or {"error": "không tìm thấy đơn"},
    ):
        pass

    return order


def _offline_answer(order_id: str | None, order: dict[str, Any] | None) -> str:
    """Câu trả lời mẫu khi chưa có OpenAI key."""
    if order and order_id:
        total = f"{order['total']:,}".replace(",", ".")
        return (
            f"Đơn {order_id} hiện có trạng thái: {order['status']} ({order['eta']}). "
            f"Tổng giá trị đơn hàng là {total}đ. "
            "Bạn cần mình hỗ trợ thêm gì không?"
        )
    return (
        "Mình chưa tìm thấy mã đơn hàng trong câu hỏi. "
        "Bạn vui lòng cho mình mã đơn (ví dụ A1001) để tra cứu nhé."
    )


def _messages(question: str, order_id: str | None, order: dict[str, Any] | None):
    if order and order_id:
        data = (
            f"Mã đơn: {order_id}\n"
            f"Trạng thái: {order['status']}\n"
            f"Dự kiến: {order['eta']}\n"
            f"Tổng tiền: {order['total']} VND"
        )
    else:
        data = "Không tìm thấy đơn hàng nào trong câu hỏi của khách."

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Dữ liệu đơn hàng:\n{data}\n\nCâu hỏi của khách: {question}",
        },
    ]


def _chunks(text: str, size: int = 4) -> Iterator[str]:
    """Chia câu trả lời thành từng cụm từ.

    Lab chia sau khi đã có câu trả lời để code dễ hiểu. Sản phẩm thật nên
    dùng `stream=True` của OpenAI để chữ hiện ra ngay khi model sinh.
    """
    words = text.split()
    for index in range(0, len(words), size):
        part = " ".join(words[index : index + size])
        if index + size < len(words):
            part += " "
        yield part


def _trace_url(langfuse, trace_id: str | None) -> str | None:
    """Tạo link tới trace, nhưng không bao giờ để lỗi mạng làm hỏng agent.

    Quan sát (observability) là phụ trợ. Nếu Langfuse chậm hoặc không
    truy cập được, người dùng vẫn phải nhận được câu trả lời bình thường.
    """
    if not trace_id:
        return None
    try:
        return langfuse.get_trace_url(trace_id=trace_id)
    except Exception:  # noqa: BLE001 - cố ý nuốt mọi lỗi của lớp tracing
        return None


def stream(
    question: str,
    *,
    user_id: str = "demo-user",
    session_id: str = "demo-session",
    chunk_delay: float = 0.0,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Chạy agent và phát ra từng sự kiện.

    Mỗi sự kiện là một cặp (loại, dữ liệu):
        ("step",  {...})  — một bước xử lý
        ("tool",  {...})  — một lần gọi tool
        ("delta", {...})  — một phần câu trả lời
        ("done",  {...})  — kết thúc, kèm metadata

    API ở buổi 2 chuyển các sự kiện này thành SSE. Nhờ vậy giao diện
    không phải chờ 10 giây rồi mới thấy gì đó.
    """
    started = time.perf_counter()
    langfuse = get_client()

    order_id = find_order_id(question)
    order: dict[str, Any] | None = None

    # Span gốc (root span) của cả lượt chạy. Mọi span con nằm bên trong.
    with langfuse.start_as_current_observation(
        as_type="agent",
        name="agent.support",
        input={"question": question},
    ) as root:
        # Các thuộc tính này gắn vào mọi observation bên trong:
        # lọc theo user, xem lại cả phiên chat, so sánh giữa các version.
        with propagate_attributes(
            trace_name="support-agent",
            user_id=user_id,
            session_id=session_id,
            version=settings.app_version,
            tags=["lab", f"model:{settings.openai_model}"],
        ):
            yield "step", {
                "name": STEP_CLASSIFY,
                "detail": {"order_id": order_id} if order_id else {"order_id": None},
            }

            if order_id:
                order = lookup_order(order_id)
                yield "tool", {
                    "name": STEP_LOOKUP,
                    "detail": {
                        "order_id": order_id,
                        "found": order is not None,
                    },
                }

            yield "step", {
                "name": STEP_LLM,
                "detail": {"model": settings.openai_model},
            }

            if settings.offline:
                answer = _offline_answer(order_id, order)
            else:
                answer = chat(_messages(question, order_id, order), name=STEP_LLM)

            for part in _chunks(answer):
                yield "delta", {"text": part}
                if chunk_delay:
                    time.sleep(chunk_delay)

            latency_ms = int((time.perf_counter() - started) * 1000)
            trace_id = langfuse.get_current_trace_id() if settings.tracing_enabled else None

            # Ghi input/output lên root span để mở trace là thấy ngay.
            if settings.tracing_enabled:
                root.update(output={"answer": answer})

            yield "done", {
                "order_id": order_id,
                "trace_id": trace_id,
                "trace_url": _trace_url(langfuse, trace_id),
                "latency_ms": latency_ms,
                "model": settings.openai_model,
                "prompt_fingerprint": prompt_fingerprint(),
                "offline": settings.offline,
            }


def run(
    question: str,
    *,
    user_id: str = "demo-user",
    session_id: str = "demo-session",
) -> AgentResult:
    """Chạy agent và gom sự kiện thành một kết quả duy nhất."""
    steps: list[dict[str, Any]] = []
    parts: list[str] = []
    done: dict[str, Any] = {}

    for event_type, data in stream(question, user_id=user_id, session_id=session_id):
        if event_type in {"step", "tool"}:
            steps.append({"type": event_type, **data})
        elif event_type == "delta":
            parts.append(data["text"])
        elif event_type == "done":
            done = data

    return AgentResult(answer="".join(parts).strip(), steps=steps, **done)
