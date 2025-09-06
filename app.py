import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Trading Dashboard — MVP")
st.caption("Upload a CSV of trades and preview it below.")

# File uploader (CSV only)
file = st.file_uploader("Upload CSV", type=["csv"])

if file is not None:
    try:
        df = pd.read_csv(file)
    except Exception:
        st.error("Could not read that file. Make sure it’s a CSV.")
        st.stop()

    st.subheader("Preview")
    st.dataframe(df.head(50), use_container_width=True)

    # ---- Use only Exit rows for stats/curve ----
    df_exits = df[df["type"].str.lower() == "exit"].copy()

    # Coerce types
    df_exits["date_time"] = pd.to_datetime(df_exits["date_time"], errors="coerce")
    df_exits["net_pnl"]   = pd.to_numeric(df_exits["net_pnl"], errors="coerce")

    # Drop rows missing key fields, sort by time
    df_exits = df_exits.dropna(subset=["date_time", "net_pnl"]).sort_values("date_time")

    # ---- KPIs ----
    total_trades = len(df_exits)
    wins   = (df_exits["net_pnl"] > 0).sum()
    losses = (df_exits["net_pnl"] <= 0).sum()
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    net_pnl_sum = df_exits["net_pnl"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Trades", total_trades)
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Net PnL", f"${net_pnl_sum:,.2f}")

    # ---- Equity curve (cumulative PnL over time) ----
    if not df_exits.empty:
        df_exits["equity"] = df_exits["net_pnl"].cumsum()
        fig = px.line(df_exits, x="date_time", y="equity", title="Equity Curve (Exits Only)")
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=360, xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No exit rows with PnL found to plot the equity curve.")

    # Raw row count (includes entries)
    st.caption(f"Rows detected (including entries): **{len(df):,}**")

else:
    st.info("Choose a CSV file to begin.")
