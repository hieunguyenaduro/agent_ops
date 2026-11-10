# Buổi 3 — Containerizing Agents with Docker

> **Học xong buổi này, bạn có thể:** viết Dockerfile cho một Agent API,
> giải thích vì sao image nhỏ và build nhanh, chạy cả hệ thống bằng Docker
> Compose, và biết dữ liệu nào sẽ mất khi container bị xoá.

## 1. Một câu để nhớ

**Image là công thức nấu ăn đóng hộp. Container là nồi đang nấu. Registry
là cái kho để gửi hộp công thức đi nơi khác.**

Công thức thì đứng yên. Nồi có thể bật, tắt, vứt đi và nấu lại bất cứ lúc
nào — và lần nào cũng ra đúng món đó.

Trước Docker, "chạy được trên máy tôi" là một câu vô nghĩa với người vận
hành. Docker biến câu đó thành một artifact cụ thể, có version, có thể
chuyển giao.

## 2. Container lifecycle

```text
Dockerfile ──build──► Image ──push──► Registry
                        │                │
                        └────pull────────┘
                              │
                           run ▼
                        Container ──stop──► (bị xoá, mọi thứ bên trong mất)
```

Bốn điều cần nhớ:

1. Image là **bất biến** (immutable). Muốn đổi, build image mới.
2. Container là một **process đang chạy**, không phải một cái máy ảo.
3. Container có filesystem riêng nhưng **dùng xong là mất**.
4. Cùng một image chạy được ở laptop, CI và cloud — đó là toàn bộ lợi ích.

## 3. Dockerfile: thứ tự lệnh quyết định tốc độ

Mỗi lệnh trong Dockerfile tạo một **layer**. Layer nào không đổi thì Docker
dùng lại cache.

```dockerfile
# ❌ Sai: sửa một dòng code là phải cài lại toàn bộ thư viện (vài phút).
COPY . .
RUN pip install -r requirements.txt
```

```dockerfile
# ✅ Đúng: thư viện chỉ cài lại khi requirements.txt đổi.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY labs/common ./labs/common
COPY labs/buoi_03/app.py ./app.py
```

Quy tắc: **thứ ít thay đổi đặt trước, thứ hay thay đổi đặt sau.**
`requirements.txt` đổi vài tuần một lần; code đổi vài phút một lần.

Ba lựa chọn nhỏ khác giúp image gọn và an toàn hơn:

| Lựa chọn | Lợi ích |
|---|---|
| `python:3.12-slim` thay vì `python:3.12` | Nhỏ hơn vài trăm MB |
| `PIP_NO_CACHE_DIR=1` | Không giữ file cài đặt tạm |
| `USER appuser` | Không chạy root trong container |

## 4. Bí mật không được nằm trong image

```dockerfile
# ❌ Sai: key bị bake vào image. Ai pull được image là thấy key.
ENV OPENAI_API_KEY=sk-proj-abc123...
```

```yaml
# ✅ Đúng: image không biết key. Lúc chạy mới đưa vào.
services:
  agent:
    env_file: ../../.env
```

Hai lớp bảo vệ:

1. `.dockerignore` chặn `.env` khỏi build context.
2. `.gitignore` chặn `.env` khỏi git.

Cả hai đều cần, vì chúng bảo vệ hai đường rò rỉ khác nhau.

> Quy tắc thực dụng: nếu một giá trị khác nhau giữa các môi trường, nó là
> cấu hình (biến môi trường). Nếu nó cho phép truy cập tài nguyên, nó là
> bí mật (secret manager khi lên cloud).

## 5. Networking và dữ liệu

**Networking:** trong Compose, các service gọi nhau bằng **tên service**,
không phải `localhost`.

```text
máy bạn ──localhost:8000──► [agent]  ──redis:6379──► [redis]
```

`localhost` bên trong container là chính container đó. Đây là lỗi kinh
điển khi chuyển từ chạy local sang Compose.

**Dữ liệu:** container có thể bị xoá bất cứ lúc nào. Mọi thứ cần giữ lại
phải nằm trên volume:

```yaml
volumes:
  - agent-data:/data
```

Trong lab, SQLite nằm ở `/data/agent.db`. Kiểm tra:

```bash
# Tạo vài request, rồi xoá container (volume vẫn còn)
docker compose -f labs/buoi_03/docker-compose.yml down
docker compose -f labs/buoi_03/docker-compose.yml up
# Lịch sử vẫn còn.

# Xoá luôn volume — dữ liệu mất thật.
docker compose -f labs/buoi_03/docker-compose.yml down -v
```

## 6. Health check và tắt một cách lịch sự

**Health check** trả lời: container còn phục vụ được không? Nó phải nhẹ,
không gọi model, không chạy job dài.

**Graceful shutdown** là phần ít người để ý nhưng gây lỗi thật:

```text
Cloud gửi SIGTERM
      │
      ├─ uvicorn ngừng nhận request mới
      ├─ đợi request đang chạy xong (tối đa 10–15s)
      ├─ đóng database, flush trace
      ▼
   process thoát
```

Nếu không có bước này, một request đang stream dở sẽ bị cắt giữa chừng mỗi
lần deploy. Trong lab:

```dockerfile
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000",
     "--timeout-graceful-shutdown", "10"]
```

```yaml
stop_grace_period: 15s
```

Con số 15 lớn hơn 10 để Docker còn thời gian chờ uvicorn tự đóng, thay vì
gửi SIGKILL ngay.

## 7. Đồng nhất local và production

Docker không tự động đảm bảo "giống hệt", nhưng nó loại bỏ phần lớn khác
biệt:

| Thứ có thể lệch | Cách kiểm soát |
|---|---|
| Phiên bản Python | Cố định trong base image |
| Phiên bản thư viện | Pin trong `requirements.txt` |
| Biến môi trường | `.env` local, secret manager trên cloud |
| Cổng, đường dẫn file | Cấu hình bằng biến, không hardcode |
| Quyền ghi file | Volume + user không phải root |

## 8. Lab — 30 phút

Từ **thư mục gốc repo** (build context phải là root vì image cần
`labs/common`):

```bash
# Cách 1: chỉ Docker
docker build -f labs/buoi_03/Dockerfile -t support-agent:0.3.0 .
docker run --rm -p 8000:8000 --env-file .env \
  -v agent-data:/data support-agent:0.3.0

# Cách 2: Docker Compose (khuyến nghị)
docker compose -f labs/buoi_03/docker-compose.yml up --build
```

Kiểm tra:

```bash
python -m labs.buoi_03.smoke_test
curl http://127.0.0.1:8000/healthz
```

Xem container có khoẻ không:

```bash
docker ps
docker inspect --format '{{.State.Health.Status}}' support-agent-lab-agent-1
docker logs -f support-agent-lab-agent-1
```

## 9. Lỗi thường gặp

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| `Cannot connect to the Docker daemon` | Chưa mở Docker Desktop |
| Build báo `labs/common not found` | Build sai context, phải đứng ở root |
| Container thoát ngay | Xem `docker logs`; thường thiếu biến môi trường |
| `permission denied` khi ghi `/data` | Volume chưa đúng quyền hoặc chạy sai user |
| Sửa code mà container không đổi | Chưa `--build`, đang dùng image cũ |

## 10. Bài tập

1. Đo dung lượng image trước và sau khi đổi base sang `slim`. Ghi lại số
   liệu — đây là thói quen tốt cho buổi 8.
2. Sửa một dòng trong `app.py`, build lại. Quan sát: layer nào được dùng
   cache, layer nào chạy lại?
3. Chạy `docker compose ... down` rồi `up` lại. Lịch sử request còn không?
   Thử `down -v` và giải thích kết quả.
4. Thêm biến `APP_VERSION=0.3.0` vào compose, kiểm tra `/healthz` trả đúng.

## 11. Tự kiểm tra

1. Vì sao `COPY requirements.txt` phải đứng trước `COPY . .`?
2. Nếu container bị xoá, dữ liệu nào mất? Thiết kế nào để không mất?
3. Mô tả điều gì xảy ra từ lúc cloud gửi SIGTERM đến khi container thoát.

## 12. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Câu hỏi: "Nếu đưa laptop cho đồng nghiệp, điều gì khiến app không chạy?" Liệt kê lên bảng. |
| 5–15 | Image / container / registry + lifecycle. So sánh với máy ảo để thấy container nhẹ hơn ở đâu. |
| 15–25 | Dockerfile: cho xem hai thứ tự lệnh, hỏi cái nào build nhanh hơn và vì sao. |
| 25–35 | Secrets, networking, volume. Nhấn mạnh: container là process, filesystem mất khi xoá. |
| 35–55 | Lab: build, compose up, chạy smoke test. Đi từng bàn xem `docker ps`. |
| 55–60 | Demo `down` rồi `up` (dữ liệu còn) và `down -v` (dữ liệu mất). |

**Bài học để nhớ:** "Chạy được trên máy tôi" chỉ là điểm xuất phát. Image
là thứ biến nó thành cam kết với người khác.
