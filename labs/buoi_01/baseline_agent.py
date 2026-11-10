"""Buổi 1 — chạy agent baseline và gửi một trace lên Langfuse.

Chạy từ thư mục gốc repo:

    python -m labs.buoi_01.baseline_agent

Đây là "bản chụp" để các buổi sau so sánh: cùng câu hỏi, cùng model,
cùng prompt. Khi tối ưu cost/latency ở buổi 8, ta quay lại đúng câu hỏi
này để biết mình đã tốt lên hay xấu đi.
"""

from __future__ import annotations

from langfuse import get_client

from labs.common.agent import run
from labs.common.config import settings

QUESTION = "Đơn A1001 của tôi bao giờ thì tới?"


def main() -> None:
    result = run(QUESTION, user_id="demo-user", session_id="buoi-01-baseline")

    print("\n=== KẾT QUẢ ===")
    print(f"Câu hỏi : {QUESTION}")
    print(f"Trả lời : {result.answer}")

    print("\n=== CÁC BƯỚC ĐÃ CHẠY ===")
    for step in result.steps:
        print(f"  - {step['name']}: {step['detail']}")

    print("\n=== THÔNG TIN PHIÊN BẢN ===")
    print(f"Model             : {result.model}")
    print(f"App version       : {settings.app_version}")
    print(f"Prompt fingerprint: {result.prompt_fingerprint}")
    print(f"Latency           : {result.latency_ms} ms")
    print(f"Offline           : {result.offline}")

    if result.trace_url:
        print(f"\nTrace trên Langfuse: {result.trace_url}")
        print("Mở link này để thấy cây span: agent.support → tool.lookup_order → llm.answer")
    else:
        print(
            "\nChưa có trace. Kiểm tra LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY "
            "trong .env và kết nối mạng."
        )

    # SDK gửi trace bất đồng bộ. Lệnh ngắn phải flush, nếu không
    # chương trình kết thúc trước khi trace kịp bay lên server.
    get_client().flush()


if __name__ == "__main__":
    main()
