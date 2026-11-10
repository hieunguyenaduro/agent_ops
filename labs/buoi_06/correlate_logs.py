"""Buổi 6 — truy một request lỗi từ log tới trace.

Chạy:

    python -m labs.buoi_06.correlate_logs
    python -m labs.buoi_06.correlate_logs --trace-id 7f3c9a1b

Kịch bản: khách báo "hôm qua tôi hỏi mà nó treo". Ta chỉ có log của
service. Mục tiêu là tìm đúng request, rồi lấy trace_id để mở trace
bên Langfuse.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

LOG_FILE = Path(__file__).with_name("sample_logs.jsonl")


def load_logs() -> list[dict]:
    return [
        json.loads(line)
        for line in LOG_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def find_failed_trace(logs: list[dict]) -> str:
    for entry in logs:
        if entry.get("level") == "ERROR":
            return entry["trace_id"]
    raise SystemExit("Không tìm thấy lỗi nào trong log.")


def timeline(trace_id: str, logs: list[dict]) -> None:
    entries = [entry for entry in logs if entry.get("trace_id") == trace_id]
    if not entries:
        raise SystemExit(f"Không có dòng log nào với trace_id={trace_id}")

    print(f"\nCác dòng log của trace {trace_id}:\n")
    for entry in entries:
        marker = "❌" if entry.get("level") == "ERROR" else "  "
        print(
            f"{marker} {entry['ts']}  {entry['event']:<14} "
            f"{entry.get('message', '')}"
        )

    request_id = entries[0].get("request_id")
    print(f"\n→ request_id: {request_id}")
    print(f"→ trace_id  : {trace_id}")
    print(
        "\nBước tiếp theo: mở trace này trên Langfuse, xem span lỗi nằm ở đâu,\n"
        "rồi đối chiếu với release/version ghi trên trace."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-id", help="Trace cần xem; bỏ trống để tự tìm lỗi")
    args = parser.parse_args()

    logs = load_logs()
    trace_id = args.trace_id or find_failed_trace(logs)
    timeline(trace_id, logs)


if __name__ == "__main__":
    main()
