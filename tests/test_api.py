"""Test cho HTTP API: health check, validate input, và SSE."""

from __future__ import annotations

from fastapi.testclient import TestClient

from labs.buoi_02.app import app


def test_healthz():
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.5.0"


def test_chat_tra_ve_chuoi_su_kien():
    payload = {
        "question": "Đơn A1002 đã giao chưa?",
        "user_id": "test-user",
        "session_id": "test-session",
    }

    with TestClient(app) as client:
        with client.stream("POST", "/chat", json=payload) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            body = "".join(response.iter_text())

    assert "event: start" in body
    assert "event: tool" in body
    assert "event: delta" in body
    assert "event: done" in body
    assert "A1002" in body


def test_chat_tu_choi_cau_hoi_rong():
    with TestClient(app) as client:
        response = client.post("/chat", json={"question": "", "user_id": "u"})

    # Pydantic chặn trước khi agent kịp chạy — đúng loại lỗi nên trả 422.
    assert response.status_code == 422


def test_chat_gioi_han_do_dai_cau_hoi():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"question": "x" * 2_001, "user_id": "u"},
        )

    assert response.status_code == 422
