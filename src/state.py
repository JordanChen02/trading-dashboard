# src/state.py
from __future__ import annotations
import pandas as pd
import streamlit as st

def _first_of_month(ts) -> pd.Timestamp:
    ts = pd.to_datetime(ts, errors="coerce")
    if pd.isna(ts):
        ts = pd.Timestamp.today()
    return pd.Timestamp(year=ts.year, month=ts.month, day=1)

def ensure_defaults(date_series: pd.Series | None = None) -> None:
    """
    Idempotently seed Streamlit session-state keys used across views.
    Call this once early in app startup (after you know date_series).
    """
    # Calendar month start — prefer LAST date in the current dataset; else today
    if "_cal_month_start" not in st.session_state:
        if date_series is not None and len(date_series) > 0:
            ds = pd.to_datetime(date_series, errors="coerce").dropna()
            base = ds.max() if len(ds) else pd.Timestamp.today()
        else:
            base = pd.Timestamp.today()
        st.session_state["_cal_month_start"] = _first_of_month(base)

    # Height used by some charts as a fallback (e.g., equity)
    st.session_state.setdefault("_cal_height", 240)

    # Daily/Weekly toggle default for PnL
    st.session_state.setdefault("_dpnl_mode", "Daily")

    # Whether we already hinted the user about filters
    st.session_state.setdefault("_filters_prompted", False)
