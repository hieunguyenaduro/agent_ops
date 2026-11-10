"""Buổi 8 — gọi tool song song để giảm latency.

Chạy:

    python -m labs.buoi_08.parallel_tools

Ba tool độc lập, mỗi tool mất 0.4 giây. Gọi tuần tự mất ~1.2 giây; gọi
song song chỉ còn ~0.4 giây. Đây là món "free lunch" hiếm hoi của tối ưu
latency: không đổi chất lượng, không đổi model, chỉ đổi cách chờ.

Điều kiện an toàn: các tool không phụ thuộc kết quả của nhau và có thể
chạy đồng thời mà không tranh chấp tài nguyên.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor


def fetch_order(order_id: str) -> dict:
    time.sleep(0.4)
    return {"order_id": order_id, "status": "đang giao"}


def fetch_shipping(order_id: str) -> dict:
    time.sleep(0.4)
    return {"order_id": order_id, "eta": "2 ngày"}


def fetch_policy(order_id: str) -> dict:
    time.sleep(0.4)
    return {"order_id": order_id, "refund": "trong 7 ngày"}


def sequential(order_id: str) -> list[dict]:
    return [
        fetch_order(order_id),
        fetch_shipping(order_id),
        fetch_policy(order_id),
    ]


def parallel(order_id: str) -> list[dict]:
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(fetch_order, order_id),
            pool.submit(fetch_shipping, order_id),
            pool.submit(fetch_policy, order_id),
        ]
        return [future.result() for future in futures]


def timed(label: str, fn) -> float:
    started = time.perf_counter()
    result = fn("A1001")
    duration = time.perf_counter() - started
    print(f"{label:<12}{duration:>6.2f}s  {len(result)} kết quả")
    return duration


def main() -> None:
    print("Ba tool độc lập, mỗi tool 0.4s\n")
    seq = timed("tuần tự", sequential)
    par = timed("song song", parallel)
    print(f"\nNhanh hơn: {seq / par:.1f}×")

    print(
        "\nLưu ý: chỉ song song hóa khi các tool thật sự độc lập.\n"
        "Nếu tool sau cần kết quả tool trước, phải giữ tuần tự."
    )


if __name__ == "__main__":
    main()
