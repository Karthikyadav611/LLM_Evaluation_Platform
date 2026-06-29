from typing import Any

import streamlit as st


def get_session_api_keys() -> dict[str, str]:
    return st.session_state.setdefault("api_keys", {})


def set_session_api_key(provider: str, value: str) -> None:
    keys = get_session_api_keys()
    if value:
        keys[provider] = value
    elif provider in keys:
        del keys[provider]


def set_active_results(results: Any) -> None:
    st.session_state["active_results"] = results


def get_active_results() -> Any:
    return st.session_state.get("active_results")
