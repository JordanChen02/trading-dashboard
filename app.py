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

    # === More KPIs ===
    profits = df.loc[df["pnl"] > 0, "pnl"]
    losses  = df.loc[df["pnl"] < 0, "pnl"]

    profit_sum = float(profits.sum())
    loss_sum   = float(losses.sum())  # negative number or 0

    profit_factor = (profit_sum / abs(loss_sum)) if loss_sum != 0 else float("inf")
    expectancy    = float(df["pnl"].mean()) if len(df) else 0.0
    avg_win       = float(profits.mean()) if len(profits) else 0.0
    avg_loss      = float(losses.mean())  if len(losses)  else 0.0  # will be negative if any losses

    # Max Drawdown (absolute and %)
    equity = df["pnl"].cumsum()
    roll_peak = equity.cummax()
    dd = equity - roll_peak                      # <= 0
    max_dd_abs = float(dd.min())                 # most negative
    max_dd_pct = float(((equity / roll_peak) - 1.0).min() * 100) if (roll_peak > 0).any() else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Profit Factor", "∞" if profit_factor == float("inf") else f"{profit_factor:.2f}")
    c2.metric("Expectancy (per trade)", f"${expectancy:,.2f}")
    c3.metric("Max Drawdown", f"${max_dd_abs:,.2f}  ({max_dd_pct:.1f}%)")

    c4, c5 = st.columns(2)
    c4.metric("Avg Win", f"${avg_win:,.2f}")
    c5.metric("Avg Loss", f"${avg_loss:,.2f}")
