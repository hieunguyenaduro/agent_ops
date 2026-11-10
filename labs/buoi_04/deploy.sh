#!/usr/bin/env bash
# Buổi 4 — deploy Agent API lên Google Cloud Run.
#
# Yêu cầu: đã cài gcloud, đã `gcloud auth login` và chọn đúng project.
#
#   export PROJECT_ID=my-project
#   export APP_VERSION=0.4.0
#   bash labs/buoi_04/deploy.sh
#
# Script cố tình để mọi thứ quan trọng thành biến, để cùng một script
# chạy được cho staging và production.

set -euo pipefail

: "${PROJECT_ID:?Cần đặt PROJECT_ID, ví dụ: export PROJECT_ID=my-project}"

REGION="${REGION:-asia-southeast1}"
SERVICE="${SERVICE:-support-agent}"
REPO="${REPO:-agent-repo}"
VERSION="${APP_VERSION:-0.4.0}"
MODEL="${OPENAI_MODEL:-gpt-4.1-mini}"
LANGFUSE_HOST_VALUE="${LANGFUSE_HOST:-https://cloud.langfuse.com}"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}:${VERSION}"

echo "→ Project : ${PROJECT_ID}"
echo "→ Region  : ${REGION}"
echo "→ Image   : ${IMAGE}"
echo "→ Version : ${VERSION}"
echo

# 1. Build image bằng Cloud Build (không cần Docker trên máy).
#    Build context là thư mục gốc repo vì image cần labs/common.
gcloud builds submit --tag "${IMAGE}" .

# 2. Deploy. Chú ý:
#    - PORT do Cloud Run inject (8080); Dockerfile đã đọc biến này.
#    - Bí mật lấy từ Secret Manager bằng --set-secrets, không nằm trong image.
#    - max-instances là "phanh" chi phí quan trọng nhất lúc mới chạy.
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 20 \
  --min-instances 0 \
  --max-instances 5 \
  --timeout 300 \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,LANGFUSE_PUBLIC_KEY=langfuse-public-key:latest,LANGFUSE_SECRET_KEY=langfuse-secret-key:latest" \
  --set-env-vars "APP_VERSION=${VERSION},OPENAI_MODEL=${MODEL},LANGFUSE_HOST=${LANGFUSE_HOST_VALUE}"

URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format 'value(status.url)')"

echo
echo "✅ Đã deploy: ${URL}"
echo "→ Kiểm tra: python -m labs.buoi_04.preflight --url ${URL} --strict"
echo
echo "Rollback về revision trước:"
echo "  gcloud run revisions list --service ${SERVICE} --region ${REGION}"
echo "  gcloud run services update-traffic ${SERVICE} --region ${REGION} --to-revisions REVISION=100"
