"""Buổi 8 — cache tầng ứng dụng: thứ rẻ nhất là thứ không phải gọi lại.

Chạy:

    python -m labs.buoi_08.cache_demo

Kịch bản: nhiều khách hỏi cùng một câu, hoặc cùng một câu hỏi được gửi lại
do người dùng bấm nút hai lần. Cache exact-match (sau khi chuẩn hóa) xử lý
được phần lớn các trường hợp này mà không cần hạ tầng phức tạp.

Lưu ý: cache theo *câu hỏi* chỉ an toàn khi câu trả lời không phụ thuộc
người dùng. Nếu có dữ liệu riêng của từng người, khóa cache phải gồm
user_id — hoặc không cache.
"""

from __future__ import annotations

import re

from labs.common.config import settings
from labs.common.llm import chat_full

QUESTIONS = [
    "Đơn A1001 bao giờ tới?",
    "đơn   a1001 BAO GIỜ tới?",
    "Đơn A1002 đã giao chưa?",
    "Đơn A1001 bao giờ tới?",
    "Đơn A1003 đang xử lý à?",
    "ĐƠN A1003 ĐANG XỬ LÝ À?",
]

CACHE: dict[str, str] = {}


def normalize(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def answer(question: str) -> tuple[str, bool]:
    key = normalize(question)
    if key in CACHE:
        return CACHE[key], True

    result = chat_full(
        [
            {"role": "system", "content": "Trả lời ngắn gọn về đơn hàng."},
            {"role": "user", "content": question},
        ],
        name="llm.cache_demo",
    )
    CACHE[key] = result.text
    return result.text, False


def main() -> None:
    hits = 0
    total_tokens = 0

    print(f"{'câu hỏi':<32}{'cache':<8}{'token':>7}")
    for question in QUESTIONS:
        text, hit = answer(question)
        tokens = len(text) // 4  # ước lượng để so sánh tương đối
        total_tokens += 0 if hit else tokens
        hits += 1 if hit else 0
        print(f"{question[:31]:<32}{'HIT' if hit else 'MISS':<8}{tokens:>7}")

    hit_rate = hits / len(QUESTIONS)
    print(f"\nSố câu: {len(QUESTIONS)} | cache hit: {hits} | tỉ lệ: {hit_rate:.0%}")
    print(f"Token phải trả cho model: {total_tokens} (ước lượng)")

    if settings.offline:
        print("\nĐang offline: câu trả lời là mẫu, nhưng cách cache vẫn chạy thật.")
    print(
        "\nBài học: chuẩn hóa khóa (lowercase, gộp khoảng trắng) tăng hit rate\n"
        "mà không cần thêm hạ tầng. Nhưng đừng cache dữ liệu riêng của user."
    )


if __name__ == "__main__":
    main()
