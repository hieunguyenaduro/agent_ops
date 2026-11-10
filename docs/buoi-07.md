# Buổi 7 — Continuous Evaluation with Langfuse

> **Học xong buổi này, bạn có thể:** xây một dataset hồi quy nhỏ, viết
> evaluator, so sánh baseline với candidate, và đặt quality gate chặn
> release kém.

## 1. Một câu để nhớ

**Unit test hỏi "code có chạy không?". Evaluation hỏi "câu trả lời có tốt
không?".**

Hai câu này khác nhau, và không thể thay thế nhau. Một agent có thể trả
về đúng JSON, không lỗi, nhưng trả lời sai hoàn toàn — unit test vẫn xanh.

Evaluation là cách duy nhất để biết mình đang tốt lên hay xấu đi.

## 2. Vòng lặp cải thiện chất lượng

```text
   ① Thu thập ca khó        (feedback, lỗi production, review tay)
            │
            ▼
   ② Đưa vào dataset        (input + kỳ vọng, có version)
            │
            ▼
   ③ Chạy experiment        (baseline vs candidate)
            │
            ▼
   ④ Chấm điểm              (code, LLM-judge, người)
            │
            ▼
   ⑤ So sánh & quyết định   (quality gate)
            │
            └──── release hoặc quay lại ①
```

Điểm quan trọng: vòng lặp này **không bắt đầu từ code**. Nó bắt đầu từ
một ca thực tế đã làm người dùng không hài lòng.

## 3. Offline và online evaluation

| | Offline | Online |
|---|---|---|
| Chạy trên | Dataset cố định | Trace thật trên production |
| Khi nào | Trước release | Liên tục |
| Trả lời | "Bản mới có tốt hơn bản cũ?" | "Hôm nay có gì bất thường?" |
| Rủi ro | Dataset lệch với thực tế | Nhiễu, thiếu nhãn |
| Chi phí | Thấp, lặp lại được | Cao hơn, cần sampling |

Hai thứ bổ sung nhau. Offline giúp **quyết định release**. Online giúp
**phát hiện điều dataset chưa từng thấy**.

## 4. Dataset: nhỏ mà đúng

Dataset tốt không phải dataset lớn. Nó là tập **ca khó đã từng xảy ra**:

- Câu hỏi thiếu mã đơn.
- Mã đơn không tồn tại.
- Câu hỏi mơ hồ ("đơn của tôi sao rồi?").
- Câu hỏi ghép hai ý ("đơn A1001 có được hoàn tiền không?").
- Ca từng lỗi trong production (quan trọng nhất).

Với mỗi mẫu, cần:

```json
{
  "input": {"order_id": "A1001", "question": "Đơn A1001 bao giờ tới?"},
  "expected_output": ["A1001", "đang giao", "2 ngày"]
}
```

Vì sao `expected_output` là **danh sách từ khóa**, không phải nguyên câu?
Vì agent không deterministic. Ta cần biết **thông tin bắt buộc có xuất
hiện** hay không, không cần câu chữ giống hệt.

> Quy tắc: kỳ vọng càng cụ thể, test càng dễ giòn. Kỳ vọng càng mơ hồ,
> test càng dễ cho qua sai. Chọn mức "đủ để phân biệt đúng/sai".

## 5. Ba loại evaluator

| Loại | Cách làm | Mạnh | Yếu |
|---|---|---|---|
| Code | `if keyword in output` | Nhanh, rẻ, ổn định | Không hiểu ngữ nghĩa |
| LLM-as-a-judge | Gọi model chấm theo rubric | Hiểu ngữ nghĩa, linh hoạt | Tốn tiền, có thể thiên vị |
| Người | Review mẫu | Chuẩn nhất | Chậm, đắt, không scale |

Thứ tự thực dụng:

1. Bắt đầu bằng **code evaluator** cho thứ đo được (có mã đơn? đúng
   trạng thái? đúng format?).
2. Thêm **LLM-judge** cho thứ cần hiểu nghĩa (có lịch sự? có bịa không?).
3. Dùng **người** để **hiệu chuẩn** judge, không dùng để chấm mọi mẫu.

Một LLM-judge chưa được hiệu chuẩn là một ý kiến, không phải một phép đo.

## 6. Quality gate: biến đánh giá thành quyết định

Điểm số chỉ có giá trị khi nó chặn được một hành động. Quality gate là
một dòng trong pipeline:

```python
if candidate_score < 0.8:
    sys.exit(1)          # chặn release
if candidate_score < baseline_score:
    sys.exit(1)          # tệ hơn bản cũ cũng chặn
```

Ba lưu ý:

1. **Ngưỡng phải do con người đặt và ghi lại.** Đừng để model tự quyết.
2. **Luôn so với baseline**, không chỉ so với ngưỡng tuyệt đối. Một bản
   điểm 0.85 có thể vẫn tệ hơn bản cũ 0.90.
3. **Gate có thể sai.** Nếu gate chặn một bản thực sự tốt, sửa dataset
   hoặc evaluator — đừng tắt gate.

## 7. Đừng overfit vào dataset

Nếu bạn sửa prompt cho đến khi 5 mẫu đều 1.0, bạn có thể chỉ đang học
thuộc 5 mẫu đó.

Ba cách giữ dataset trung thực:

- Giữ một phần mẫu **không dùng để sửa prompt** (hold-out).
- Thêm mẫu mới từ production mỗi tháng.
- Xoay vòng mẫu cũ, nhưng giữ lại các ca "kinh điển" đã từng gây sự cố.

## 8. Lab — 30 phút

Chạy so sánh hai prompt:

```bash
python -m labs.buoi_07.run_eval
```

Kết quả mong đợi (offline):

```text
baseline  : 0.400
candidate : 1.000
chênh lệch: +0.600
```

Thử gate:

```bash
python -m labs.buoi_07.run_eval --gate
python -m labs.buoi_07.run_eval --gate --threshold 1.1   # cố tình fail
```

Đưa dataset lên Langfuse (nếu có key):

```bash
python -m labs.buoi_07.seed_dataset
```

Sau đó mở **Datasets** trên Langfuse, chạy experiment và so sánh hai lần
chạy cạnh nhau.

## 9. Bài tập

1. Thêm một mẫu "mã đơn không tồn tại" (`A9999`). Agent hiện trả lời thế
   nào? Câu trả lời đó có chấp nhận được không?
2. Viết thêm evaluator `must_not_hallucinate`: trả 0 nếu câu trả lời chứa
   một mã đơn không có trong dữ liệu.
3. Đổi ngưỡng gate xuống 0.5. Điều gì xảy ra với baseline? Vì sao ngưỡng
   thấp không giúp release nhanh hơn?
4. Viết một LLM-judge ngắn (3 tiêu chí: đúng, đủ, lịch sự). So sánh điểm
   của nó với `keyword_match` trên cùng dataset. Chúng lệch nhau ở đâu?

## 10. Tự kiểm tra

1. Vì sao không nên so khớp nguyên văn câu trả lời trong eval agent?
2. Khi nào dùng code evaluator, khi nào cần LLM-judge?
3. Quality gate nên so với ngưỡng tuyệt đối, baseline, hay cả hai? Vì sao?

## 11. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Hỏi: "Bạn biết agent tốt lên nhờ đâu?" Ghi câu trả lời. |
| 5–15 | Vòng lặp 5 bước + offline/online. Nhấn mạnh: bắt đầu từ ca khó. |
| 15–25 | Dataset và ba loại evaluator; ưu nhược điểm. |
| 25–35 | Quality gate + overfit. Kể ví dụ gate cứu một lần release. |
| 35–55 | Lab: chạy eval, cố tình làm gate fail, thêm một mẫu mới. |
| 55–60 | Chốt: "không có baseline thì không có cải thiện". |

**Thảo luận:** nếu evaluator và người chấm bất đồng 20% số mẫu, tin ai?
Câu trả lời tốt: tin người, sửa evaluator, ghi lại các ca bất đồng.
