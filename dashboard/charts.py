from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


def render_metric_bars(rows: list[dict[str, Any]], metric: str, label: str) -> None:
    frame = pd.DataFrame(rows)
    if frame.empty or metric not in frame:
        return
    st.plotly_chart(
        px.bar(frame, x="configuration_id", y=metric, title=label),
        use_container_width=True,
    )
