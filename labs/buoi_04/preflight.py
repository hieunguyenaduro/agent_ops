"""Buổi 4 — kiểm tra sẵn sàng trước khi deploy lên Cloud Run.

Chạy được ngay trên máy, không cần tài khoản GCP:

    python -m labs.buoi_04.preflight

Kiểm tra thêm một service đang chạy thật:

    python -m labs.buoi_04.preflight --url https://support-agent-xxx.run.app --strict

Mục đích: những lỗi làm deploy thất bại thường rất nhàm chán — sai tên
biến, thiếu Dockerfile, version không khớp. Kiểm tra trước 10 giây tốt
hơn chờ build 3 phút rồi mới biết.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

from labs.common.config import settings

ROOT = Path(__file__).resolve().parents[2]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def ok(label: str, condition: bool, hint: str = "") -> bool:
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ⚠️  {label}" + (f" — {hint}" if hint else ""))
    return condition


def check_local() -> list[bool]:
    print("\n=== KIỂM TRA CẤU HÌNH ===")
    results = [
        ok("APP_VERSION đúng dạng x.y.z", bool(SEMVER.match(settings.app_version)), settings.app_version),
        ok("OPENAI_API_KEY đã cấu hình", not settings.offline, "agent sẽ trả lời giả lập"),
        ok("LANGFUSE keys đã cấu hình", settings.tracing_enabled, "sẽ không có trace"),
    ]

    print("\n=== KIỂM TRA ARTIFACT ===")
    results += [
        ok("Dockerfile tồn tại", (ROOT / "labs/buoi_03/Dockerfile").exists()),
        ok("requirements.txt có pin phiên bản", ">=" in (ROOT / "requirements.txt").read_text()),
        ok("service.yaml tồn tại", (ROOT / "labs/buoi_04/service.yaml").exists()),
        ok(".env không nằm trong git", (ROOT / ".gitignore").exists()),
    ]
    return results


def check_service(url: str) -> list[bool]:
    print(f"\n=== KIỂM TRA SERVICE: {url} ===")
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/healthz", timeout=10) as response:
            body = json.loads(response.read())
    except Exception as exc:  # noqa: BLE001 - hiển thị lỗi cho người vận hành
        print(f"  ❌ Không gọi được /healthz: {exc}")
        return [False]

    print(f"  status={body.get('status')} version={body.get('version')} db={body.get('database')}")
    return [
        ok("Service trả status ok", body.get("status") == "ok"),
        ok("Version khớp APP_VERSION", body.get("version") == settings.app_version,
           f"service={body.get('version')} local={settings.app_version}"),
        ok("Database ghi được", body.get("database") == "ok"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="URL Cloud Run cần kiểm tra sau deploy")
    parser.add_argument("--strict", action="store_true", help="Trả exit code 1 nếu có cảnh báo")
    args = parser.parse_args()

    results = check_local()
    if args.url:
        results += check_service(args.url)

    print("\n=== KẾT LUẬN ===")
    if all(results):
        print("  Sẵn sàng deploy.")
        raise SystemExit(0)

    if args.strict:
        print("  Còn mục chưa đạt — chặn deploy (chế độ --strict).")
        raise SystemExit(1)

    print("  Còn cảnh báo. Vẫn có thể deploy, nhưng hãy đọc từng dòng ở trên.")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
