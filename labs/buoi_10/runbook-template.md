# Runbook — Support Agent

> Mẫu để điền. Giữ ngắn: người trực lúc 2 giờ sáng không đọc văn dài.
> Mỗi mục phải trả lời được: **làm gì, ở đâu, bằng lệnh nào**.

## Thông tin dịch vụ

| Trường | Giá trị |
|---|---|
| Tên service | support-agent |
| Môi trường | production |
| Region | asia-southeast1 |
| Dashboard | <link> |
| Trace | <link Langfuse> |
| Log | <link Cloud Logging> |
| Repo | <link> |
| On-call chính | <tên> — <kênh> |
| On-call phụ | <tên> — <kênh> |

## Mức độ sự cố

| Mức | Nghĩa | Ví dụ | Phản hồi |
|---|---|---|---|
| SEV1 | Không dùng được | 100% request lỗi | Ngay, gọi người |
| SEV2 | Suy giảm nặng | p95 > 30s, lỗi > 10% | Trong 15 phút |
| SEV3 | Suy giảm nhẹ | một tool lỗi, có fallback | Trong 1 giờ |
| SEV4 | Không ảnh hưởng người dùng | alert nhiễu | Ngày làm việc |

## 5 phút đầu tiên

1. **Xác nhận** sự cố có thật: gọi `/healthz`, gửi một câu hỏi thử.
2. **Khoanh vùng**: lỗi ở API, model, tool, hàng đợi, hay database?
3. **Lấy một trace**: tìm `trace_id` trong log của request lỗi.
4. **Chọn hành động rẻ nhất**: rollback > tắt tính năng > sửa nóng.
5. **Thông báo**: ai bị ảnh hưởng, đang làm gì, khi nào cập nhật tiếp.

Không cố sửa gốc trong 5 phút đầu. Mục tiêu là **giảm ảnh hưởng**.

## Sự cố thường gặp

### Model trả 401 / 403

```text
Dấu hiệu : tất cả request lỗi auth, health vẫn ok
Kiểm tra : secret có bị xoay/ xoá? key còn hạn?
Hành động: cập nhật secret, restart revision
Xác minh : một request thử trả lời bình thường
```

### Model trả 429 (rate limit)

```text
Dấu hiệu : lỗi tăng theo giờ cao điểm, message có "rate limit"
Kiểm tra : token/phút so với quota; có vòng lặp retry không jitter?
Hành động: giảm concurrency, bật backoff, tạm hạ model nhỏ hơn
Xác minh : 429 giảm, p95 trở lại baseline
```

### Tool tra cứu đơn hàng chết

```text
Dấu hiệu : trace có span tool.lookup_order đỏ, agent trả lời xin lỗi
Kiểm tra : health của order-service; timeout cấu hình
Hành động: tăng timeout có kiểm soát HOẶC bật fallback trả lời "chưa tra được"
Xác minh : không còn 5xx; người dùng vẫn nhận câu trả lời lịch sự
```

### Hàng đợi tồn đọng

```text
Dấu hiệu : queued tăng liên tục, tuổi job lâu nhất tăng
Kiểm tra : worker còn sống? dead letter có tăng? provider chậm?
Hành động: scale worker, tạm dừng nhận job mới, xử lý dead letter
Xác minh : tuổi job lâu nhất giảm
```

### Chi phí tăng bất thường

```text
Dấu hiệu : cost/giờ > 150% baseline
Kiểm tra : model đổi? prompt phải? vòng lặp tool? một user bất thường?
Hành động: rate limit theo user, hạ max_tokens, tạm chặn user bất thường
Xác minh : cost/giờ về baseline trong 30 phút
```

### Bản deploy mới có vấn đề

```text
Dấu hiệu : lỗi hoặc latency tăng ngay sau deploy
Kiểm tra : revision mới bắt đầu từ lúc nào? lỗi có từ bản trước không?
Hành động: chuyển 100% traffic về revision cũ
Xác minh : chỉ số về mức trước deploy
```

## Rollback

```bash
# 1. Xem revision và thời điểm tạo
gcloud run revisions list \
  --service support-agent \
  --region asia-southeast1

# 2. Chuyển toàn bộ traffic về revision tốt gần nhất
gcloud run services update-traffic support-agent \
  --region asia-southeast1 \
  --to-revisions support-agent-00004-old=100

# 3. Xác minh
curl -fsS https://<service-url>/healthz
python -m labs.buoi_04.preflight --url https://<service-url> --strict
```

Điều kiện: image cũ còn trong registry, database tương thích ngược, secret
cũ vẫn còn. Nếu đã xoá một trong ba, rollback sẽ không cứu được.

## Kill switch

Cách tắt agent mà không cần deploy (chọn cách đã cài đặt):

- Đặt biến `AGENT_ENABLED=false` và restart revision.
- Hoặc chặn ở gateway/feature flag, trả về "tạm bảo trì".
- Hoặc hạ `max-instances=0` (thô nhưng hiệu quả tức thì).

Ghi lại cách nào đã dùng và ai có quyền bật/tắt.

## Truyền thông

Mẫu cập nhật mỗi 15 phút:

```text
[Support Agent] Cập nhật lúc <giờ>
Ảnh hưởng: <ai, bao nhiêu>
Đang làm: <hành động>
Tiếp theo: <mốc thời gian>
Người phụ trách: <tên>
```

Sau khi ổn định: thông báo rõ "đã khắc phục", thời gian kéo dài, và mục
postmortem (không đổ lỗi).

## Sau sự cố

1. Viết timeline: phát hiện → hành động → phục hồi (mốc thời gian thật).
2. Tìm **nguyên nhân gốc** bằng 5 câu hỏi "vì sao", không dừng ở "ai".
3. Ghi hành động khắc phục có **người** và **hạn**.
4. Thêm một ca vào dataset hồi quy nếu sự cố liên quan chất lượng.
5. Cập nhật runbook này — nếu lần sau vẫn phải đoán, runbook chưa đủ tốt.
