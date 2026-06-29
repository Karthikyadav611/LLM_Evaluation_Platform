import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Settings
from app.constants import API_KEY_ENV_VARS, SUPPORTED_PROVIDERS


def main() -> None:
    st.set_page_config(page_title="Settings", layout="wide")
    st.title("Settings")
    settings = Settings()
    st.subheader("Default Thresholds")
    st.json(settings.thresholds())
    st.subheader("Storage")
    st.write({"database_url": settings.database_url, "reports_dir": str(Path("reports").resolve())})
    st.subheader("Supported Providers")
    st.dataframe(
        [{"provider": provider, "env_var": API_KEY_ENV_VARS[provider]} for provider in SUPPORTED_PROVIDERS],
        use_container_width=True,
        hide_index=True,
    )
    st.subheader("Active Configuration")
    st.json(
        {
            "generation_provider": settings.generation_provider,
            "generation_model": settings.generation_model,
            "judge_provider": settings.judge_provider,
            "judge_model": settings.judge_model,
            "max_concurrent_requests": settings.max_concurrent_requests,
        }
    )
    st.caption("API keys are intentionally not displayed.")


if __name__ == "__main__":
    main()
