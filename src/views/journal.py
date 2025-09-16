# src/views/journal.py
from __future__ import annotations

import pandas as pd
import streamlit as st


def render(df: pd.DataFrame) -> None:
    st.title("Journal")
    st.caption("Filters + table live here (temporary home).")

    # ===== Filters (moved here) =====
    symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
    sides = sorted(df["side"].dropna().unique().tolist()) if "side" in df.columns else []

    c1, c2, c3 = st.columns([2, 2, 3], gap="small")
    with c1:
        sel_symbols = st.multiselect("Symbol", symbols, default=symbols if symbols else [])
    with c2:
        sel_sides = st.multiselect("Side", sides, default=sides if sides else [])

    # Tag options: pull from df + any in-session tags
    _tags_present = set()
    if "tag" in df.columns:
        _tags_present |= set(df["tag"].dropna().astype(str).str.strip().tolist())
    _tags_present |= set(st.session_state.get("_trade_tags", {}).values())
    _known_order = ["A+", "A", "B", "C"]
    tag_options = [t for t in _known_order if t in _tags_present]

    with c3:
        sel_tags = st.multiselect(
            "Tag",
            options=tag_options,
            default=tag_options if tag_options else [],
            help="Grades applied to trades (A+, A, B, C).",
        )

    # Apply filters locally on this page
    df_filtered = df.copy()
    if "symbol" in df_filtered.columns and sel_symbols:
        df_filtered = df_filtered[df_filtered["symbol"].isin(sel_symbols)]
    if "side" in df_filtered.columns and sel_sides:
        df_filtered = df_filtered[df_filtered["side"].isin(sel_sides)]
    if "tag" in df_filtered.columns and sel_tags:
        df_filtered = df_filtered[df_filtered["tag"].isin(sel_tags)]

    st.divider()
    st.subheader(f"Rows: {len(df_filtered)}")

    if "entry_time" in df_filtered.columns:
        df_filtered = df_filtered.sort_values("entry_time", ascending=False)

    st.dataframe(df_filtered, use_container_width=True, height=480)


# ===================== FILTERS (render after df exists) =====================
# Recreate the sidebar expander now that df is available
#     with st.sidebar.expander("Filters", expanded=True):
#         symbols = sorted(df["symbol"].dropna().unique().tolist()) if "symbol" in df.columns else []
#         sides = sorted(df["side"].dropna().unique().tolist()) if "side" in df.columns else []

#         sel_symbols = st.multiselect("Symbol", symbols, default=symbols if symbols else [])
#         sel_sides = st.multiselect("Side", sides, default=sides if sides else [])
#         # --- Tag filter (A+/A/B/C) ---
#         # We gather possible tags from the DataFrame if present, plus any in-session tags.
#         _tags_present = set()
#         if "tag" in df.columns:
#             _tags_present |= set(
#                 df["tag"].dropna().astype(str).str.strip().tolist()
#             )  # |= is set-union assignment

#         _tags_present |= set(st.session_state.get("_trade_tags", {}).values())

#         # Keep only known tag grades in a nice order
#         _known_order = ["A+", "A", "B", "C"]
#         tag_options = [t for t in _known_order if t in _tags_present]

#         sel_tags = st.multiselect(
#             "Tag",
#             options=tag_options,
#             default=tag_options if tag_options else [],
#             help="Quick grades you’ve applied to trades (A+, A, B, C).",
#         )

# # Apply filters
# df_filtered = df.copy()
# if "symbol" in df_filtered.columns and sel_symbols:
#     df_filtered = df_filtered[df_filtered["symbol"].isin(sel_symbols)]
# if "side" in df_filtered.columns and sel_sides:
#     df_filtered = df_filtered[df_filtered["side"].isin(sel_sides)]
# if "tag" in df_filtered.columns and sel_tags:
#     df_filtered = df_filtered[df_filtered["tag"].isin(sel_tags)]

# if df_filtered.empty:
#     st.info("No rows match the current filters. Adjust filters in the sidebar.")
#     st.stop()

# # From here on, keep your existing code but make it operate on the filtered data:
# df = df_filtered
