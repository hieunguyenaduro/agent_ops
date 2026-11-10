# Checklist trước khi mở cho người dùng thật

Điền tên người chịu trách nhiệm cho từng mục. Mục nào chưa có tên thì
chưa được coi là xong — kể cả khi kỹ thuật đã làm.

## 1. Danh tính và quyền

| Mục | Người chịu trách nhiệm | Bằng chứng |
|---|---|---|
| Có service account riêng cho agent | <điền tên> | tên SA, role tối thiểu |
| Bí mật nằm trong Secret Manager, không trong image | <điền tên> | ảnh chụp cấu hình |
| Không có key trong repo/git history | <điền tên> | kết quả quét |
| Quyền truy cập production có danh sách rõ ràng | <điền tên> | danh sách |

## 2. Vận hành

| Mục | Người chịu trách nhiệm | Bằng chứng |
|---|---|---|
| On-call có tên và kênh liên lạc | <điền tên> | lịch trực |
| `/healthz` kiểm tra version và database | <điền tên> | output |
| Có **rollback** đã tập ít nhất một lần | <điền tên> | thời gian rollback |
| Có **kill switch** tắt agent mà không cần deploy | <điền tên> | cách bật/tắt |
| Giới hạn `max-instances` và ngân sách tháng | <điền tên> | cấu hình |

## 3. Observability

| Mục | Người chịu trách nhiệm | Bằng chứng |
|---|---|---|
| Log có `request_id` và `trace_id` | <điền tên> | một dòng log mẫu |
| Dashboard có traffic / lỗi / p95 / cost | <điền tên> | link dashboard |
| Alert lỗi 5xx và p95 đã bật | <điền tên> | ngưỡng alert |
| **Dead letter** có alert khi > 0 | <điền tên> | link alert |
| Trace không chứa dữ liệu nhạy cảm | <điền tên> | mẫu trace |

## 4. Chất lượng

| Mục | Người chịu trách nhiệm | Bằng chứng |
|---|---|---|
| Dataset hồi quy có ít nhất 5 ca khó | <điền tên> | tên dataset |
| Quality gate chặn release kém | <điền tên> | lần gate fail gần nhất |
| Có baseline để so sánh | <điền tên> | điểm baseline |
| Đã thử ít nhất một prompt xấu để thấy gate hoạt động | <điền tên> | kết quả |

## 5. Dữ liệu và pháp lý

| Mục | Người chịu trách nhiệm | Bằng chứng |
|---|---|---|
| Biết dữ liệu nào được gửi cho model | <điền tên> | danh sách trường |
| Có chính sách lưu/ xoá log và trace | <điền tên> | thời hạn lưu |
| Người dùng biết họ đang nói chuyện với AI | <điền tên> | câu thông báo |
| Có đường escalate sang người thật | <điền tên> | quy trình |

## 6. Ngày launch

| Mục | Người chịu trách nhiệm | Bằng chứng |
|---|---|---|
| Deploy lúc ít người dùng, có người theo dõi | <điền tên> | giờ deploy |
| Có người sẵn sàng rollback trong 2 phút | <điền tên> | tên + kênh |
| Thông báo cho bộ phận CSKH biết điều gì mới | <điền tên> | tin nhắn |
| Biết chính xác sẽ xem chỉ số nào trong 30 phút đầu | <điền tên> | 3 chỉ số |

## Câu hỏi cuối cùng

Nếu chỉ được giữ **một** mục trong checklist này, bạn giữ mục nào?

Câu trả lời gợi ý: **rollback**. Mọi mục khác đều có thể sửa sau; không có
rollback thì mỗi lỗi nhỏ đều trở thành sự cố dài.
