"""Buổi 2 — client terminal để xem SSE chạy.

Chạy (sau khi đã bật server ở terminal khác):

    python -m labs.buoi_02.client_demo

Client in ra từng sự kiện ngay khi nhận được, kèm mốc thời gian, để
thấy rõ: chữ hiện dần chứ không phải chờ một cục.
"""

from __future__ import annotations

import json
import os
import sys
import time

import httpx

# Cho phép đổi địa chỉ khi chạy: python -m labs.buoi_02.client_demo http://127.0.0.1:8011
BASE_URL = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.getenv("AGENT_URL", "http://127.0.0.1:8000")
)
URL = f"{BASE_URL.rstrip('/')}/chat"

PAYLOAD = {
    "question": "Đơn A1002 của tôi đã giao chưa?",
    "user_id": "demo-user",
    "session_id": "demo-session-01",
}


def main() -> None:
    started = time.perf_counter()
    print(f"→ POST {URL}\n")

    answer = []

    with httpx.stream("POST", URL, json=PAYLOAD, timeout=60) as response:
        response.raise_for_status()

        event_name = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            elif line.startswith("data: ") and event_name:
                data = json.loads(line.removeprefix("data: "))
                elapsed = (time.perf_counter() - started) * 1000

                if event_name == "delta":
                    # In ngay, không xuống dòng, để thấy chữ chạy ra.
                    print(data["text"], end="", flush=True)
                    answer.append(data["text"])
                elif event_name == "start":
                    print(f"[{elapsed:6.0f} ms] start      request={data['request_id']}")
                elif event_name == "step":
                    print(f"[{elapsed:6.0f} ms] step       {data['name']} {data['detail']}")
                elif event_name == "tool":
                    print(f"[{elapsed:6.0f} ms] tool       {data['name']} {data['detail']}")
                elif event_name == "done":
                    print(f"\n[{elapsed:6.0f} ms] done       latency={data['latency_ms']} ms")
                    if data.get("trace_url"):
                        print(f"                  trace: {data['trace_url']}")
                elif event_name == "error":
                    print(f"\n[{elapsed:6.0f} ms] LỖI        {data['message']}")


if __name__ == "__main__":
    main()
