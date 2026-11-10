# Phụ lục — Cài Langfuse trong 5 phút

Langfuse là nơi lưu **trace**: mỗi lượt agent chạy được ghi lại thành một
cây các bước, kèm prompt, output, token, cost và thời gian. Không có nó,
bạn chỉ có log rời rạc và phải đoán.

## 1. Tạo project

1. Vào [cloud.langfuse.com](https://cloud.langfuse.com) (EU) hoặc
   [us.cloud.langfuse.com](https://us.cloud.langfuse.com) (US), đăng ký.
2. Tạo organization → project, ví dụ `agent-ops-lab`.
3. Vào **Settings → API Keys → Create new API key**.
4. Sao chép **Public Key** (`pk-lf-...`) và **Secret Key** (`sk-lf-...`).
   Secret key chỉ hiện một lần.

## 2. Điền vào `.env`

```dotenv
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Kiểm tra nhanh:

```bash
python -m labs.buoi_01.check_env
```

Ba dòng `LANGFUSE_*` phải có dấu ✅.

## 3. Chạy một trace đầu tiên

```bash
python -m labs.buoi_01.baseline_agent
```

Cuối output có dòng `Trace trên Langfuse: https://.../trace/...`.
Mở link, bạn sẽ thấy:

```text
agent.support
├── tool.lookup_order
└── llm.answer
```

Bấm vào `llm.answer` để xem prompt đầu vào, câu trả lời, model, token và cost.
Bấm vào `agent.support` để xem `user_id`, `session_id`, `version` và tag.

## 4. Đọc trace như dân vận hành

| Bạn cần biết | Xem ở đâu |
|---|---|
| Request này chậm ở đâu? | Độ dài các thanh thời gian trong cây span |
| Tốn bao nhiêu? | Token + cost ở generation |
| Tool nào hay lỗi? | Lọc theo tên `tool.*`, xem status/error |
| Một người dùng hỏi gì? | Lọc theo `user_id` |
| Cả cuộc trò chuyện? | Mở `session_id` |
| Bản nào tạo ra kết quả này? | `version` và tag `model:...` |

## 5. Vì sao đôi khi không thấy trace?

| Triệu chứng | Kiểm tra |
|---|---|
| Không có dòng "Trace trên Langfuse" | Thiếu key trong `.env`, hoặc chưa load `.env` |
| Có link nhưng mở ra 404 | Sai `LANGFUSE_HOST` (EU/US) hoặc sai project |
| Chạy script xong mất trace | Thiếu `langfuse.flush()` ở cuối chương trình ngắn |
| Trace có nhưng thiếu span con | Span con được tạo ngoài context của span cha |
| Trace cũ hiện chậm | API đọc có độ trễ; trace mới vẫn ghi nhận |

## 6. Một lưu ý về phiên bản

Lab dùng **Langfuse Python SDK v5** (dựa trên OpenTelemetry). SDK này cần
Langfuse Cloud hoặc self-host **v4.59.0 trở lên**. Nếu bạn dùng bản self-host
cũ hơn, hãy nâng cấp server hoặc cài `langfuse>=4,<5`.

Các ví dụ cũ trên mạng thường dùng `langfuse.trace()`, `langfuse.span()`
hoặc `langfuse_context.update_current_trace()`. Những API đó đã bị bỏ.
Cách viết hiện tại:

```python
from langfuse import get_client, observe, propagate_attributes

langfuse = get_client()

@observe(name="agent.support")
def run(question: str, user_id: str):
    with propagate_attributes(user_id=user_id, session_id="s-1", version="0.1.0"):
        ...
```

## 7. Quan hệ với OpenTelemetry

Langfuse SDK nói chuyện bằng OpenTelemetry. Nghĩa là sau này bạn có thể gửi
cùng dữ liệu sang Grafana/Jaeger mà không phải instrument lại. Buổi 6 sẽ
nói kỹ phần này; hôm nay chỉ cần nhớ: **trace là chuẩn chung, Langfuse là
một nơi để xem nó.**
