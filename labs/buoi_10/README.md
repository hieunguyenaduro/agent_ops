# Lab buổi 10 — Game Day & Production Readiness

## Mục tiêu

- Tự kiểm tra mức sẵn sàng vận hành bằng scorecard.
- Diễn tập bốn sự cố thường gặp, không cần cloud hay key.
- Có checklist và runbook để điền tên người thật.

## Chạy scorecard

```bash
python -m labs.buoi_10.game_day
python -m labs.buoi_10.game_day --strict
```

Kết quả mong đợi:

```text
Bảo mật
  ✅ Không có API key trong repo
  ✅ .env nằm trong .gitignore
Vận hành
  ✅ /healthz trả status và version
  ✅ Runbook có rollback
  ✅ Checklist đủ mục bắt buộc
...
Kết quả: 10/10 mục đạt.
```

## Chạy diễn tập

```bash
python -m labs.buoi_10.game_day --drill all
python -m labs.buoi_10.game_day --drill timeout
python -m labs.buoi_10.game_day --drill tool-error
python -m labs.buoi_10.game_day --drill queue
python -m labs.buoi_10.game_day --drill rollback
```

Mỗi drill in ra hành vi mong đợi. Ghi lại thời gian phát hiện và phục hồi
— đó là số liệu để cải thiện, không phải điểm số.

## Hai tài liệu phải điền

| File | Dùng khi nào |
|---|---|
| `checklist.md` | Trước khi mở cho người dùng thật |
| `runbook-template.md` | Khi có sự cố, và trước khi trực |

Điền ít nhất một mục có tên người thật. Checklist không có tên là checklist
để đọc, không phải để làm.

## Bài tập

Xem phần **Bài tập** trong [docs/buoi-10.md](../../docs/buoi-10.md#10-bài-tập).

## Gợi ý cho buổi học cuối

Chia nhóm, mỗi nhóm nhận một sự cố và viết 5 dòng: triệu chứng, chỉ số cần
xem, hành động đầu tiên, người quyết định, cách xác minh. So sánh giữa các
nhóm — khác biệt thường nằm ở bước xác minh.
