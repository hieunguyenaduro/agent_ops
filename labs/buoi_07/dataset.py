"""Buổi 7 — dataset hồi quy và evaluator.

Dataset nhỏ, cố tình chứa vài trường hợp khó. Mục tiêu không phải "đủ mọi
câu hỏi", mà là **bắt được lỗi đã từng xảy ra** và không tái phát.

Quy ước:
    input           = {"order_id": ..., "question": ...}
    expected_output = danh sách từ khóa BẮT BUỘC phải có trong câu trả lời

Vì sao dùng từ khóa thay vì so khớp nguyên câu? Vì agent không
deterministic. Ta đánh giá **thông tin có mặt**, không đánh giá cách diễn đạt.
"""

from __future__ import annotations

from typing import Any

from langfuse import Evaluation

from labs.common.agent import ORDERS
from labs.common.config import settings
from labs.common.llm import chat

BASELINE_PROMPT = "Bạn là trợ lý chăm sóc khách hàng. Trả lời ngắn gọn."

CANDIDATE_PROMPT = (
    "Bạn là trợ lý chăm sóc khách hàng. Luôn nêu rõ mã đơn, trạng thái hiện "
    "tại và thời gian dự kiến. Trả lời ngắn gọn, thân thiện."
)

DATASET: list[dict[str, Any]] = [
    {
        "input": {"order_id": "A1001", "question": "Đơn A1001 bao giờ tới?"},
        "expected_output": ["A1001", "đang giao", "2 ngày"],
    },
    {
        "input": {"order_id": "A1002", "question": "A1002 giao chưa shop?"},
        "expected_output": ["A1002", "đã giao"],
    },
    {
        "input": {"order_id": "A1003", "question": "Đơn A1003 đang xử lý à?"},
        "expected_output": ["A1003", "đang xử lý", "3 ngày"],
    },
    {
        "input": {"order_id": "A1001", "question": "Tổng tiền đơn A1001 là bao nhiêu?"},
        "expected_output": ["A1001", "450.000"],
    },
    {
        "input": {"order_id": "A1002", "question": "Tôi muốn kiểm tra đơn A1002."},
        "expected_output": ["A1002", "đã giao", "1.290.000"],
    },
]


def _offline_answer(order_id: str, order: dict, system_prompt: str) -> str:
    """Câu trả lời mô phỏng khi không có OpenAI key.

    Prompt càng yêu cầu chi tiết thì câu trả lời càng đủ thông tin — nhờ
    vậy lab vẫn so sánh được baseline/candidate mà không cần gọi model.
    """
    if "trạng thái" not in system_prompt:
        return f"Đơn {order_id} đã được ghi nhận. Chúng tôi sẽ phản hồi sớm."

    total = f"{order['total']:,}".replace(",", ".")
    return (
        f"Đơn {order_id} hiện có trạng thái: {order['status']} "
        f"({order['eta']}). Tổng giá trị: {total}đ."
    )


def make_task(system_prompt: str):
    """Tạo hàm task cho một biến thể prompt."""

    def task(*, item, **kwargs) -> str:
        order_id = item["input"]["order_id"]
        question = item["input"]["question"]
        order = ORDERS[order_id]

        if settings.offline:
            return _offline_answer(order_id, order, system_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        return chat(messages, name="llm.eval")

    return task


def keyword_evaluator(
    *, input, output, expected_output, metadata=None, **kwargs
) -> Evaluation:
    """Đo tỉ lệ từ khóa bắt buộc có trong câu trả lời (0.0 → 1.0)."""
    keywords = expected_output or []
    text = (output or "").lower()
    hits = [keyword for keyword in keywords if keyword.lower() in text]
    value = len(hits) / len(keywords) if keywords else 0.0

    return Evaluation(
        name="keyword_match",
        value=round(value, 3),
        comment=f"{len(hits)}/{len(keywords)} từ khóa: {hits}",
    )


def average_score(result, name: str = "keyword_match") -> float:
    values = [
        evaluation.value
        for item in result.item_results
        for evaluation in item.evaluations
        if evaluation.name == name and isinstance(evaluation.value, (int, float))
    ]
    return sum(values) / len(values) if values else 0.0
