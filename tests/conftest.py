"""Buổi 5 — test cho agent và API, chạy được không cần key.

Nguyên tắc: test phải nhanh, lặp lại được, và không phụ thuộc mạng.
Vì vậy bộ test này chạy ở chế độ offline của agent.
"""

from __future__ import annotations

import os

# Đặt trước khi import bất cứ module nào của labs: config dùng
# load_dotenv(override=False), nên biến đã có (dù rỗng) sẽ thắng .env.
os.environ["OPENAI_API_KEY"] = ""
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
os.environ["APP_VERSION"] = "0.5.0"
