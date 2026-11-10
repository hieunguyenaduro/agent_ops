# Lab buổi 9 — Durable Execution

## Mục tiêu

- Hiểu vì sao agent cần hàng đợi thay vì chạy trong request HTTP.
- Thấy tận mắt lease, crash và phục hồi.
- Biết retry, dead letter và idempotency khác nhau ở đâu.

## Chạy

```bash
python -m labs.buoi_09.demo
```

Kết quả mong đợi:

```text
5 câu hỏi → 5 job
Bấm lại cùng key → id giống: 5e2ed61d7ce5
ban đầu                     queued=5 | running=0 | done=0 | dead=0

[worker-a] ... ✅ xong sau 0ms (lần thử 1)
[worker-a] ... ✅ xong sau 0ms (lần thử 1)
💥 worker worker-a chết khi đang xử lý ...
sau crash                   queued=2 | running=1 | done=2 | dead=0

[worker-b] ... ✅ xong sau 0ms (lần thử 2)
...
sau khi worker B chạy       queued=0 | running=0 | done=5 | dead=0
```

Ba điều cần chú ý trong output:

1. Job bị crash có `attempts=2` — nó được xử lý lại, không bị mất.
2. Các job khác vẫn `attempts=1` — không có chuyện làm lại tất cả.
3. Job lỗi ba lần chuyển sang `dead`, không lặp vô hạn.

## Thử phá

```bash
# Chạy demo nhiều lần
python -m labs.buoi_09.demo

# Xem test mô tả hành vi
pytest -q tests/test_queue.py
```

Sau đó sửa thử:

1. Đổi `lease_seconds=0.5` thành `5`. Demo sẽ chờ bao lâu? Vì sao worker B
   không nhận được job ngay?
2. Đổi `max_attempts=1`. Job crash có được cứu không?
3. Bỏ `idempotency_key` khi enqueue. Bấm nút hai lần tạo bao nhiêu job?

## Khi nào dùng hàng đợi

| Dùng hàng đợi | Giữ đồng bộ |
|---|---|
| Việc > 5–10 giây | Việc < 1 giây |
| Cần chịu lỗi khi deploy/restart | Không quan trọng mất một request |
| Có thể trả kết quả sau (email, báo cáo) | Người dùng đang chờ kết quả |
| Cần retry tự động | Lỗi là vĩnh viễn |

Agent thường thuộc nhóm đầu: một câu hỏi phức tạp có thể gọi model 5–10
lần, dễ vượt timeout của load balancer.

## Đọc thêm

- [docs/buoi-09.md](../../docs/buoi-09.md) — bài giảng đầy đủ.
- `labs/buoi_09/store.py` — hợp đồng trạng thái, lease, retry.
- `labs/buoi_09/worker.py` — vòng lặp claim → làm → complete.
