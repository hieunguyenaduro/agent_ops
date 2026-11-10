# Buổi 2 — Serving an Agent with FastAPI

> **Học xong buổi này, bạn có thể:** bọc agent thành một HTTP API, stream
> tiến trình về giao diện bằng SSE, tách dữ liệu giữa các người dùng, và
> đọc log để biết một request đã đi qua đâu.

## 1. Một câu để nhớ

API là **quầy lễ tân** của agent. Khách không được phép đi thẳng vào bếp.
Lễ tân nhận yêu cầu, kiểm tra giấy tờ, ghi sổ, rồi báo tiến độ qua loa.

Nếu không có quầy lễ tân, ai cũng gọi thẳng vào model: không kiểm soát được
chi phí, không biết ai đang dùng, không tách được dữ liệu, và một người
làm sập là tất cả cùng sập.

## 2. Ôn lại agent harness — chỉ mức cần cho vận hành

Agent = một vòng lặp có "tay chân":

```text
câu hỏi ──► [ model quyết định ] ──► gọi tool ──► [ quan sát kết quả ]
                    ▲                                      │
                    └──────────── lặp tới khi xong ◄───────┘
```

Khi vận hành, ta quan tâm bốn thứ **nhìn thấy được từ bên ngoài**:

| Thành phần | Câu hỏi vận hành |
|---|---|
| Model call | Tốn bao nhiêu token, mất bao lâu? |
| Tool call | Gọi tool nào, tham số gì, tool lỗi không? |
| Vòng lặp | Có bị lặp vô hạn hay dừng quá sớm không? |
| State | Request này thuộc user nào, phiên nào? |

## 3. Hợp đồng API tối thiểu

```http
GET  /healthz        → {"status": "ok", ...}
POST /chat           → text/event-stream
```

Request:

```json
{
  "question": "Đơn A1002 của tôi đã giao chưa?",
  "user_id": "u-123",
  "session_id": "s-456"
}
```

Vì sao cần `user_id` và `session_id` ngay từ đầu?

- `user_id`: giới hạn quyền, tính chi phí theo người, lọc trace khi điều tra.
- `session_id`: gom nhiều lượt chat thành một cuộc trò chuyện. Cùng một
  người có thể có nhiều phiên; cùng một phiên có thể kéo dài qua nhiều request.

**Không** để server tự đoán hai giá trị này từ IP hay cookie. Client phải
gửi rõ ràng, còn server phải kiểm tra và giới hạn độ dài.

## 4. SSE: báo tiến độ thay vì bắt khách chờ

Agent chạy 5–30 giây. Nếu trả JSON một lần, người dùng thấy màn hình trắng
rồi đột ngột có kết quả — giống gọi tổng đài mà không có nhạc chờ.

SSE (Server-Sent Events) là một **dòng chảy một chiều từ server xuống
client**, định dạng chỉ gồm text:

```text
event: start
data: {"request_id":"a1b2","session_id":"s-456"}

event: tool
data: {"name":"tool.lookup_order","detail":{"order_id":"A1002","found":true}}

event: delta
data: {"text":"Đơn A1002 hiện có trạng thái: "}

event: done
data: {"latency_ms":1830,"trace_url":"https://cloud.langfuse.com/trace/..."}
```

Mỗi sự kiện cách nhau **một dòng trống**. Hai dòng `:` bắt đầu bằng dấu
hai chấm là comment/heartbeat, dùng để giữ kết nối sống khi agent im lặng.

Các event trong lab:

| Event | Khi nào | Nội dung |
|---|---|---|
| `start` | Ngay khi nhận request | `request_id`, `session_id` |
| `step` | Chuyển sang bước mới | tên bước, tham số ngắn |
| `tool` | Gọi tool xong | tool nào, tìm thấy dữ liệu không |
| `delta` | Có thêm chữ | một cụm từ của câu trả lời |
| `done` | Kết thúc | latency, trace URL, fingerprint |
| `error` | Có lỗi giữa chừng | thông báo thân thiện, `request_id` |

**SSE hay WebSocket?** SSE nhẹ hơn, tự động reconnect, đi qua proxy dễ hơn,
và đúng nhu cầu: server nói, client nghe. WebSocket chỉ cần khi client cũng
phải gửi liên tục trong lúc agent chạy.

## 5. Tách dữ liệu giữa các người dùng

Quy tắc: **không có state toàn cục trong request path.**

```python
# ❌ Sai: hai người dùng ghi chung một chỗ, người này thấy đơn của người kia.
CURRENT_USER = {"id": None}
CURRENT_ORDER = {}

@app.post("/chat")
def chat(req):
    CURRENT_USER["id"] = req.user_id
    ...
```

```python
# ✅ Đúng: mọi thứ thuộc request nằm trong biến cục bộ của request đó.
@app.post("/chat")
def chat(payload: ChatRequest):
    request_id = uuid.uuid4().hex[:12]   # riêng cho request này
    session_id = payload.session_id or f"sess-{request_id}"
    ...
```

Nếu cần lưu state dài hạn (giỏ hàng, lịch sử), lưu theo khóa
`(user_id, session_id)` trong database — không giữ trong biến toàn cục của
process, vì process có thể bị restart hoặc chạy thành nhiều bản sao.

## 6. Lỗi: HTTP status không cứu được SSE

Vấn đề: khi bắt đầu stream, server đã trả `200 OK`. Nếu lỗi xảy ra ở giây
thứ 8, không thể đổi thành `500` nữa.

Cách xử lý đúng:

1. Bọc phần sinh sự kiện trong `try/except`.
2. Gửi `event: error` với thông báo **không lộ chi tiết nội bộ**.
3. Ghi log đầy đủ kèm `request_id` để điều tra.
4. Luôn kết thúc generator — đừng để client treo.

```python
try:
    for event_type, data in stream(...):
        yield sse(event_type, data)
except Exception:
    log.exception("chat.failed request_id=%s", request_id)
    yield sse("error", {"request_id": request_id,
                        "message": "Agent đang gặp sự cố. Vui lòng thử lại."})
```

Ngoài ra, client phải có timeout. Server phải có giới hạn thời gian chạy
cho agent. Một request treo không được phép treo cả service.

## 7. Health check và log

**Health check** phải nhẹ và nhanh:

```python
@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": settings.app_version}
```

Đừng gọi model trong health check. Nếu model chậm, orchestrator tưởng
container chết và restart liên tục — sự cố nhỏ thành sự cố lớn.

**Log nên có cấu trúc**, mỗi dòng một JSON, để máy đọc được:

```json
{"event":"chat.start","request_id":"a1b2","user_id":"u-123","session_id":"s-456"}
{"event":"chat.end","request_id":"a1b2","trace_id":"7f3c...","duration_ms":1830}
```

Hai khóa quan trọng nhất:

- `request_id`: nối các dòng log của cùng một request.
- `trace_id`: nối log của service với trace của agent trên Langfuse.

Có hai khóa này, khi khách báo "hôm qua tôi hỏi mà nó trả lời sai", bạn tìm
được đúng request trong vài giây thay vì đọc hàng nghìn dòng log.

### Một chi tiết nhỏ trong code

Trong `app.py` có `preserve_context(events())`. Starlette có thể gọi từng
bước của generator trên các thread khác nhau. OpenTelemetry giữ context
theo thread, nên một span mở ở thread này mà đóng ở thread khác sẽ báo
`Failed to detach context`, và trace có thể mất quan hệ cha–con.

`preserve_context` giữ nguyên context cho cả vòng đời generator. Bạn không
cần viết lại đoạn này — chỉ cần biết vì sao nó tồn tại, để không vô tình
xoá mất khi refactor.

## 8. Lab — 25 phút

Terminal 1:

```bash
uvicorn labs.buoi_02.app:app --reload
```

Terminal 2:

```bash
python -m labs.buoi_02.client_demo
```

Bạn sẽ thấy các event hiện dần, câu trả lời chạy ra từng cụm từ, và cuối
cùng là `done` kèm latency.

Thử thêm bằng `curl`:

```bash
curl -N -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Đơn A1001 bao giờ tới?","user_id":"u1","session_id":"s1"}'
```

`-N` tắt buffer của curl — nếu không, bạn sẽ thấy tất cả sự kiện hiện ra
cùng lúc và tưởng SSE không hoạt động.

## 9. Bài tập

1. Thêm một event `heartbeat` mỗi 5 giây khi agent chưa xong. Gợi ý: dùng
   generator + `time.sleep`, hoặc tách agent sang thread.
2. Chạy hai `client_demo` cùng lúc với hai `user_id` khác nhau. Kiểm tra
   log có `request_id` riêng và không lẫn dữ liệu.
3. Đặt `chunk_delay=0` trong `stream()`. Latency thay đổi thế nào? Trải
   nghiệm người dùng thay đổi thế nào?
4. Thêm giới hạn: nếu câu hỏi dài quá 500 ký tự, trả lỗi 422 ngay từ
   Pydantic thay vì để agent xử lý.

## 10. Tự kiểm tra

1. Vì sao không thể trả `500` khi lỗi xảy ra giữa một stream SSE?
2. `user_id` và `session_id` khác nhau ở đâu? Cho một ví dụ cần cả hai.
3. Health check gọi model có lợi hay có hại? Vì sao?

## 11. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Demo: gọi một API trả JSON sau 15 giây. Hỏi: "Trong 15 giây đó người dùng thấy gì?" |
| 5–15 | Agent harness ở mức vận hành + hợp đồng API. Nhấn mạnh `user_id`/`session_id` phải do client gửi. |
| 15–25 | SSE: cho xem raw text của một event, rồi so sánh với JSON một cục. |
| 25–30 | Lỗi giữa stream, health check, log có cấu trúc. |
| 30–50 | Lab: hai terminal, chạy client, mở log server. Yêu cầu học viên chỉ ra `request_id` của request vừa rồi. |
| 50–60 | Thử phá: tắt server giữa lúc stream; sửa để client báo lỗi tử tế. |

**Mẹo demo:** chạy `curl -N` và `curl` (không `-N`) cạnh nhau. Cả lớp sẽ
thấy ngay buffer ảnh hưởng thế nào đến trải nghiệm.
