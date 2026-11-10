# Buổi 9 — Durable Execution & Background Jobs

> **Học xong buổi này, bạn có thể:** chuyển một agent chạy trong request
> HTTP sang hàng đợi bền vững, hiểu lease/retry/dead letter, và biết vì sao
> "at-least-once" buộc mọi tác dụng phụ phải idempotent.

## 1. Một câu để nhớ

**Request HTTP là lời hứa 30 giây. Agent thì có thể cần 5 phút.**

Nếu bạn giữ người dùng chờ trong lúc agent suy nghĩ, ba chuyện sẽ xảy ra:
load balancer cắt kết nối, container restart giữa chừng, và không ai biết
việc đang làm đã xong hay chưa. Hàng đợi giải quyết cả ba.

## 2. Đồng bộ vs bất đồng bộ

```text
Đồng bộ (buổi 2)
client ──► API ──► agent ──► model ──► trả lời
             │
             └── giữ kết nối suốt 10–30s; chết là mất việc

Bất đồng bộ (buổi 9)
client ──► API ──► queue ──► 202 + job_id
                              │
                              ▼
                          worker ──► agent ──► kết quả vào DB
client ──► GET /jobs/{id} ──► trạng thái/kết quả
```

Đổi lại, người dùng không nhận câu trả lời ngay. Vì vậy chỉ dùng cách này
khi sản phẩm chấp nhận được: gửi email, tạo báo cáo, xử lý tài liệu, hoặc
chat có thông báo khi xong.

## 3. Trạng thái của một job

Năm trạng thái, đủ cho hầu hết hệ thống:

```text
        enqueue
           │
           ▼
       ┌────────┐  claim   ┌─────────┐  complete  ┌──────┐
       │ queued │ ───────► │ running │ ─────────► │ done │
       └────────┘          └─────────┘            └──────┘
           ▲                   │
           │                   │ fail (còn lượt)
           └───────────────────┘
                               │ fail (hết lượt)
                               ▼
                            ┌──────┐
                            │ dead │
                            └──────┘
```

Điều quan trọng không phải tên gọi, mà là **mỗi lần chuyển trạng thái được
ghi xuống đĩa**. Nếu trạng thái chỉ nằm trong RAM, restart là mất.

## 4. Lease: cách phát hiện worker đã chết

Worker không "báo chết" khi bị kill. Vì vậy hệ thống dùng **lease**:

```text
worker A claim job 42  →  status=running, lease_until = now + 30s
worker A chết          →  không ai ghi gì thêm
30 giây sau            →  worker B thấy lease hết hạn, nhận lại job 42
```

Chọn lease ngắn hay dài:

| Lease | Được | Mất |
|---|---|---|
| Ngắn (10s) | Phục hồi nhanh | Job dài bị nhận lại khi vẫn đang chạy → làm trùng |
| Dài (5 phút) | Ít làm trùng | Job chết phải chờ lâu mới được cứu |

Cách tốt hơn lease cố định: **heartbeat** — worker gia hạn lease định kỳ
khi còn làm việc. Job chết không heartbeat, lease hết hạn tự nhiên.

## 5. At-least-once và idempotency

Hệ thống này đảm bảo job được xử lý **ít nhất một lần**, không phải đúng
một lần. Lý do: worker có thể chết **sau khi** gửi email nhưng **trước khi**
ghi `done`. Lần sau job chạy lại và gửi email lần hai.

```text
claim → gọi model → gửi email → 💥 chết trước khi complete
                              │
                              ▼
                     lần sau: gọi model → gửi email lần 2
```

Vì vậy mọi tác dụng phụ phải **idempotent** — làm nhiều lần cho kết quả
như làm một lần:

| Tác dụng phụ | Cách idempotent |
|---|---|
| Gửi email | Dùng `job_id` làm khóa; downstream bỏ qua nếu đã gửi |
| Trừ tiền | Idempotency key trong API thanh toán |
| Ghi database | `INSERT ... ON CONFLICT DO NOTHING` |
| Gọi webhook | Kèm `event_id`, bên nhận dedupe |

Còn **idempotency key lúc enqueue** giải quyết vấn đề khác: người dùng bấm
nút hai lần. Khóa do client gửi, server trả cùng `job_id` cho cả hai lần.

> Hai khái niệm dễ lẫn: idempotency key **đầu vào** chống tạo job trùng;
> idempotent **đầu ra** chống tác dụng phụ trùng. Cần cả hai.

## 6. Retry: lỗi nào nên thử lại

Không phải lỗi nào cũng đáng retry:

| Lỗi | Retry? | Vì sao |
|---|---|---|
| Timeout mạng | Có | Tạm thời |
| 429 rate limit | Có, có backoff | Chờ quota hồi |
| 500/503 từ provider | Có | Tạm thời |
| 401 sai key | Không | Retry chỉ tốn thời gian |
| 400 request sai | Không | Sửa code, không sửa số lần |
| Nội dung vi phạm policy | Không | Lặp lại vẫn vi phạm |

Backoff nên tăng dần và có jitter:

```text
lần 1: 1s   lần 2: 2s   lần 3: 4s   (+ ngẫu nhiên 0–1s)
```

Không có jitter, hàng nghìn job cùng retry một lúc sẽ đánh sập provider
vừa hồi phục — "thundering herd".

## 7. Dead letter: nơi lỗi được nhìn thấy

Job hết lượt thử không nên biến mất. Nó vào `dead` để:

1. **Alert**: `dead > 0` là tín hiệu có người cần xem.
2. **Điều tra**: giữ `error`, `attempts`, input gốc.
3. **Requeue** sau khi sửa nguyên nhân — không chạy lại mù.

Nếu bạn xoá job lỗi để "cho sạch dashboard", bạn đang xoá bằng chứng.

## 8. Backpressure: bảo vệ hệ thống khi việc đến nhanh hơn xử lý

Ba cách, tăng dần độ phức tạp:

| Cách | Khi nào |
|---|---|
| Giới hạn độ dài hàng đợi | Luôn nên có; trả 429 khi đầy |
| Scale worker theo độ dài queue | Việc tăng theo giờ/chiến dịch |
| Ưu tiên + rate limit theo user | Nhiều khách, một số dùng quá nhiều |

Điều không nên làm: để hàng đợi phình vô hạn. Nó không làm chậm ngay, nhưng
biến mọi sự cố nhỏ thành sự cố lớn vì phải xử lý tồn đọng nhiều giờ.

## 9. Từ SQLite tới production

Lab dùng SQLite để bạn thấy toàn bộ hợp đồng trong một file đọc được. Khi
lên production:

| Thành phần | Thay bằng | Giữ nguyên |
|---|---|---|
| SQLite | Postgres / Redis / SQS | Trạng thái, lease, attempts |
| Vòng lặp worker | Celery, RQ, Cloud Tasks, Temporal | claim → làm → complete |
| Lease thủ công | Visibility timeout / heartbeat | Khái niệm lease |
| `dead` table | Dead letter queue | Alert + requeue |

Nếu công việc có nhiều bước dài và cần checkpoint (ví dụ agent chờ người
duyệt), cân nhắc **durable workflow engine** như Temporal. Nó làm sẵn
việc lưu lịch sử bước, nhưng thêm khái niệm và hạ tầng phải học.

## 10. Human-in-the-loop

Một biến thể rất thực tế: job dừng ở trạng thái `waiting_approval`.

```text
running → waiting_approval → (người duyệt) → queued → running → done
```

Điều cần làm đúng: lưu **toàn bộ ngữ cảnh** tại điểm dừng (câu hỏi, câu trả
lời nháp, trace id), để người duyệt thấy đủ thông tin và worker có thể tiếp
tục mà không chạy lại từ đầu.

## 11. Lab — 30 phút

```bash
python -m labs.buoi_09.demo
pytest -q tests/test_queue.py
```

Trong demo, tìm:

1. Job nào có `attempts=2`? Vì sao chỉ job đó?
2. Sau crash, `queued` và `running` bằng bao nhiêu? Vì sao không phải 0?
3. Job lỗi chuyển `dead` ở lần thứ mấy? Vì sao không phải lần thứ tư?

## 12. Bài tập

1. Đổi `lease_seconds` thành 5 giây. Demo chờ bao lâu? Viết 2 câu giải
   thích đánh đổi giữa lease ngắn và dài.
2. Thêm trạng thái `waiting_approval` và một hàm `approve(job_id)`. Demo
   luồng: job dừng, in nháp, gọi `approve`, worker chạy tiếp.
3. Viết `requeue_dead(store)` đưa mọi job `dead` về `queued` và reset
   `attempts=0`. Vì sao phải reset attempts?
4. Thêm backoff: khi `fail`, ghi `next_run_at = now + 2**attempts`. Sửa
   `claim` để bỏ qua job chưa tới giờ. Thử với 3 job lỗi.
5. Mô tả bằng lời: nếu worker chết **sau khi** trừ tiền thành công nhưng
   **trước khi** ghi `done`, hệ thống thanh toán phải làm gì để không trừ
   hai lần?

## 13. Tự kiểm tra

1. Vì sao lease hết hạn lại là cách phát hiện worker chết, thay vì chờ
   worker báo lỗi?
2. At-least-once khác exactly-once ở đâu, và tại sao exactly-once khó?
3. Idempotency key lúc enqueue khác idempotent tác dụng phụ như thế nào?

## 14. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Hỏi: "Deploy giữa lúc agent đang trả lời thì sao?" |
| 5–15 | Sync vs async; sơ đồ 5 trạng thái; vì sao ghi trạng thái xuống đĩa. |
| 15–25 | Lease, heartbeat; at-least-once và idempotency. Kể ví dụ trừ tiền hai lần. |
| 25–35 | Retry/backoff/jitter; dead letter; backpressure. |
| 35–55 | Lab: chạy demo, tìm job `attempts=2`, làm bài tập 1–2. |
| 55–60 | Chốt: "hệ thống bền không phải hệ thống không chết, mà là hệ thống biết mình đang ở đâu sau khi chết". |

**Demo gây ấn tượng:** chạy demo, dừng ở phần crash, mở DB bằng
`sqlite3` cho cả lớp xem job `running` với lease. Sau đó chạy tiếp và cho
thấy job được cứu — không cần thao tác tay nào.
