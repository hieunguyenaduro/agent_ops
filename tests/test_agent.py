"""Test cho lõi agent — không gọi mạng, không cần key."""

from __future__ import annotations

from labs.common.agent import find_order_id, prompt_fingerprint, run


def test_find_order_id_tim_dung_ma():
    assert find_order_id("Đơn A1001 tới đâu rồi?") == "A1001"
    assert find_order_id("đơn a1002") == "A1002"


def test_find_order_id_khong_co_ma():
    assert find_order_id("Xin chào, shop ơi") is None
    assert find_order_id("Mã 12345 không đúng định dạng") is None


def test_run_tra_cuu_duoc_don_hang():
    result = run("Đơn A1001 bao giờ tới?", user_id="test", session_id="s1")

    assert "A1001" in result.answer
    assert result.order_id == "A1001"
    assert [step["name"] for step in result.steps] == [
        "step.find_order_id",
        "tool.lookup_order",
        "llm.answer",
    ]


def test_run_khi_khong_co_ma_don():
    result = run("Shop ơi, tôi muốn hỏi chút", user_id="test", session_id="s2")

    assert result.order_id is None
    assert "mã đơn" in result.answer.lower()


def test_prompt_fingerprint_on_dinh():
    # Cùng cấu hình thì fingerprint phải giống nhau — đây là nền tảng
    # để so sánh giữa các lần chạy.
    assert prompt_fingerprint() == prompt_fingerprint()
    assert len(prompt_fingerprint()) == 12
