# Lab buổi 2 — FastAPI + SSE

## Mục tiêu

- Bọc agent thành HTTP API.
- Stream tiến trình và câu trả lời bằng SSE.
- Thấy `request_id`, `session_id` và `trace_id` nối với nhau trong log.

## Chạy

Terminal 1 — server:

```bash
uvicorn labs.buoi_02.app:app --reload
```

Terminal 2 — client:

```bash
python -m labs.buoi_02.client_demo
```

Đổi cổng nếu 8000 bận:

```bash
uvicorn labs.buoi_02.app:app --port 8011
python -m labs.buoi_02.client_demo http://127.0.0.1:8011
```

## Kết quả mong đợi

```text
→ POST http://127.0.0.1:8000/chat

[    80 ms] start      request=995313edda58
[    80 ms] step       step.find_order_id {'order_id': 'A1002'}
[    80 ms] tool       tool.lookup_order {'order_id': 'A1002', 'found': True}
[    80 ms] step       llm.answer {'model': 'gpt-4.1-mini'}
Đơn A1002 hiện có trạng thái: đã giao...
[   250 ms] done       latency=170 ms
```

## Thử bằng curl

```bash
curl -N -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Đơn A1001 bao giờ tới?","user_id":"u1","session_id":"s1"}'
```

`-N` rất quan trọng: không có nó, curl buffer toàn bộ và bạn tưởng SSE
không chạy.

## Xem tài liệu API

Mở http://127.0.0.1:8000/docs — FastAPI tự sinh Swagger UI từ Pydantic model.

## Bài tập

Xem phần **Bài tập** trong [docs/buoi-02.md](../../docs/buoi-02.md#9-bài-tập).
