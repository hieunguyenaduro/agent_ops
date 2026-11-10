# Lab buổi 8 — Cost & Latency Optimization

## Mục tiêu

- Đo token, chi phí và latency trước khi tối ưu.
- Thấy ảnh hưởng của system prompt và `max_tokens`.
- Dùng cache tầng ứng dụng và gọi tool song song.

## Chạy

```bash
python -m labs.buoi_08.measure
python -m labs.buoi_08.cache_demo
python -m labs.buoi_08.parallel_tools
```

Kết quả mong đợi (offline):

```text
              in tok  out tok     latency   cost 3 req
baseline         178       23  n/a (offline)     0.000324$
optimized         24       23  n/a (offline)     0.000139$

Giảm token: 77%
```

`cache_demo` cho thấy 3/6 câu là cache hit (50%) nhờ chuẩn hóa câu hỏi.
`parallel_tools` cho thấy gọi 3 tool song song nhanh hơn khoảng 3 lần.

> Offline không gọi model nên không có latency thật — bảng in `n/a`.
> Điền `OPENAI_API_KEY` để có số đo latency thật.

## Đọc số liệu đúng cách

| Chỉ số | Lấy từ đâu | Cẩn thận |
|---|---|---|
| Token vào/ra | `usage` của model | Đừng tự đếm bằng `len(text)//4` khi có số thật |
| Chi phí | Token × bảng giá hiện hành | Giá thay đổi; ghi ngày tra giá |
| Latency | Đo quanh lời gọi | p50 khác p95 rất nhiều |
| Cache hit | Bộ đếm của bạn | Hit rate cao chưa chắc đúng (cache sai dữ liệu) |

## Bài tập

1. Đổi `OPTIMIZED_PROMPT` dài gần bằng baseline. Chi phí tăng bao nhiêu?
   Chất lượng (dùng eval buổi 7) có tăng tương ứng không?
2. Thêm `user_id` vào khóa cache. Khi nào **không** được cache theo câu hỏi?
3. Thêm tool thứ tư mất 0.4s nhưng phụ thuộc kết quả `fetch_order`. Sửa
   `parallel_tools` cho đúng thứ tự và giải thích vì sao không song song được.
4. Đặt `max_tokens=30` trong `measure.py`. Câu trả lời có bị cắt không?
   Đây là cách chặn chi phí hay cách làm hỏng trải nghiệm?

## Bài học chính

- Tối ưu phải **đo trước**, nếu không bạn chỉ đang đổi chỗ tốn kém.
- Prompt ngắn là cách giảm chi phí rẻ nhất, nhưng phải kiểm tra chất lượng.
- Cache và song song hóa là tối ưu tầng ứng dụng: không đổi model, không
  đổi hạ tầng.
