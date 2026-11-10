"""Buổi 8 — đo và so sánh cost/latency giữa hai cấu hình.

Chạy:

    python -m labs.buoi_08.measure

Hai biến thể:
    baseline  — system prompt dài, max_tokens rộng
    optimized — prompt ngắn, max_tokens vừa đủ

Mục tiêu không phải "dùng prompt ngắn là tốt". Mục tiêu là thấy **cùng một
tác vụ, hai cấu hình cho ra chi phí và độ trễ khác nhau** — và phải đo
trước khi tối ưu.
"""

from __future__ import annotations

from dataclasses import dataclass

from labs.common.config import settings
from labs.common.llm import ChatResult, chat_full

# Giá minh họa cho gpt-4.1-mini, USD trên 1 triệu token.
# Giá thay đổi theo thời gian — luôn kiểm tra bảng giá hiện hành khi tính thật.
PRICE_INPUT_PER_M = 0.40
PRICE_OUTPUT_PER_M = 1.60

BASELINE_PROMPT = """Bạn là trợ lý chăm sóc khách hàng của một cửa hàng online.
Hãy luôn thân thiện, lịch sự, kiên nhẫn và chuyên nghiệp trong mọi câu trả lời.
Khi khách hỏi về đơn hàng, hãy giải thích rõ quy trình xử lý đơn hàng của shop:
đơn được tiếp nhận, đóng gói, bàn giao cho đơn vị vận chuyển, và giao đến khách.
Nếu khách hỏi về chính sách đổi trả, hãy nhắc rằng shop hỗ trợ đổi trả trong vòng
7 ngày kể từ ngày nhận hàng, với điều kiện sản phẩm còn nguyên tem mác.
Nếu khách hỏi về phí vận chuyển, hãy nói rằng phí được tính theo địa chỉ giao hàng
và hiển thị rõ ở bước thanh toán. Luôn kết thúc bằng một lời cảm ơn chân thành
và lời chúc tốt đẹp. Trả lời ngắn gọn nhưng đầy đủ thông tin cần thiết.
"""

OPTIMIZED_PROMPT = (
    "Trợ lý đơn hàng. Trả lời ngắn, nêu mã đơn, trạng thái, thời gian dự kiến."
)

QUESTIONS = [
    "Đơn A1001 bao giờ tới?",
    "Đơn A1002 đã giao chưa?",
    "Đơn A1003 đang xử lý à?",
]


@dataclass
class Summary:
    label: str
    input_tokens: float
    output_tokens: float
    latency_ms: float
    cost_usd: float


def cost_of(result: ChatResult) -> float:
    return (
        result.input_tokens / 1_000_000 * PRICE_INPUT_PER_M
        + result.output_tokens / 1_000_000 * PRICE_OUTPUT_PER_M
    )


def run_variant(label: str, system_prompt: str, max_tokens: int) -> Summary:
    results = []
    for question in QUESTIONS:
        result = chat_full(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            name=f"llm.{label}",
            max_tokens=max_tokens,
        )
        results.append(result)

    count = len(results)
    return Summary(
        label=label,
        input_tokens=sum(r.input_tokens for r in results) / count,
        output_tokens=sum(r.output_tokens for r in results) / count,
        latency_ms=sum(r.latency_ms for r in results) / count,
        cost_usd=sum(cost_of(r) for r in results),
    )


def main() -> None:
    print(f"Model: {settings.openai_model} | offline={settings.offline}\n")

    baseline = run_variant("baseline", BASELINE_PROMPT, max_tokens=500)
    optimized = run_variant("optimized", OPTIMIZED_PROMPT, max_tokens=120)

    print(f"{'':<12}{'in tok':>8}{'out tok':>9}{'latency':>15}{'cost 3 req':>13}")
    for summary in (baseline, optimized):
        # Offline không gọi model nên không có latency thật. In "n/a" thay vì
        # "0ms" để không tạo cảm giác sai rằng model trả lời tức thì.
        latency = "n/a (offline)" if settings.offline else f"{summary.latency_ms:.0f}ms"
        print(
            f"{summary.label:<12}"
            f"{summary.input_tokens:>8.0f}"
            f"{summary.output_tokens:>9.0f}"
            f"{latency:>15}"
            f"{summary.cost_usd:>13.6f}$"
        )

    token_saving = 1 - (
        optimized.input_tokens + optimized.output_tokens
    ) / (baseline.input_tokens + baseline.output_tokens)
    print(f"\nGiảm token: {token_saving:.0%}")

    if settings.offline:
        print(
            "\nĐang offline: token được ước lượng từ độ dài văn bản.\n"
            "Điền OPENAI_API_KEY để có số liệu thật từ usage của model."
        )


if __name__ == "__main__":
    main()
