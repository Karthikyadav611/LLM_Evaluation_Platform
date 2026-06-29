import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.helpers import fairness_warnings, load_csv

REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    st.set_page_config(page_title="Model Comparison", layout="wide")
    st.title("Model Comparison")
    rows = load_csv(REPORTS_DIR / "model_comparison.csv")
    if rows.empty:
        st.info("No model comparison report found.")
        return
    warnings = fairness_warnings(rows.to_dict(orient="records"))
    for warning in warnings:
        st.warning(warning)
    st.dataframe(rows, use_container_width=True, hide_index=True)
    metric_cols = [column for column in ["pass_rate", "average_correctness", "average_relevancy", "average_faithfulness", "hallucination_rate", "safety_pass_rate", "p95_latency", "average_estimated_cost"] if column in rows]
    if metric_cols:
        st.subheader("Winners by Metric")
        winners = []
        for metric in metric_cols:
            ascending = metric in {"hallucination_rate", "p95_latency", "average_estimated_cost"}
            clean = rows.dropna(subset=[metric])
            if not clean.empty:
                best = clean.sort_values(metric, ascending=ascending).iloc[0]
                winners.append({"metric": metric, "configuration_id": best.get("configuration_id"), "value": best[metric]})
        st.dataframe(pd.DataFrame(winners), use_container_width=True, hide_index=True)
        st.caption("Balanced recommendation depends on your preferred trade-off between quality, latency, and cost.")


if __name__ == "__main__":
    main()
