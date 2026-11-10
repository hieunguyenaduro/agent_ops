# Buổi 8 — Cost & Latency Optimization

> **Học xong buổi này, bạn có thể:** biết tiền của một agent đi đâu, đo
> đúng ba chỉ số (token, chi phí, latency), tìm điểm nghẽn thật, và chọn
> tối ưu theo đúng thứ tự từ rẻ đến đắt.

## 1. Một câu để nhớ

**Không đo thì không tối ưu — chỉ đang đoán chỗ tiêu tiền.**

Một agent chậm và tốn kém thường không hỏng ở chỗ bạn nghĩ. Người ta hay
sửa prompt trước, trong khi điểm nghẽn thật là một tool gọi 3 lần, hoặc
một vòng lặp agent không có giới hạn.

## 2. Tiền đi đâu

Với một agent, chi phí có bốn phần:

```text
Chi phí request
├── 1. Token vào   (system prompt + lịch sử + tool schema + dữ liệu)
├── 2. Token ra    (câu trả lời, suy luận, JSON)
├── 3. Số lần gọi  (một request người dùng = N lần gọi model)
└── 4. Hạ tầng     (instance, database, queue, egress)
```

Phần thường bị đánh giá thấp là **số lần gọi**. Một câu hỏi của khách có
thể thành 5–10 lần gọi model nếu agent dùng vòng lặp tool. Giảm 20% token
trên mỗi lần gọi không bằng giảm từ 6 lần xuống 3 lần.

Công thức thực dụng:

```text
cost ≈ (token_in × giá_in + token_out × giá_out) × số_lần_gọi
```

## 3. Ba chỉ số, ba cách đọc

| Chỉ số | Đơn vị | Đọc thế nào |
|---|---|---|
| Token | in / out | Xu hướng, không phải mục tiêu tuyệt đối |
| Chi phí | USD / 1.000 request | Con số để ra quyết định |
| Latency | p50 / p95 | Người dùng cảm nhận p95, không phải p50 |

Đừng báo cáo "trung bình". Với agent, phân bố latency rất lệch: phần lớn
request 2 giây, một số ít 30 giây vì model gọi tool nhiều lần. **p95 mới là
con số người dùng nhớ.**

Ba câu hỏi trước khi tối ưu:

1. Chỉ số nào đang tệ: chi phí, p95, hay tỉ lệ lỗi?
2. Nó tệ ở bước nào? (xem trace buổi 6)
3. Tối ưu bước đó có làm chất lượng giảm không? (đo bằng eval buổi 7)

## 4. Tìm điểm nghẽn bằng trace

Một trace minh họa:

```text
request.handle                  agent       8.4s   $0.012
├── retrieve.context            retriever   0.3s
├── tool.lookup_order  ×3       tool        2.1s   (gọi lặp!)
├── llm.plan                    generation  2.0s   $0.006
├── llm.tool_call               generation  1.8s   $0.004
└── llm.answer                  generation  2.2s   $0.002
```

Nhìn vào đây ta thấy:

- **Thời gian**: tool chiếm 2.1s; model chiếm 6s. Nghẽn chính là model.
- **Tiền**: `llm.plan` tốn nhất vì prompt dài (nhiều context + tool schema).
- **Lỗi thiết kế**: `tool.lookup_order` gọi 3 lần cho cùng một mã đơn.

Sửa theo thứ tự: bỏ gọi lặp (rẻ, an toàn) → giảm prompt (cần eval) → đổi
model hoặc song song hóa (đắt, rủi ro hơn).

## 5. Tối ưu theo thứ tự: rẻ trước, đắt sau

| Bậc | Cách làm | Giảm được | Rủi ro |
|---|---|---|---|
| 1 | Bỏ gọi lặp, cache kết quả tool trong request | Token + latency | Thấp |
| 2 | Giảm prompt, bỏ hướng dẫn thừa, rút tool schema | Token vào | Trung bình — phải eval |
| 3 | Đặt `max_tokens` hợp lý | Token ra + latency | Cắt câu trả lời nếu quá thấp |
| 4 | Cache theo câu hỏi (exact match) | Toàn bộ request | Sai dữ liệu nếu cache theo user |
| 5 | Gọi tool song song | Latency | Chỉ khi tool độc lập |
| 6 | Model nhỏ hơn cho bước dễ | Token + latency | Chất lượng |
| 7 | Streaming | Không giảm tổng, giảm cảm giác chờ | Không |
| 8 | Đổi kiến trúc (bỏ vòng lặp, thêm routing) | Nhiều | Cao, cần thiết kế lại |

Đây không phải danh sách "làm hết". Đây là **thứ tự thử**: bậc 1–3 thường
đủ, và không làm hỏng chất lượng nếu đo lại.

## 6. Prompt: chỗ tốn tiền âm thầm

System prompt được gửi **mỗi lần gọi**. Một prompt 800 token, gọi 6 lần
một request, 100.000 request/tháng:

```text
800 × 6 × 100.000 = 480.000.000 token vào mỗi tháng
```

Ở giá 0,40 USD/1M token, riêng system prompt tốn khoảng **192 USD/tháng** —
trước khi tính câu hỏi của khách. Rút prompt từ 800 xuống 200 token tiết
kiệm 75% khoản này mà không đổi model.

Nhưng cẩn thận: prompt ngắn có thể mất hướng dẫn quan trọng. Đây là lý do
buổi 7 tồn tại — **giảm prompt phải đi kèm eval**.

## 7. Cache: thứ rẻ nhất là thứ không gọi lại

Ba tầng cache, khác nhau hoàn toàn:

| Tầng | Khóa | Ai làm | Ghi chú |
|---|---|---|---|
| Prompt cache | Tiền tố prompt | Nhà cung cấp model | Tự động, giảm giá token vào |
| Exact-match cache | Câu hỏi đã chuẩn hóa | Ứng dụng | Rẻ, dễ hiểu, hit rate vừa |
| Semantic cache | Vector gần đúng | Hạ tầng thêm | Mạnh nhưng dễ trả sai |

Trong lab dùng exact-match: chuẩn hóa (lowercase, gộp khoảng trắng) rồi
so khớp. Nó xử lý được người dùng bấm nút hai lần hoặc hỏi lại cùng câu.

> **Quy tắc an toàn:** nếu câu trả lời phụ thuộc người dùng (đơn của tôi,
> số dư của tôi), khóa cache **phải** gồm `user_id`. Nếu không, bạn đang
> trả dữ liệu của người này cho người khác — một sự cố bảo mật, không phải
> một lỗi hiệu năng.

## 8. Song song hóa: chỉ khi độc lập

Ba tool độc lập, mỗi tool 0.4 giây:

```text
tuần tự : 0.4 + 0.4 + 0.4 = 1.2s
song song: max(0.4, 0.4, 0.4) = 0.4s
```

Điều kiện:

1. Tool sau **không cần** kết quả tool trước.
2. Các tool không tranh chấp tài nguyên (cùng ghi một bản ghi, cùng rate limit).
3. Có timeout cho từng tool, để một tool treo không giữ cả request.

Nếu vi phạm điều 1, song song hóa tạo ra kết quả sai — tệ hơn là chậm.

## 9. AI gateway: đặt luật ở một chỗ

Khi có nhiều service cùng gọi model, đừng lặp lại logic ở từng service.
Đặt một **AI gateway** ở giữa:

```text
service A ─┐
service B ─┼──► AI gateway ──► OpenAI / model khác
service C ─┘        │
                    ├── rate limit theo user/team
                    ├── ngân sách theo tháng
                    ├── cache
                    ├── fallback model
                    └── log + cost attribution
```

Lợi ích: một chỗ đặt giới hạn, một chỗ xem chi phí, đổi model không sửa
code từng service. Đánh đổi: thêm một thành phần có thể hỏng, thêm latency
một chặng, và cần người vận hành.

Với khóa học này, điều tối thiểu cần nhớ: **giới hạn chi phí phải ở tầng
gateway hoặc tầng app, không phải trong lời nhắc của prompt.**

## 10. Đánh đổi: mỗi tối ưu đều có giá

| Tối ưu | Được | Mất |
|---|---|---|
| Prompt ngắn | Rẻ, nhanh | Có thể mất ngữ cảnh |
| Model nhỏ | Rẻ, nhanh | Chất lượng giảm ở ca khó |
| Cache | Rẻ, rất nhanh | Dữ liệu cũ, rủi ro rò rỉ |
| Song song | Nhanh | Phức tạp, khó debug |
| `max_tokens` thấp | Rẻ, nhanh | Câu trả lời bị cắt |
| Streaming | Cảm giác nhanh | Không giảm chi phí, khó đo |

Không có bữa trưa miễn phí. Câu hỏi đúng không phải "tối ưu nào tốt nhất",
mà **"đánh đổi nào chấp nhận được với chất lượng hiện tại"**.

## 11. Lab — 30 phút

```bash
python -m labs.buoi_08.measure
python -m labs.buoi_08.cache_demo
python -m labs.buoi_08.parallel_tools
```

Quan sát:

1. `measure`: prompt dài gấp ~7 lần, token vào gấp ~7 lần. Chi phí 3 request?
2. `cache_demo`: 6 câu, 3 hit. Câu nào trượt và vì sao?
3. `parallel_tools`: 1.2s → 0.4s. Điều kiện nào khiến cách này an toàn?

## 12. Bài tập

1. Đổi `OPTIMIZED_PROMPT` dài gần bằng baseline, chạy lại `measure`. Chi
   phí tăng bao nhiêu? Chạy `labs.buoi_07.run_eval` với prompt đó — chất
   lượng có tăng tương ứng không?
2. Thêm `user_id` vào khóa cache trong `cache_demo.py`. Viết 3 câu giải
   thích khi nào **không** được cache theo câu hỏi.
3. Thêm tool thứ tư phụ thuộc `fetch_order` vào `parallel_tools.py`. Sắp
   xếp lại cho đúng và giải thích vì sao không thể song song.
4. Đặt `max_tokens=30`. Câu trả lời có bị cắt? Đây là cách tiết kiệm hay
   cách làm hỏng trải nghiệm?
5. Dùng trace buổi 6 (hoặc trace thật của bạn), tìm bước tốn tiền nhất.
   Đề xuất một tối ưu bậc 1–3 và nêu cách đo lại.

## 13. Tự kiểm tra

1. Vì sao giảm số lần gọi model thường hiệu quả hơn giảm token mỗi lần gọi?
2. Khi nào được cache câu trả lời theo câu hỏi, khi nào phải thêm `user_id`?
3. Vì sao p95 hữu ích hơn latency trung bình khi đánh giá agent?

## 14. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Hỏi: "Agent của bạn tốn tiền ở đâu?" Ghi các câu trả lời lên bảng. |
| 5–15 | Bốn phần chi phí + công thức. Nhấn mạnh số lần gọi. |
| 15–25 | Đọc trace tìm nghẽn; p50 vs p95; ba câu hỏi trước khi tối ưu. |
| 25–35 | Thứ tự 8 bậc; prompt cache vs exact cache vs semantic cache. |
| 35–55 | Lab: chạy 3 script, so sánh số liệu, làm bài tập 1. |
| 55–60 | Chốt: "tối ưu không đi kèm eval là đang đánh cược chất lượng". |

**Demo gây ấn tượng:** chạy `measure` với prompt dài và ngắn, chiếu bảng
chi phí. Sau đó chạy `run_eval` với prompt ngắn để thấy chất lượng có thể
giảm — mở ra cuộc thảo luận về đánh đổi thay vì "cứ rút ngắn prompt".
