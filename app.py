import streamlit as st
import pandas as pd

# 👇 our modules
from src.io import load_trades, validate
from src.metrics import add_pnl

st.set_page_config(page_title="Trading Dashboard — MVP", layout="wide")
st.title("Trading Dashboard — MVP")
st.caption("Upload a CSV of trades and preview it below.")

# Upload
file = st.file_uploader("Upload CSV", type=["csv"])

if file is not None:
    # 1) Load
    try:
        df = load_trades(file)
    except Exception as e:
        st.error(f"Could not read that file: {e}")
        st.stop()

    # 2) Validate
    issues = validate(df)
    if issues:
        st.error("We found issues in your CSV:")
        for i, msg in enumerate(issues, start=1):
            st.write(f"{i}. {msg}")
        st.stop()

    # 3) Derive PnL
    df = add_pnl(df)

    # 4) Preview
    st.subheader("Preview (first 50 rows)")
    st.dataframe(df.head(50), use_container_width=True)

        # === KPIs ===
    st.subheader("Key Stats")

    total_trades = len(df)
    wins = (df["pnl"] > 0).sum()
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

    c1, c2 = st.columns(2)
    c1.metric("Total Trades", f"{total_trades}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")

