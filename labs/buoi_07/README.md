# Lab buổi 7 — Continuous Evaluation

## Mục tiêu

- Chạy experiment trên một dataset nhỏ.
- So sánh baseline và candidate bằng evaluator.
- Dùng quality gate để chặn release kém.

## Chạy

```bash
python -m labs.buoi_07.run_eval
python -m labs.buoi_07.run_eval --gate
```

Kết quả mong đợi (chế độ offline):

```text
baseline  : 0.400
candidate : 1.000
chênh lệch: +0.600
```

## Đưa dataset lên Langfuse

```bash
python -m labs.buoi_07.seed_dataset
```

Sau đó vào **Datasets → support-agent-regression**, chạy experiment và
so sánh hai lần chạy.

## Dùng trong CI

Thêm bước sau vào pipeline (cần secret thật):

```yaml
- name: Quality gate
  run: python -m labs.buoi_07.run_eval --gate
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
    LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
```

Có sẵn file mẫu `.github/workflows/eval.yml` (chạy tay bằng
`workflow_dispatch` để tránh tốn tiền mỗi lần push).

## Bài tập

Xem phần **Bài tập** trong [docs/buoi-07.md](../../docs/buoi-07.md#9-bài-tập).
