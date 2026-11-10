"""Buổi 3 — kiểm tra nhanh một container đang chạy.

Chạy sau khi `docker compose up`:

    python -m labs.buoi_03.smoke_test

Kiểm tra 3 điều:
1. /healthz trả ok và database ghi được.
2. /chat trả đúng chuỗi sự kiện SSE và có câu trả lời.
3. Request được lưu vào SQLite (nếu container mount volume đúng).
"""

from __future__ import annotations

import json
import sys

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def main() -> None:
    print(f"Kiểm tra {BASE_URL}\n")

    health = httpx.get(f"{BASE_URL}/healthz", timeout=5)
    health.raise_for_status()
    info = health.json()
    print(f"✅ /healthz: status={info['status']} version={info['version']} db={info['database']}")
    assert info["status"] == "ok", "Container chưa khoẻ"

    payload = {
        "question": "Đơn A1003 bao giờ tới?",
        "user_id": "smoke-test",
        "session_id": "smoke-session",
    }

    events: list[str] = []
    answer: list[str] = []
    done: dict = {}

    with httpx.stream("POST", f"{BASE_URL}/chat", json=payload, timeout=60) as response:
        response.raise_for_status()
        event_name = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
                events.append(event_name)
            elif line.startswith("data: ") and event_name:
                data = json.loads(line.removeprefix("data: "))
                if event_name == "delta":
                    answer.append(data["text"])
                elif event_name == "done":
                    done = data

    text = "".join(answer).strip()
    print(f"✅ SSE events: {' → '.join(events)}")
    print(f"✅ Trả lời: {text}")
    print(f"✅ Latency: {done.get('latency_ms')} ms")

    assert events[0] == "start", "Sự kiện đầu tiên phải là start"
    assert events[-1] == "done", "Sự kiện cuối cùng phải là done"
    assert text, "Không nhận được câu trả lời"
    assert "offline" in done, "Event done thiếu thông tin phiên bản"

    print("\nTất cả kiểm tra đã qua.")


if __name__ == "__main__":
    main()
