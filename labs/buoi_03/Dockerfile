# syntax=docker/dockerfile:1
#
# Build từ thư mục gốc repo (không phải từ labs/buoi_03), vì image cần
# cả package dùng chung labs/common:
#
#   docker build -f labs/buoi_03/Dockerfile -t support-agent:0.3.0 .
#
# Thứ tự các lệnh rất quan trọng: COPY requirements.txt trước rồi mới
# pip install, để khi chỉ sửa code (không đổi thư viện) Docker dùng lại
# layer cài đặt đã cache, build nhanh hơn nhiều.

FROM python:3.12-slim-bookworm

# - Không ghi .pyc: image sạch hơn.
# - Không buffer stdout: log hiện ngay, quan trọng khi debug container.
# - Không lưu cache pip: image nhỏ hơn.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DB_PATH=/data/agent.db

WORKDIR /app

# Layer 1: thư viện. Chỉ đổi khi requirements.txt đổi.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Layer 2: code. Đổi mỗi lần sửa code nhưng không phải cài lại thư viện.
COPY labs/__init__.py ./labs/__init__.py
COPY labs/common ./labs/common
COPY labs/buoi_03/app.py ./app.py

# Chạy bằng user thường, không phải root. Nếu kẻ tấn công thoát được
# khỏi ứng dụng, hắn có ít quyền hơn.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

# Docker tự gọi endpoint này để biết container còn khoẻ.
# Dùng python có sẵn, không cần cài curl vào image.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"

# --timeout-graceful-shutdown: khi nhận SIGTERM, cho request đang chạy
# tối đa 10 giây để hoàn tất trước khi bị kill.
# Cổng lấy từ biến PORT: Cloud Run tự đặt PORT=8080, local mặc định 8000.
# `exec` giữ cho uvicorn là tiến trình chính để nhận được SIGTERM.
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-graceful-shutdown 10"]
