import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.helpers import (
    get_latest_report_directory,
    load_csv,
    load_json,
    load_latest_report_pointer,
    local_experiment_directories,
    safe_extract_report_zip,
)

REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    st.set_page_config(page_title="Report Viewer", layout="wide")
    st.title("Report Viewer")
    source = st.radio(
        "Report source",
        ["Latest local experiment", "Select local experiment", "Upload Evaluation Reports ZIP"],
    )
    reports_dir: Path | None = None
    if source == "Latest local experiment":
        pointer = load_latest_report_pointer(REPORTS_DIR)
        reports_dir = get_latest_report_directory(REPORTS_DIR)
        if pointer:
            st.caption(f"Latest pointer: {pointer.get('report_directory')}")
        if reports_dir is None:
            st.warning("latest.json is missing or points to a missing report directory. Select another local experiment or upload a report ZIP.")
    elif source == "Select local experiment":
        experiment_dirs = local_experiment_directories(REPORTS_DIR)
        if not experiment_dirs:
            st.info("No local saved experiments found under reports/experiments.")
            return
        labels = [path.name for path in experiment_dirs]
        selected = st.selectbox("Local saved experiment", labels)
        reports_dir = experiment_dirs[labels.index(selected)]
        st.caption(f"Local saved reports: {reports_dir.relative_to(PROJECT_ROOT).as_posix()}")
    else:
        uploaded = st.file_uploader(
            "Upload Evaluation Reports ZIP",
            type="zip",
            help="Upload a ZIP containing previously generated evaluation CSV and JSON files. Do not upload the source-code project ZIP.",
        )
        if uploaded is None:
            st.info("Upload an evaluation reports ZIP to view it.")
            return
        extracted, error = safe_extract_report_zip(uploaded, REPORTS_DIR / "uploaded")
        if error:
            st.error(error)
            return
        if extracted:
            reports_dir = extracted
            st.caption("Viewing uploaded reports.")

    if reports_dir is None:
        return

    summary = load_json(reports_dir / "experiment_summary.json") or load_json(
        reports_dir / "evaluation_summary.json"
    )
    if summary:
        st.json(summary)
    else:
        st.info("No summary JSON found.")

    tabs = st.tabs(["Tests", "Configurations", "Gates", "Failed"])
    for tab, filename in zip(
        tabs,
        ["test_results.csv", "configuration_results.csv", "quality_gates.csv", "failed_tests.csv"],
        strict=False,
    ):
        with tab:
            frame = load_csv(reports_dir / filename)
            if frame.empty:
                st.info(f"No {filename} found.")
            else:
                st.dataframe(frame, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
