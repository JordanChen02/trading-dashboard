# src/views/checklist.py
from __future__ import annotations

import pandas as pd  # keep df signature consistent with other pages
import streamlit as st


def render(df: pd.DataFrame) -> None:
    # Simple header with a small SVG icon
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:.5rem;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
               xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M9 11l3 3L22 4" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"
                  stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <h2 style="margin:0;">Checklist</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Placeholder page — we’ll build the editor here next.")
