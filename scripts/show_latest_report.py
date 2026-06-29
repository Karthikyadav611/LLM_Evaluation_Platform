import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.reports.persistence import latest_report_directory, read_latest_pointer
from dashboard.helpers import load_json


def main() -> int:
    reports_dir = PROJECT_ROOT / "reports"
    pointer = read_latest_pointer(reports_dir)
    if pointer is None:
        print("No reports/latest.json found.")
        return 1

    report_dir = latest_report_directory(reports_dir)
    print("Latest experiment metadata:")
    print(json.dumps(pointer, indent=2))
    if report_dir is None:
        print("Referenced report directory is missing.")
        return 2

    print(f"\nReport directory: {report_dir.relative_to(PROJECT_ROOT).as_posix()}")
    print("Available report files:")
    for path in sorted(report_dir.iterdir()):
        if path.is_file():
            print(f"- {path.name}")

    summary = load_json(report_dir / "experiment_summary.json")
    if summary:
        candidate = summary.get("candidate_metrics", {})
        print("\nKey summary metrics:")
        print(f"- pipeline_status: {summary.get('pipeline_status')}")
        print(f"- pass_rate: {candidate.get('pass_rate')}")
        print(f"- average_correctness: {candidate.get('average_correctness')}")
        print(f"- average_faithfulness: {candidate.get('average_faithfulness')}")
        print(f"- hallucination_rate: {candidate.get('hallucination_rate')}")
        print(f"- safety_pass_rate: {candidate.get('safety_pass_rate')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
