# Lab buổi 1 — Baseline và phiên bản

## Mục tiêu

- Biết môi trường đang chạy phiên bản gì.
- Tạo một baseline có thể tái lập cho các buổi sau.
- Thấy trace đầu tiên trên Langfuse.

## Chạy

Từ thư mục gốc repo:

```bash
python -m labs.buoi_01.check_env
python -m labs.buoi_01.baseline_agent
```

## Kết quả mong đợi

`check_env` in bảng phiên bản, trạng thái key và ghi `baseline.json`:

```json
{
  "git_sha": "no-git",
  "app_version": "0.1.0",
  "model": "gpt-4.1-mini",
  "prompt_fingerprint": "7ee93e9e0ab8"
}
```

`baseline_agent` in câu trả lời, các bước đã chạy và link trace.

## Ghi chú

- Chưa có `OPENAI_API_KEY` vẫn chạy được: agent trả lời bằng dữ liệu mẫu.
- Chưa có `LANGFUSE_*` vẫn chạy được, chỉ là không có trace.
- `baseline.json` đã nằm trong `.gitignore` — đây là dữ liệu của máy bạn,
  không phải thứ để commit.

## Bài tập

Xem phần **Bài tập** trong [docs/buoi-01.md](../../docs/buoi-01.md#8-bài-tập).
