"""Cấu hình đọc từ biến môi trường.

Nguyên tắc 12-factor: cùng một đoạn code chạy ở laptop, CI và production;
chỉ biến môi trường là khác nhau. Vì vậy không hardcode key, model hay URL
vào code.

File `.env` chỉ dùng khi chạy local. Trên cloud, biến môi trường được
inject bởi nền tảng (Cloud Run, GitHub Actions, Docker Compose...).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Đọc .env nếu có. Không sao nếu không có — production không dùng file này.
load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    """Toàn bộ cấu hình của lab, gom về một chỗ."""

    openai_api_key: str = _env("OPENAI_API_KEY")
    openai_model: str = _env("OPENAI_MODEL", "gpt-4.1-mini")
    app_version: str = _env("APP_VERSION", "0.1.0")

    langfuse_public_key: str = _env("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = _env("LANGFUSE_SECRET_KEY")
    langfuse_host: str = _env("LANGFUSE_HOST", "https://cloud.langfuse.com")

    @property
    def offline(self) -> bool:
        """True khi chưa có OpenAI key.

        Lab vẫn chạy được ở chế độ này để người chưa có key vẫn học được
        luồng API, SSE và Docker.
        """
        return not self.openai_api_key

    @property
    def tracing_enabled(self) -> bool:
        """Chỉ bật Langfuse khi đã có đủ cặp key."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


settings = Settings()

if not settings.tracing_enabled:
    # `.env.example` có sẵn `LANGFUSE_PUBLIC_KEY=` (chuỗi rỗng). Nếu để
    # nguyên, SDK có thể vẫn cố gửi span và in lỗi 401 mỗi lần chạy.
    # Tắt hẳn tracing khi thiếu key.
    os.environ["LANGFUSE_TRACING_ENABLED"] = "false"

    # Đồng thời tắt cảnh báo "thiếu public key" cho gọn khi học.
    # Nếu đã có key mà key sai, cảnh báo vẫn hiện để còn sửa.
    import logging

    logging.getLogger("langfuse").setLevel(logging.CRITICAL)
