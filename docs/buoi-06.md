# Buổi 6 — Observability for Agent Systems

> **Học xong buổi này, bạn có thể:** đọc một sự cố từ log, tìm đúng trace,
> hiểu span nào chậm/lỗi/tốn tiền, và biết nên đặt alert ở đâu.

## 1. Một câu để nhớ

**Log là nhật ký sự kiện. Metric là đồng hồ đo. Trace là bản đồ đường đi.**

Khi khách báo "nó treo", bạn cần cả ba:

- Log cho biết **chuyện gì** đã xảy ra và lúc nào.
- Metric cho biết **bao nhiêu** request bị ảnh hưởng.
- Trace cho biết request đó **đi qua những bước nào** và tắc ở đâu.

Thiếu một trong ba, bạn sẽ đoán. Mà đoán trong production rất tốn kém.

## 2. Ba tín hiệu, ba câu hỏi

| Tín hiệu | Trả lời | Ví dụ trong agent |
|---|---|---|
| Log | Chuyện gì xảy ra? | `tool.timeout`, `chat.failed` |
| Metric | Bao nhiêu, nhanh hay chậm? | p95 latency, tỉ lệ lỗi, token/phút |
| Trace | Đi qua đâu, tắc ở bước nào? | `agent → tool → llm` với thời gian từng bước |

Điểm khác biệt khi làm agent: **một request có thể có 10–50 bước con**.
Log chỉ nói "request thất bại"; trace mới nói "thất bại vì tool thứ ba
timeout sau 2 giây, rồi agent thử lại hai lần".

## 3. Log có cấu trúc và correlation

Đừng log câu văn tự do:

```text
❌ 2026-12-04 09:58:03 ERROR gọi order-service lỗi
```

Hãy log JSON, mỗi dòng một sự kiện:

```json
{
  "ts": "2026-12-04T09:58:03.210Z",
  "level": "ERROR",
  "event": "tool.timeout",
  "request_id": "req-88a1",
  "trace_id": "7f3c9a1b2d4e",
  "message": "order-service quá 2s"
}
```

Hai khóa nối mọi thứ lại:

| Khóa | Nối cái gì với cái gì |
|---|---|
| `request_id` | Các dòng log của cùng một request HTTP |
| `trace_id` | Log của service ↔ trace của agent |

Nếu chỉ nhớ một điều từ buổi này: **hãy đảm bảo `trace_id` có trong log.**
Nó biến việc điều tra từ "đọc 10.000 dòng" thành "mở đúng một trace".

## 4. Một trace tốt trông như thế nào

```text
request.handle                    agent    1.8s
├── retrieve.policy               retriever 20ms
├── tool.lookup_order             tool      2.0s  ❌ ERROR timeout
└── llm.answer                    generation 1.2s  (120 in / 38 out, $0.0003)
```

Bốn thứ làm nên một trace dùng được:

1. **Tên nhất quán**: `tool.lookup_order`, `llm.answer` — không phải
   `step1`, `call_llm_final_v2`.
2. **Input/output**: đủ để hiểu quyết định, nhưng **không chứa dữ liệu
   nhạy cảm**. Che email, số điện thoại, số thẻ.
3. **Lỗi được đánh dấu**: `level=ERROR` + `status_message`, không chỉ nằm
   trong text output.
4. **Thuộc tính phiên bản**: `user_id`, `session_id`, `version`, tag
   `model:...`. Không có chúng, bạn không so sánh được giữa các bản.

## 5. Langfuse, OpenTelemetry và Grafana

Ba thứ này không cạnh tranh nhau — chúng ở ba tầng:

```text
Agent code
   │  OpenTelemetry (chuẩn chung)
   ├──────────────► Langfuse     (trace agent, prompt, cost, eval)
   └──────────────► Grafana/Tempo (hạ tầng: HTTP, DB, queue, service)
```

- **Langfuse** hiểu khái niệm agent: generation, token, cost, session,
  evaluation. Đây là nơi làm việc hằng ngày.
- **OpenTelemetry** là định dạng dây chung. Nhờ nó, cùng một span có thể
  đi nhiều nơi.
- **Grafana** mạnh về dashboard hạ tầng và alert. Nó không cần biết
  "prompt" là gì, nhưng rất giỏi trả lời "service này có khoẻ không".

Đừng cố dùng một công cụ cho cả ba. Hãy nối chúng bằng `trace_id`.

## 6. Dashboard và alert: cảnh báo theo triệu chứng

Alert tốt cảnh báo **điều người dùng cảm nhận**, không phải nguyên nhân
nội bộ:

| Nên alert | Không nên alert |
|---|---|
| Tỉ lệ lỗi 5xx > 2% trong 5 phút | CPU > 70% |
| p95 latency > 10s trong 10 phút | Một span cụ thể chậm |
| Cost/giờ vượt 150% baseline | Số token tăng |
| Tỉ lệ eval giảm dưới ngưỡng sau release | Prompt đổi |

Dashboard tối thiểu nên có bốn khối:

1. **Traffic**: request/phút, số session.
2. **Lỗi**: 5xx, lỗi tool, lỗi model (401/429/timeout).
3. **Latency**: p50/p95/p99, tách theo bước (LLM vs tool).
4. **Cost**: token và tiền theo giờ, theo model, theo user.

## 7. Điều tra một request lỗi — theo đúng thứ tự

Kịch bản trong lab: khách báo request bị treo. Ta có log của service.

```text
Bước 1  Alert hoặc báo cáo        "p95 tăng, có lỗi 5xx"
Bước 2  Lọc log theo thời gian    tìm event ERROR gần nhất
Bước 3  Lấy trace_id từ log       req-88a1 → 7f3c9a1b2d4e
Bước 4  Mở trace                  xem span nào đỏ, mất bao lâu
Bước 5  Đọc span lỗi              tool.lookup_order timeout 2s
Bước 6  Đối chiếu version         lỗi xuất hiện từ bản nào?
Bước 7  Hành động                 rollback / tăng timeout / sửa tool
Bước 8  Xác minh                  cùng câu hỏi, trace mới không còn lỗi
```

Câu hỏi quan trọng ở bước 6: **cùng lỗi này có xảy ra ở bản trước không?**
Nếu không, rollback là hành động rẻ nhất. Nếu có, đó là lỗi hệ thống, cần
sửa gốc.

## 8. Lab — 30 phút

Phần 1 — tạo trace thủ công:

```bash
python -m labs.buoi_06.trace_manual
```

Mở trace trên Langfuse (nếu đã cấu hình key), tìm span đỏ và đọc
`status_message`.

Phần 2 — truy vết từ log:

```bash
python -m labs.buoi_06.correlate_logs
python -m labs.buoi_06.correlate_logs --trace-id 2a9d4c7e1f00
```

Thử trả lời: request nào lỗi, lỗi ở bước nào, mất bao lâu, cùng user có
request nào khác không?

## 9. Bài tập

1. Thêm một span `guardrail.check` vào `trace_manual.py`, đánh dấu
   `WARNING` khi câu hỏi chứa từ "hoàn tiền". Xem nó nằm ở đâu trong cây.
2. Viết script đọc `sample_logs.jsonl`, tính p95 latency từ các dòng
   `chat.end`. So sánh với cảm nhận "chậm" của người dùng.
3. Thêm `request_id` vào mọi log của API buổi 2 (đã có) và thử tìm một
   request chỉ bằng `grep`.
4. Che dữ liệu nhạy cảm: sửa `trace_manual.py` để input chỉ còn 4 số cuối
   của mã đơn. Giải thích vì sao vẫn đủ để debug.

## 10. Tự kiểm tra

1. Khi nào dùng log, khi nào dùng trace? Cho một ví dụ cần cả hai.
2. Vì sao alert theo CPU thường không hữu ích bằng alert theo p95?
3. Một trace có `trace_id` nhưng log không có. Thiếu bước nào?

## 11. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Kể một sự cố thật: "khách báo treo, bạn có 10 phút". Hỏi: mở gì trước? |
| 5–15 | Ba tín hiệu + correlation id. Vẽ sơ đồ log → trace. |
| 15–25 | Cấu trúc một trace tốt; span type, input/output, version, lỗi. |
| 25–35 | Langfuse vs OTel vs Grafana; alert theo triệu chứng. |
| 35–55 | Lab: chạy `correlate_logs`, tìm trace, mở trace thủ công. |
| 55–60 | Chốt: "không có trace_id trong log thì chưa gọi là observability". |

**Bài tập nhóm:** đưa mỗi nhóm một trace lỗi (ảnh chụp hoặc dữ liệu mẫu),
yêu cầu viết 5 dòng: triệu chứng, trace id, span lỗi, giả thuyết, hành động.
