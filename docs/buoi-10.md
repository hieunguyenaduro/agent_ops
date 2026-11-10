# Buổi 10 — Game Day & Production Readiness

> **Học xong buổi này, bạn có thể:** chuẩn bị một buổi diễn tập sự cố,
> viết runbook ngắn mà người trực dùng được lúc 2 giờ sáng, đặt SLO và
> error budget, và chạy postmortem không đổ lỗi.

## 1. Một câu để nhớ

**Production không hỏi bạn biết bao nhiêu. Nó hỏi bạn phản ứng nhanh thế nào.**

Mười buổi vừa qua dạy cách xây agent. Buổi này dạy cách **sống với nó**.
Khác biệt lớn nhất: khi có sự cố, bạn không có thời gian học. Bạn chỉ dùng
được những gì đã chuẩn bị **trước đó**.

## 2. Game day là gì

Một buổi diễn tập có kiểm soát: giả lập sự cố trên môi trường giống
production, đo thời gian phát hiện và phục hồi, rồi sửa những chỗ lúng túng.

Không phải để chứng minh hệ thống hoàn hảo. Mục đích là **tìm chỗ sẽ lúng
túng trước khi khách hàng tìm thấy**.

```text
Chuẩn bị  →  Giả lập  →  Quan sát  →  Ghi timeline  →  Sửa  →  Lặp lại
```

Bốn kịch bản nên diễn tập:

| Kịch bản | Cách giả lập | Câu hỏi cần trả lời |
|---|---|---|
| Model chậm/timeout | Chặn mạng tới provider, hoặc thêm delay | Bao lâu thì có fallback? |
| Tool chết | Tắt order-service giả lập | Người dùng thấy gì? |
| Worker chết | Kill worker giữa lúc chạy | Job có được cứu? |
| Deploy xấu | Deploy image cố tình lỗi | Rollback mất bao lâu? |

Đo ba con số: **thời gian phát hiện (MTTD)**, **thời gian phục hồi (MTTR)**,
và **số bước thủ công** phải làm. Mục tiêu là giảm cả ba.

## 3. Runbook: viết cho người đang hoảng

Runbook tốt có ba đặc điểm:

1. **Ngắn** — người trực đọc trong 30 giây, không phải 30 phút.
2. **Có lệnh cụ thể** — không phải "kiểm tra hệ thống", mà là câu lệnh kèm
   tham số.
3. **Có thứ tự ưu tiên** — rollback trước, tìm nguyên nhân sau.

Cấu trúc tối thiểu:

```text
Thông tin dịch vụ   → link dashboard, trace, log, ai trực
Mức độ sự cố        → SEV1–SEV4, khi nào gọi người
5 phút đầu tiên     → 5 bước, không hơn
Sự cố thường gặp    → dấu hiệu / kiểm tra / hành động / xác minh
Rollback            → lệnh chính xác
Kill switch         → cách tắt nhanh
Truyền thông        → mẫu cập nhật
Sau sự cố           → postmortem
```

Trong repo có `labs/buoi_10/runbook-template.md` — điền vào, đừng chỉ đọc.

> Bài kiểm tra một câu: **"Rollback bằng lệnh nào?"** Nếu người trực không
> trả lời được trong 5 giây, runbook chưa xong.

## 4. On-call và incident command

Khi sự cố lớn, có ba vai — một người có thể kiêm nếu hệ thống nhỏ:

| Vai | Việc |
|---|---|
| Incident Commander | Ra quyết định, giữ timeline, không tự sửa |
| Operator | Chạy lệnh, deploy, rollback |
| Communicator | Cập nhật người dùng và stakeholder |

Vì sao tách vai? Vì người vừa sửa vừa trấn an vừa quyết định sẽ làm cả ba
kém. Trong sự cố, **một người quyết định** quan trọng hơn một người giỏi nhất.

Ba câu người trực cần nói sớm:

1. "Tôi đang xử lý, cập nhật sau 15 phút."
2. "Ảnh hưởng hiện tại là …, tôi chưa biết nguyên nhân."
3. "Tôi cần thêm người ở …, ai nhận được?"

## 5. SLO và error budget

SLO là lời hứa về mức dịch vụ. Error budget là lượng lỗi được phép trước
khi lời hứa bị phá.

```text
SLO: 99,5% request thành công trong 30 ngày
     → error budget = 0,5% × tổng request

Ví dụ 1.000.000 request/tháng:
     budget = 5.000 request lỗi
```

Cách dùng:

- Còn budget → được phép thử cái mới, deploy thường xuyên.
- Gần hết budget → chậm lại, ưu tiên độ ổn định.
- Hết budget → đóng băng thay đổi cho tới khi hồi phục.

Với agent, đo thêm hai SLO chất lượng:

| SLO | Cách đo |
|---|---|
| Tỉ lệ trả lời đúng | Eval định kỳ trên dataset |
| Tỉ lệ có fallback khi lỗi | Đếm request lỗi có câu trả lời thay thế |

Đừng đặt SLO 100%. Không ai đạt được, và nó làm mất ý nghĩa của budget.

## 6. Alert: đủ nhạy, đủ ít

Alert tốt có ba tính chất:

1. **Có thể hành động** — nhận alert biết phải làm gì.
2. **Liên quan người dùng** — lỗi 5xx, p95, cost, chứ không phải CPU.
3. **Không trùng lặp** — một sự cố không tạo 20 alert.

Phân tầng:

| Loại | Ví dụ | Ai nhận |
|---|---|---|
| Page | 5xx > 5% trong 5 phút | Gọi on-call ngay |
| Ticket | dead letter > 0 | Xử lý trong ngày |
| Dashboard | cost tăng 20% | Xem khi họp tuần |

Nếu một alert không dẫn tới hành động nào trong 3 tháng, xoá hoặc sửa nó.
Alert nhiễu làm người trực bỏ qua alert thật.

## 7. Postmortem không đổ lỗi

Mục tiêu là học, không phải tìm người chịu phạt. Người sợ bị phạt sẽ giấu
thông tin — và lần sau sự cố sẽ tệ hơn.

Cấu trúc:

```text
1. Tóm tắt        một đoạn, người ngoài đọc hiểu
2. Ảnh hưởng      ai, bao nhiêu, bao lâu
3. Timeline       mốc thời gian thật, kể cả lúc chưa biết gì
4. Nguyên nhân    chuỗi "vì sao", không dừng ở "ai làm"
5. Điều đã tốt    cái gì giúp phục hồi nhanh
6. Hành động      có người, có hạn, có cách kiểm tra
7. Bài học        thêm vào runbook/checklist/dataset
```

Câu hỏi "vì sao" đi tới gốc:

```text
Sự cố: agent trả lời sai hàng loạt.
Vì sao? Prompt bị đổi.
Vì sao? Không có eval trước release.
Vì sao? Quality gate chưa bật cho đường deploy đó.
→ Hành động: bật gate, không chỉ sửa prompt.
```

## 8. Checklist trước launch

`labs/buoi_10/checklist.md` có 6 nhóm: quyền, vận hành, observability,
chất lượng, dữ liệu/pháp lý, ngày launch.

Điều quan trọng nhất: **mỗi mục có tên người**, không chỉ có dấu ✅. Một
mục không có người nghĩa là không ai làm khi có sự cố.

Nếu chỉ được giữ một mục, hãy giữ **rollback**.

## 9. Lab — 30 phút

Chạy scorecard:

```bash
python -m labs.buoi_10.game_day
python -m labs.buoi_10.game_day --strict
```

Chạy diễn tập:

```bash
python -m labs.buoi_10.game_day --drill all
python -m labs.buoi_10.game_day --drill queue
```

Sau đó mở `checklist.md` và `runbook-template.md`, điền tên thật vào một
mục bất kỳ. Đây là bài tập nhỏ nhưng là khác biệt giữa tài liệu và vận hành.

## 10. Bài tập

1. Chạy `--drill all`, ghi lại thời gian của từng drill. Drill nào mất lâu
   nhất? Vì sao?
2. Chọn một sự cố trong runbook, viết timeline giả định 30 phút với 6 mốc.
   Đánh dấu mốc nào là quyết định, mốc nào là hành động.
3. Đặt SLO 99,5% cho agent. Với 200.000 request/tháng, error budget là bao
   nhiêu? Nếu đã dùng 80%, bạn có nên deploy tính năng mới không?
4. Viết một alert cho "dead letter tăng". Nêu ngưỡng, người nhận, hành
   động đầu tiên.
5. Viết postmortem 1 trang cho một lỗi bạn từng gây ra (trong khóa học
   cũng được). Tập trung vào chuỗi "vì sao", không đổ lỗi.

## 11. Tự kiểm tra

1. Vì sao rollback quan trọng hơn tìm nguyên nhân gốc trong 5 phút đầu?
2. Error budget dùng để quyết định điều gì? Cho một ví dụ.
3. Một alert tốt khác alert xấu ở điểm nào?

## 12. Tổng kết khóa học

Mười buổi là một vòng đời:

```text
1  Baseline & versioning      biết mình đang ở đâu
2  FastAPI + SSE              đưa ra ngoài, có streaming
3  Docker                     đóng gói chạy được ở mọi nơi
4  Cloud Run                  chạy thật, có secret và scaling
5  CI/CD                      tự động kiểm tra và deploy
6  Observability              nhìn thấy bên trong
7  Evaluation                 biết mình tốt lên hay xấu đi
8  Cost & latency             làm nhanh hơn, rẻ hơn có kiểm soát
9  Durable execution          không mất việc khi có sự cố
10 Game day & runbook         sống sót và học sau sự cố
```

Điều xuyên suốt: **mỗi thay đổi phải đo được, và mỗi sự cố phải để lại
một cải tiến**. Đó là khác biệt giữa một prototype và một hệ thống vận hành được.

## 13. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Hỏi: "Sự cố production đầu tiên của bạn là gì?" |
| 5–15 | Game day: mục đích, MTTD/MTTR, bốn kịch bản. |
| 15–25 | Runbook + on-call + ba vai. Nhấn mạnh câu "rollback bằng lệnh nào?". |
| 25–35 | SLO/error budget, alert theo triệu chứng, postmortem không đổ lỗi. |
| 35–55 | Lab: chạy scorecard + drill, điền checklist, viết timeline. |
| 55–60 | Tổng kết khóa; mỗi người nêu một việc sẽ làm trong tuần tới. |

**Hoạt động nhóm cuối khóa:** chia nhóm, mỗi nhóm nhận một sự cố (model
401, tool chết, queue tồn đọng, deploy xấu). Trong 5 phút, viết 5 dòng:
triệu chứng, chỉ số cần xem, hành động đầu tiên, người quyết định, cách xác
minh đã phục hồi. So sánh giữa các nhóm — sự khác biệt thường nằm ở bước
"xác minh", chứ không phải bước "sửa".
