# src/state.py
from __future__ import annotations

import pandas as pd
import streamlit as st


def ensure_defaults() -> None:
    """Initialize Streamlit session_state defaults once."""
    if "_dpnl_mode" not in st.session_state:
        st.session_state["_dpnl_mode"] = "Daily"
    if "_filters_prompted" not in st.session_state:
        st.session_state["_filters_prompted"] = False
    # Month start used by Calendar (first day of current month)
    if "_cal_month_start" not in st.session_state:
        st.session_state["_cal_month_start"] = pd.Timestamp.today().normalize().replace(day=1)
