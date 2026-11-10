"""Một chỗ duy nhất để gọi model.

Vì sao cần gom về một hàm?
- Đổi model chỉ sửa một nơi.
- Mọi lời gọi đều đi qua Langfuse wrapper nên tự động có trace,
  token usage, cost và latency.
- Chế độ offline xử lý một lần, không rải `if` khắp agent.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .config import settings

_client: Any = None


def _openai_client():
    """Tạo OpenAI client một lần rồi dùng lại.

    `langfuse.openai.OpenAI` là bản thay thế trực tiếp (drop-in) cho
    `openai.OpenAI`: code giữ nguyên, nhưng mỗi lời gọi được ghi lại.
    """
    global _client
    if _client is None:
        from langfuse.openai import OpenAI

        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def chat(messages: list[dict[str, str]], *, name: str = "llm.chat") -> str:
    """Gửi messages tới model và trả về text.

    `name` là tên hiển thị của generation trong Langfuse, giúp đọc trace
    dễ hơn nhiều so với tên mặc định.
    """
    if settings.offline:
        return (
            "Mình đang chạy ở chế độ offline (chưa có OPENAI_API_KEY) nên "
            "không gọi được model. Phần tool tra cứu đơn hàng vẫn chạy thật."
        )

    response = _openai_client().chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0,
        name=name,
    )
    return (response.choices[0].message.content or "").strip()


@dataclass
class ChatResult:
    """Kết quả kèm số liệu vận hành, dùng cho buổi đo cost/latency."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    offline: bool

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def _estimate_tokens(text: str) -> int:
    """Ước lượng thô khi chạy offline: khoảng 4 ký tự một token.

    Chỉ dùng để lab có số liệu so sánh tương đối. Khi có key thật, luôn
    dùng con số `usage` do nhà cung cấp trả về.
    """
    return max(1, len(text) // 4)


def chat_full(
    messages: list[dict[str, str]],
    *,
    name: str = "llm.chat",
    max_tokens: int | None = None,
) -> ChatResult:
    """Như `chat()` nhưng trả thêm token, model và latency."""
    started = time.perf_counter()

    if settings.offline:
        prompt_text = " ".join(message["content"] for message in messages)
        # Câu trả lời cố định đủ ngắn để thấy rõ ảnh hưởng của max_tokens.
        text = (
            "Mình chưa gọi được model vì thiếu OPENAI_API_KEY. "
            "Đây là câu trả lời giả lập để đo luồng xử lý."
        )
        return ChatResult(
            text=text,
            model=settings.openai_model,
            input_tokens=_estimate_tokens(prompt_text),
            output_tokens=_estimate_tokens(text),
            latency_ms=int((time.perf_counter() - started) * 1000),
            offline=True,
        )

    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": 0,
        "name": name,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    response = _openai_client().chat.completions.create(**kwargs)
    usage = response.usage

    return ChatResult(
        text=(response.choices[0].message.content or "").strip(),
        model=settings.openai_model,
        input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
        output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        latency_ms=int((time.perf_counter() - started) * 1000),
        offline=False,
    )
