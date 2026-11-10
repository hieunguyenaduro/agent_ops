"""Buổi 7 — chạy experiment so sánh baseline và candidate.

Chạy:

    python -m labs.buoi_07.run_eval
    python -m labs.buoi_07.run_eval --gate          # dùng trong CI

Trong CI, `--gate` trả exit code 1 nếu điểm trung bình dưới ngưỡng. Đây là
"quality gate": không cho release một bản kém hơn ngưỡng đã thống nhất.
"""

from __future__ import annotations

import argparse
import sys

from langfuse import get_client

from labs.buoi_07.dataset import (
    BASELINE_PROMPT,
    CANDIDATE_PROMPT,
    DATASET,
    average_score,
    keyword_evaluator,
    make_task,
)
from labs.common.config import settings


def run_variant(name: str, prompt: str):
    client = get_client()
    return client.run_experiment(
        name=f"support-eval-{name}",
        run_name=f"{name}-{settings.app_version}",
        description=f"Đánh giá {name} trên {len(DATASET)} mẫu",
        data=DATASET,
        task=make_task(prompt),
        evaluators=[keyword_evaluator],
        metadata={
            "variant": name,
            "model": settings.openai_model,
            "app_version": settings.app_version,
            "offline": str(settings.offline),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Điểm keyword_match tối thiểu để gate cho qua (mặc định 0.8)",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="Trả exit code 1 nếu candidate dưới ngưỡng",
    )
    args = parser.parse_args()

    print(f"Model  : {settings.openai_model}")
    print(f"Offline: {settings.offline}")
    print(f"Dataset: {len(DATASET)} mẫu\n")

    baseline = run_variant("baseline", BASELINE_PROMPT)
    candidate = run_variant("candidate", CANDIDATE_PROMPT)

    base_score = average_score(baseline)
    cand_score = average_score(candidate)
    delta = cand_score - base_score

    print("Kết quả")
    print(f"  baseline  : {base_score:.3f}")
    print(f"  candidate : {cand_score:.3f}")
    print(f"  chênh lệch: {delta:+.3f}")

    if baseline.experiment_url:
        print(f"\nSo sánh trên Langfuse: {baseline.experiment_url}")
    if candidate.experiment_url:
        print(f"Candidate            : {candidate.experiment_url}")

    if settings.offline:
        print(
            "\nLưu ý: đang chạy offline nên câu trả lời là template mô phỏng.\n"
            "Điền OPENAI_API_KEY để thấy khác biệt thật giữa hai prompt."
        )

    if args.gate:
        if cand_score < args.threshold:
            print(
                f"\n❌ QUALITY GATE THẤT BẠI: {cand_score:.3f} < {args.threshold:.3f}"
            )
            sys.exit(1)
        if delta < 0:
            print(
                f"\n❌ QUALITY GATE THẤT BẠI: candidate kém hơn baseline {delta:+.3f}"
            )
            sys.exit(1)
        print(f"\n✅ Quality gate đạt: {cand_score:.3f} ≥ {args.threshold:.3f}")


if __name__ == "__main__":
    main()
