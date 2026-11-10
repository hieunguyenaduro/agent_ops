# Lab buổi 3 — Docker và Docker Compose

## Mục tiêu

- Đóng gói Agent API thành image.
- Chạy bằng Docker Compose với biến môi trường và volume.
- Kiểm tra health check, log và tính bền vững của dữ liệu.

## Chuẩn bị

- Docker Desktop đang chạy.
- File `.env` ở thư mục gốc repo (sao chép từ `.env.example`).

## Chạy

Từ thư mục gốc repo:

```bash
docker compose -f labs/buoi_03/docker-compose.yml up --build
```

Lần đầu sẽ mất 1–2 phút để tải base image và cài thư viện. Các lần sau
nhanh hơn nhờ cache.

Kiểm tra:

```bash
python -m labs.buoi_03.smoke_test
```

Kết quả mong đợi:

```text
✅ /healthz: status=ok version=0.3.0 db=ok
✅ SSE events: start → step → tool → step → delta ... → done
✅ Trả lời: Đơn A1003 hiện có trạng thái: đang xử lý...
```

## Kiểm tra dữ liệu bền vững

```bash
docker compose -f labs/buoi_03/docker-compose.yml down
docker compose -f labs/buoi_03/docker-compose.yml up
python -m labs.buoi_03.smoke_test
```

Volume `agent-data` vẫn còn, nên lịch sử request vẫn còn.

```bash
# Xoá luôn dữ liệu — chỉ dùng khi muốn làm lại từ đầu
docker compose -f labs/buoi_03/docker-compose.yml down -v
```

## Xem container

```bash
docker ps
docker logs -f support-agent-lab-agent-1
docker inspect --format '{{.State.Health.Status}}' support-agent-lab-agent-1
```

## Lỗi thường gặp

| Lỗi | Cách sửa |
|---|---|
| `labs/common not found` | Build sai context — phải đứng ở thư mục gốc repo |
| `Cannot connect to the Docker daemon` | Mở Docker Desktop |
| `env file ... not found` | Chưa có `.env` ở thư mục gốc |
| Cổng 8000 bị chiếm | Đổi `"8001:8000"` trong compose |
| Sửa code mà không thấy đổi | Thêm `--build` khi `up` |

## Bài tập

Xem phần **Bài tập** trong [docs/buoi-03.md](../../docs/buoi-03.md#10-bài-tập).
