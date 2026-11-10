#!/usr/bin/env bash
# Chạy đúng những gì CI chạy, ngay trên máy — trước khi push.
#
#   bash scripts/ci_local.sh

set -euo pipefail

echo "→ 1/3 Biên dịch toàn bộ code"
python -m compileall -q labs
echo "   ok"

echo "→ 2/3 Chạy test"
pytest -q

echo "→ 3/3 Kiểm tra sẵn sàng deploy"
python -m labs.buoi_04.preflight

echo
echo "✅ Tất cả bước local đã qua. Có thể push."
