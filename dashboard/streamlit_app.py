import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.helpers import get_latest_report_directory, load_csv, load_json

REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    st.set_page_config(page_title="LLM Eval Platform", layout="wide")
    st.title("LLM Evaluation Platform")
    st.caption("A lightweight, self-hosted, multi-provider LLM regression-testing and evaluation platform.")

    latest_dir = get_latest_report_directory(REPORTS_DIR)
    report_dir = latest_dir or REPORTS_DIR
    summary = load_json(report_dir / "experiment_summary.json") or load_json(
        report_dir / "evaluation_summary.json"
    )
    if summary is None:
        st.info("No reports found yet. Use the Run Evaluation page to create one.")
        return

    status = summary.get("pipeline_status", summary.get("status", "UNKNOWN"))
    cols = st.columns(4)
    cols[0].metric("Status", status)
    cols[1].metric("Generator", f"{summary.get('generation_provider', '-')}")
    cols[2].metric("Judge", f"{summary.get('judge_provider', '-')}")
    cols[3].metric("Run", summary.get("run_id", "-"))

    if latest_dir:
        st.caption(f"Latest local reports: {latest_dir.relative_to(PROJECT_ROOT).as_posix()}")

    configuration_results = load_csv(report_dir / "configuration_results.csv")
    if not configuration_results.empty:
        st.subheader("Configuration Results")
        display_columns = [
            column
            for column in [
                "configuration_id",
                "prompt_name",
                "pass_rate",
                "average_correctness",
                "average_relevancy",
                "average_faithfulness",
                "safety_pass_rate",
                "hallucination_rate",
                "p95_latency",
                "average_estimated_cost",
            ]
            if column in configuration_results
        ]
        st.dataframe(configuration_results[display_columns], use_container_width=True, hide_index=True)

    failed_tests = load_csv(report_dir / "failed_tests.csv")
    st.subheader("Latest Failed Tests")
    if failed_tests.empty:
        st.success("No failed tests in the latest report.")
    else:
        st.dataframe(failed_tests, use_container_width=True, hide_index=True)

    st.markdown(
        "Use the sidebar pages for live evaluations, model comparison, experiment history, report viewing, and settings."
    )


if __name__ == "__main__":
    main()
