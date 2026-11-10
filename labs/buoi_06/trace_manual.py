"""Buổi 6 — trace thủ công: tự tạo span cho từng bước của agent.

Chạy:

    python -m labs.buoi_06.trace_manual

Bài này không gọi model thật. Mục đích là thấy cách "nhìn vào bên trong"
một pipeline: mỗi bước là một span, có input, output, thời gian, lỗi và
usage. Khi dùng OpenAI wrapper, SDK tự làm việc này; còn với provider
khác hoặc tool nội bộ, bạn phải tự tạo span như ở đây.
"""

from __future__ import annotations

import time

from langfuse import get_client, propagate_attributes

from labs.common.config import settings

QUESTION = "Đơn A1001 bị chậm, có được hoàn tiền không?"


def _trace_url(trace_id: str | None) -> str | None:
    if not trace_id or not settings.tracing_enabled:
        return None
    try:
        return get_client().get_trace_url(trace_id=trace_id)
    except Exception:  # noqa: BLE001 - tracing không được làm hỏng luồng chính
        return None


def run_pipeline() -> dict:
    langfuse = get_client()

    with langfuse.start_as_current_observation(
        as_type="agent",
        name="request.handle",
        input={"question": QUESTION},
        metadata={"environment": "lab"},
    ) as root:
        with propagate_attributes(
            trace_name="manual-trace",
            user_id="user-42",
            session_id="session-9",
            version=settings.app_version,
            tags=["buoi-06", "manual"],
        ):
            # 1. Bước retrieval: tra chính sách. Span loại "retriever".
            with langfuse.start_as_current_observation(
                as_type="retriever",
                name="retrieve.policy",
                input={"query": "hoàn tiền khi giao chậm"},
            ) as retrieval:
                time.sleep(0.02)
                retrieval.update(
                    output={"documents": ["policy-return-v2"], "count": 1}
                )

            # 2. Bước tool: gọi hệ thống đơn hàng. Cố tình lỗi để thấy
            #    một span ERROR trông thế nào trên giao diện.
            with langfuse.start_as_current_observation(
                as_type="tool",
                name="tool.lookup_order",
                input={"order_id": "A1001"},
            ) as tool:
                time.sleep(0.01)
                tool.update(
                    output={"error": "upstream timeout"},
                    level="ERROR",
                    status_message="order-service không phản hồi sau 2s",
                )

            # 3. Bước generation: bình thường SDK tự tạo khi gọi model.
            #    Ở đây tạo thủ công để thấy đầy đủ các trường.
            with langfuse.start_as_current_observation(
                as_type="generation",
                name="llm.answer",
                model=settings.openai_model,
                input=[{"role": "user", "content": QUESTION}],
            ) as generation:
                time.sleep(0.05)
                answer = (
                    "Đơn A1001 đang giao chậm. Theo chính sách, bạn được hoàn "
                    "phí vận chuyển nếu giao quá 5 ngày."
                )
                generation.update(
                    output=answer,
                    usage_details={"input_tokens": 120, "output_tokens": 38},
                    model_parameters={"temperature": 0, "max_tokens": 300},
                )

            root.update(output={"answer": answer})

    # Đảm bảo trace được gửi đi trước khi chương trình kết thúc.
    langfuse.flush()
    return {
        "answer": answer,
        "trace_id": langfuse.get_current_trace_id() if settings.tracing_enabled else None,
    }


def main() -> None:
    result = run_pipeline()
    print(f"Câu hỏi : {QUESTION}")
    print(f"Trả lời : {result['answer']}")

    if not settings.tracing_enabled:
        print("\nChưa cấu hình Langfuse — trace không được gửi đi.")
        print("Span vẫn được tạo trong process, nhưng không có nơi để xem.")
        return

    url = _trace_url(result["trace_id"])
    print(f"\nTrace: {url or result['trace_id']}")
    print(
        "\nMở trace và để ý:\n"
        "  - retrieve.policy : 20ms\n"
        "  - tool.lookup_order : màu đỏ, có status message\n"
        "  - llm.answer : có token usage để tính cost\n"
        "  - tab Session: cả cuộc trò chuyện của user-42"
    )


if __name__ == "__main__":
    main()
