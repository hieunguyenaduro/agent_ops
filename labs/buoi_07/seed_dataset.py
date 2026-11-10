"""Buổi 7 — đưa dataset lên Langfuse để dùng chung và version hóa.

Chạy khi đã cấu hình key:

    python -m labs.buoi_07.seed_dataset

Sau khi chạy, dataset xuất hiện trong mục Datasets của project. Từ đó có
thể chạy experiment từ UI hoặc từ CI, và so sánh giữa các lần release.
"""

from __future__ import annotations

from langfuse import get_client

from labs.buoi_07.dataset import DATASET
from labs.common.config import settings

DATASET_NAME = "support-agent-regression"


def main() -> None:
    if not settings.tracing_enabled:
        raise SystemExit(
            "Cần LANGFUSE_PUBLIC_KEY và LANGFUSE_SECRET_KEY trong .env.\n"
            "Không có key thì dùng dataset local trong dataset.py — lab vẫn chạy."
        )

    client = get_client()
    client.create_dataset(
        name=DATASET_NAME,
        description="Câu hỏi hồi quy cho trợ lý đơn hàng",
    )

    for item in DATASET:
        client.create_dataset_item(
            dataset_name=DATASET_NAME,
            input=item["input"],
            expected_output=item["expected_output"],
        )

    client.flush()
    print(f"✅ Đã tạo dataset '{DATASET_NAME}' với {len(DATASET)} mẫu.")
    print("Mở Langfuse → Datasets để xem và chạy experiment.")


if __name__ == "__main__":
    main()
