"""Buổi 1 — kiểm tra môi trường và ghi lại baseline.

Chạy từ thư mục gốc repo:

    python -m labs.buoi_01.check_env

Mục đích: biết chắc "hôm nay mình đang chạy phiên bản nào" trước khi
động vào bất kỳ thứ gì. Mọi buổi sau đều dựa trên baseline này.
"""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from labs.common.agent import prompt_fingerprint
from labs.common.config import settings

PACKAGES = ["langfuse", "openai", "fastapi", "uvicorn", "pydantic", "python-dotenv"]
BASELINE_PATH = Path("baseline.json")


def git_sha() -> str:
    """Lấy commit hiện tại. Không có git thì ghi rõ để không hiểu nhầm."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "no-git"


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "chưa cài"


def check(label: str, ok: bool, hint: str = "") -> bool:
    if ok:
        print(f"  ✅ {label}")
    else:
        print(f"  ⚠️  {label}" + (f" — {hint}" if hint else ""))
    return ok


def main() -> None:
    print("\n=== KIỂM TRA MÔI TRƯỜNG ===\n")

    print("Phiên bản phần mềm:")
    print(f"  Python   {platform.python_version()}")
    for name in PACKAGES:
        print(f"  {name:<12} {package_version(name)}")

    print("\nCấu hình:")
    checks = [
        check("OPENAI_API_KEY", not settings.offline, "sẽ chạy ở chế độ offline"),
        check("LANGFUSE_PUBLIC_KEY", bool(settings.langfuse_public_key), "trace sẽ không được gửi đi"),
        check("LANGFUSE_SECRET_KEY", bool(settings.langfuse_secret_key), "trace sẽ không được gửi đi"),
    ]
    print(f"  Model        {settings.openai_model}")
    print(f"  App version  {settings.app_version}")
    print(f"  Langfuse     {settings.langfuse_host}")

    fingerprint = prompt_fingerprint()
    print("\nDấu vân tay bản chạy (release fingerprint):")
    print(f"  git commit       {git_sha()}")
    print(f"  code version     {settings.app_version}")
    print(f"  model            {settings.openai_model}")
    print(f"  prompt + tools   {fingerprint}")

    baseline = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "packages": {name: package_version(name) for name in PACKAGES},
        "git_sha": git_sha(),
        "app_version": settings.app_version,
        "model": settings.openai_model,
        "prompt_fingerprint": fingerprint,
        "openai_configured": not settings.offline,
        "langfuse_configured": settings.tracing_enabled,
    }
    BASELINE_PATH.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nĐã ghi baseline vào {BASELINE_PATH.resolve()}")
    if not all(checks):
        print(
            "\nGợi ý: sao chép .env.example thành .env rồi điền key còn thiếu.\n"
            "Không có OpenAI key vẫn chạy được lab, chỉ là câu trả lời lấy từ mẫu."
        )
    print()


if __name__ == "__main__":
    main()
