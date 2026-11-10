"""Buổi 10 — Game Day: kiểm tra sẵn sàng vận hành và diễn tập sự cố.

Chạy:

    python -m labs.buoi_10.game_day
    python -m labs.buoi_10.game_day --strict
    python -m labs.buoi_10.game_day --drill all

Phần 1 là **scorecard**: tự động kiểm tra những thứ đã học ở buổi 1–9.
Phần 2 là **drill**: mô phỏng ba sự cố thường gặp và cho thấy hành vi
mong đợi. Không cần key, không cần cloud.

Đây không phải bài kiểm tra để lấy điểm. Đây là danh sách những câu hỏi
mà người trực sự cố phải trả lời được **trước khi** có sự cố.
"""

from __future__ import annotations

import argparse
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9]{20,}")


@dataclass
class Check:
    name: str
    category: str
    passed: bool
    detail: str
    hint: str = ""


def file_contains(path: Path, needle: str) -> bool:
    if not path.exists():
        return False
    return needle.lower() in path.read_text(encoding="utf-8").lower()


def count_tests() -> int:
    tests = ROOT / "tests"
    if not tests.exists():
        return 0
    return sum(
        len(re.findall(r"^def test_", path.read_text(encoding="utf-8"), re.MULTILINE))
        for path in tests.glob("test_*.py")
    )


def secrets_in_repo() -> list[str]:
    """Tìm key thật lỡ nằm trong file người đọc được (bỏ qua .venv)."""
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix not in {".py", ".md", ".yaml", ".yml", ".sh", ".json", ".env", ""}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if SECRET_PATTERN.search(text):
            hits.append(str(path.relative_to(ROOT)))
    return hits


def run_checks() -> list[Check]:
    checks: list[Check] = []

    # 1. Bí mật không nằm trong repo.
    hits = secrets_in_repo()
    checks.append(
        Check(
            "Không có API key trong repo",
            "Bảo mật",
            not hits,
            "không tìm thấy key" if not hits else f"nghi vấn: {hits}",
            "Xoá key, đổi key mới, thêm file vào .gitignore.",
        )
    )

    # 2. .env được bỏ qua.
    gitignore = ROOT / ".gitignore"
    checks.append(
        Check(
            ".env nằm trong .gitignore",
            "Bảo mật",
            file_contains(gitignore, ".env"),
            ".gitignore có .env" if file_contains(gitignore, ".env") else "chưa thấy",
        )
    )

    # 3. Health check thật sự trả lời.
    try:
        from fastapi.testclient import TestClient

        from labs.buoi_02.app import app

        with TestClient(app) as client:
            body = client.get("/healthz").json()
        healthy = body.get("status") == "ok" and "version" in body
        detail = f"status={body.get('status')} version={body.get('version')}"
    except Exception as exc:  # noqa: BLE001 - scorecard phải chạy tiếp
        healthy = False
        detail = f"{type(exc).__name__}: {exc}"

    checks.append(
        Check(
            "/healthz trả status và version",
            "Vận hành",
            healthy,
            detail,
            "Health check là thứ load balancer dùng để quyết định cắt traffic.",
        )
    )

    # 4. Có test tự động.
    tests = count_tests()
    checks.append(
        Check(
            "Có test tự động",
            "Chất lượng",
            tests >= 10,
            f"{tests} test",
            "Ít nhất một test cho agent, API và hàng đợi.",
        )
    )

    # 5. Quality gate trong CI.
    eval_workflow = ROOT / ".github/workflows/eval.yml"
    checks.append(
        Check(
            "CI có quality gate",
            "Chất lượng",
            file_contains(eval_workflow, "--gate"),
            str(eval_workflow.relative_to(ROOT)),
            "Đánh giá không có ngưỡng thì không chặn được release.",
        )
    )

    # 6. Giới hạn chi phí.
    deploy_script = ROOT / "labs/buoi_04/deploy.sh"
    checks.append(
        Check(
            "Có giới hạn max-instances",
            "Chi phí",
            file_contains(deploy_script, "--max-instances"),
            "deploy.sh có --max-instances",
            "Một vòng lặp agent chạy trên 50 instance là hoá đơn không mong muốn.",
        )
    )

    # 7. Log có correlation id.
    logs = ROOT / "labs/buoi_06/sample_logs.jsonl"
    checks.append(
        Check(
            "Log có request_id và trace_id",
            "Observability",
            file_contains(logs, '"request_id"') and file_contains(logs, '"trace_id"'),
            "sample_logs.jsonl có cả hai khóa",
            "Không có trace_id, điều tra sự cố là đọc log bằng mắt.",
        )
    )

    # 8. Có đường rollback.
    checks.append(
        Check(
            "Runbook có rollback",
            "Vận hành",
            file_contains(ROOT / "labs/buoi_10/runbook-template.md", "rollback"),
            "runbook-template.md có mục rollback",
            "Nếu không trả lời được 'rollback bằng lệnh nào', chưa sẵn sàng.",
        )
    )

    # 9. Checklist có đủ mục bắt buộc.
    checklist = ROOT / "labs/buoi_10/checklist.md"
    required = ["rollback", "on-call", "kill switch", "dead letter"]
    missing = [item for item in required if not file_contains(checklist, item)]
    checks.append(
        Check(
            "Checklist đủ mục bắt buộc",
            "Vận hành",
            checklist.exists() and not missing,
            "đủ rollback, on-call, kill switch, dead letter"
            if not missing
            else f"thiếu: {missing}",
            "Checklist thiếu mục nghĩa là chưa ai nhận trách nhiệm cho mục đó.",
        )
    )

    # 10. Có ít nhất một bài học về dead letter.
    checks.append(
        Check(
            "Hàng đợi có dead letter",
            "Độ bền",
            file_contains(ROOT / "labs/buoi_09/store.py", "'dead'"),
            "store.py có trạng thái dead",
            "Job lỗi phải được nhìn thấy, không biến mất.",
        )
    )

    return checks


# -- drills ---------------------------------------------------------------


def call_with_timeout(fn, seconds: float):
    """Gọi hàm với timeout. Lưu ý: thread Python không bị kill; hàm vẫn
    chạy tiếp ở nền. Vì vậy mọi lời gọi mạng vẫn cần timeout riêng."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(fn).result(timeout=seconds)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def safe_answer(question: str, primary, fallback) -> str:
    """Fallback tầng ứng dụng: lỗi phụ thuộc không được biến thành 500."""
    try:
        return primary(question)
    except Exception as exc:  # noqa: BLE001 - cố ý bắt mọi lỗi của dependency
        return fallback(question, exc)


def drill_timeout() -> None:
    print("\n[drill] Model/tool chậm — timeout và fallback")

    def _timeout_failure(question: str) -> str:
        raise TimeoutError("dependency quá 0.2s")

    started = time.perf_counter()
    try:
        call_with_timeout(lambda: time.sleep(0.8) or "kết quả", 0.2)
        print("  ❌ Không timeout — kiểm tra lại cấu hình.")
        return
    except TimeoutError:
        elapsed = time.perf_counter() - started

    answer = safe_answer(
        "Đơn A1001 bao giờ tới?",
        _timeout_failure,
        lambda q, exc: (
            "Xin lỗi, hệ thống tra cứu đang bận. "
            "Bạn thử lại sau ít phút hoặc để lại mã đơn, mình sẽ phản hồi sau."
        ),
    )
    print(f"  ✅ Dừng sau {elapsed:.2f}s thay vì chờ 0.8s")
    print(f"  → Người dùng nhận: {answer}")


def drill_tool_error() -> None:
    print("\n[drill] Tool lỗi — câu trả lời suy giảm, không phải 500")

    def broken_lookup(question: str) -> str:
        raise ConnectionError("order-service không phản hồi")

    answer = safe_answer(
        "Đơn A1001 bao giờ tới?",
        broken_lookup,
        lambda q, exc: (
            "Xin lỗi, mình chưa tra được đơn lúc này. "
            "Bạn vui lòng thử lại sau ít phút."
        ),
    )
    print(f"  ✅ Bắt được ConnectionError")
    print(f"  → Người dùng nhận: {answer}")
    print("  → Log/trace vẫn ghi lỗi để người trực điều tra.")


def drill_queue_backlog() -> None:
    print("\n[drill] Worker chết — hàng đợi tự phục hồi")
    import tempfile

    from labs.buoi_09.store import JobStore

    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(Path(tmp) / "jobs.db", lease_seconds=0.2, max_attempts=3)
        for index in range(4):
            store.enqueue(
                f"Đơn A100{index + 1}?",
                user_id=f"u-{index}",
                session_id=f"s-{index}",
            )

        abandoned = store.claim("worker-a")
        assert abandoned is not None
        print(f"  worker-a nhận {abandoned.id} rồi chết (không complete)")
        time.sleep(0.25)

        recovered = store.claim("worker-b")
        assert recovered is not None
        print(
            f"  ✅ worker-b nhận lại {recovered.id} "
            f"sau khi lease hết hạn, attempts={recovered.attempts}"
        )
        store.complete(recovered.id, "đã trả lời")
        print(f"  → còn lại: {store.stats()}")
        store.close()


def drill_rollback() -> None:
    print("\n[drill] Rollback — hai lệnh phải thuộc lòng")
    print("  gcloud run revisions list --service support-agent --region asia-southeast1")
    print(
        "  gcloud run services update-traffic support-agent "
        "--region asia-southeast1 --to-revisions <REVISION>=100"
    )
    print("  → Mục tiêu: quay lại bản cũ trong dưới 2 phút.")


DRILLS = {
    "timeout": drill_timeout,
    "tool-error": drill_tool_error,
    "queue": drill_queue_backlog,
    "rollback": drill_rollback,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Exit 1 nếu có mục fail")
    parser.add_argument(
        "--drill",
        choices=[*DRILLS, "all"],
        help="Chạy diễn tập sự cố thay vì scorecard",
    )
    args = parser.parse_args()

    if args.drill:
        names = list(DRILLS) if args.drill == "all" else [args.drill]
        for name in names:
            DRILLS[name]()
        print("\n✅ Diễn tập xong. Ghi lại thời gian phát hiện và thời gian phục hồi.")
        return

    checks = run_checks()
    categories: dict[str, list[Check]] = {}
    for check in checks:
        categories.setdefault(check.category, []).append(check)

    print("=== GAME DAY SCORECARD ===\n")
    for category, items in categories.items():
        print(category)
        for check in items:
            mark = "✅" if check.passed else "❌"
            print(f"  {mark} {check.name} — {check.detail}")
            if not check.passed and check.hint:
                print(f"     ↳ {check.hint}")
        print()

    passed = sum(1 for check in checks if check.passed)
    total = len(checks)
    print(f"Kết quả: {passed}/{total} mục đạt.")

    if passed < total:
        print(
            "\nĐây là danh sách việc cần làm trước launch — "
            "không phải lỗi của buổi học."
        )
        if args.strict:
            raise SystemExit(1)
    else:
        print("\n✅ Sẵn sàng cho game day.")


if __name__ == "__main__":
    main()
