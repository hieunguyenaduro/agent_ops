# Lab buổi 4 — Deploy lên Cloud Run

## Mục tiêu

- Hiểu cấu hình runtime, secret và scaling của một service trên cloud.
- Kiểm tra sẵn sàng trước khi deploy bằng một script chạy được local.
- Biết cách rollback và kiểm soát chi phí.

## Chạy không cần GCP (phần nên làm trước)

```bash
python -m labs.buoi_04.preflight
```

Script kiểm tra version, key, Dockerfile, cách pin thư viện và manifest.
Đây chính là những lỗi làm deploy thất bại.

## Deploy thật (cần tài khoản GCP)

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

export PROJECT_ID=YOUR_PROJECT_ID
export APP_VERSION=0.4.0
bash labs/buoi_04/deploy.sh
```

Sau khi có URL:

```bash
python -m labs.buoi_04.preflight --url https://support-agent-xxxx.run.app --strict
```

## Kiểm tra service trên cloud

```bash
# Xem revision đang nhận traffic
gcloud run revisions list --service support-agent --region asia-southeast1

# Xem log gần nhất
gcloud run services logs read support-agent --region asia-southeast1 --limit 50

# Rollback
gcloud run services update-traffic support-agent \
  --region asia-southeast1 \
  --to-revisions support-agent-00002-abc=100
```

## Thử thách

1. Deploy với `--max-instances 1`, dùng `hey` hoặc `locust` bắn 20 request
   đồng thời. Quan sát thời gian chờ và log.
2. Đổi `APP_VERSION` nhưng **không** đổi image tag. Chuyện gì xảy ra với
   `/healthz`? Vì sao đây là lỗi cần chặn trong CI/CD?
3. Gây lỗi bằng cách xoá một secret. Service có restart liên tục không?
   Health check có phát hiện được không?
