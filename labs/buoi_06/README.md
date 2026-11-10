# Lab buổi 6 — Observability

## Mục tiêu

- Tạo trace thủ công với span lồng nhau, lỗi và token usage.
- Truy một request lỗi từ log tới trace.
- Biết đọc span nào chậm, lỗi, tốn tiền.

## Chạy

```bash
python -m labs.buoi_06.trace_manual
python -m labs.buoi_06.correlate_logs
```

Xem trace của một request cụ thể:

```bash
python -m labs.buoi_06.correlate_logs --trace-id 2a9d4c7e1f00
```

## Kết quả mong đợi

`trace_manual` in câu trả lời và (nếu có key) link trace với 4 span:
`request.handle`, `retrieve.policy`, `tool.lookup_order`,
`llm.answer`.

`correlate_logs` in timeline của request lỗi:

```text
   2026-12-04T09:58:01.180Z  tool.start     tool.lookup_order order=A1001
❌ 2026-12-04T09:58:03.210Z  tool.timeout   order-service quá 2s
❌ 2026-12-04T09:58:03.260Z  chat.failed    agent trả về lỗi cho người dùng
```

## Trên Langfuse

Mở trace `manual-trace` và thử:

1. Bấm vào span đỏ — đọc `status_message`.
2. Mở tab Session `session-9` — thấy các request của cùng người dùng.
3. Lọc theo tag `buoi-06`.
4. So sánh `llm.answer` với một trace thật từ buổi 2 (có usage do SDK tự ghi).

## Bài tập

Xem phần **Bài tập** trong [docs/buoi-06.md](../../docs/buoi-06.md#9-bài-tập).
