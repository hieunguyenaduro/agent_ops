# Lab buổi 5 — CI/CD với GitHub Actions

## Mục tiêu

- Chạy đúng bộ kiểm tra của CI ngay trên máy.
- Hiểu pipeline: test → build → deploy → smoke test.
- Biết deploy chỉ xảy ra khi có tag, và rollback bằng tag cũ.

## Chạy local

```bash
bash scripts/ci_local.sh
```

Kết quả mong đợi:

```text
→ 1/3 Biên dịch toàn bộ code
   ok
→ 2/3 Chạy test
9 passed
→ 3/3 Kiểm tra sẵn sàng deploy
...
✅ Tất cả bước local đã qua. Có thể push.
```

## Thử làm CI thất bại

Sửa `tests/test_agent.py`, đổi kỳ vọng thành `"A9999"`, chạy lại:

```bash
pytest -q
```

Thấy test đỏ. Đây chính là thứ sẽ chặn merge trên GitHub nếu bật
required status checks. Sửa lại rồi chạy tiếp.

## Workflow có gì

| File | Khi nào chạy | Làm gì |
|---|---|---|
| `.github/workflows/ci.yml` | push `main`, mọi PR | compile + test + preflight |
| `.github/workflows/deploy.yml` | push tag `v*` | test → build image → deploy → smoke test |

## Deploy thật (cần cấu hình repo)

Thiết lập trong GitHub repo:

- Variables: `GCP_PROJECT_ID`, `GCP_REGION`
- Secrets: `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`
- Environment: `production` (có thể bật required reviewers)

Sau đó:

```bash
git tag v0.5.0
git push origin v0.5.0
```

## Bài tập

1. Thêm một bước `ruff check .` vào CI. Nếu chưa muốn thêm dependency,
   dùng `python -m compileall` như hiện tại và giải thích vì sao vẫn cần.
2. Đổi workflow deploy để chỉ chạy khi tag khớp `APP_VERSION` trong
   `pyproject`/`.env.example`. Đây là cách chặn "deploy nhầm bản".
3. Mô tả bằng lời: nếu smoke test sau deploy thất bại, pipeline nên làm
   gì tiếp theo? Tự động rollback hay dừng lại cho người quyết định?
