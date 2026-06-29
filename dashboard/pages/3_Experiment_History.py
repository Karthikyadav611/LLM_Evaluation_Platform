
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Settings
from app.storage.database import create_database_engine, create_session_factory
from app.storage.migrations import initialize_database
from app.storage.repositories import ExperimentRepository


def main() -> None:
    st.set_page_config(page_title="Experiment History", layout="wide")
    st.title("Experiment History")
    settings = Settings()
    try:
        engine = create_database_engine(settings.database_url)
        initialize_database(engine)
        repository = ExperimentRepository(create_session_factory(engine))
        rows = repository.list_experiments()
    except Exception as exc:
        st.info(f"Experiment database is not initialized yet: {exc}")
        return
    if not rows:
        st.info("No persisted experiments yet.")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)
    selected = st.selectbox(
        "Open report directory",
        [row["report_directory"] for row in rows if row.get("report_directory")],
    )
    if selected:
        report_path = (PROJECT_ROOT / selected).resolve()
        if report_path.exists():
            st.success(f"Report directory: {selected}")
        else:
            st.warning(f"Stored report directory is missing: {selected}")
    st.caption("PASS, FAIL, and ERROR experiments are included.")


if __name__ == "__main__":
    main()
