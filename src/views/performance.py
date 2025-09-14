# src/views/performance.py
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.charts.drawdown import plot_underwater


def render(
    df_view: pd.DataFrame,
    start_equity: float,
    date_col: Optional[str],
    tf: str,
    win_rate_v: float,
    avg_win_v: float,
    avg_loss_v: float,
) -> None:
    """Render the Performance tab (KPIs, Underwater, Daily PnL, Export)."""

    # ---- Header ----
    st.subheader("Performance KPIs")
    st.caption(f"Using Range: **{tf}**")

    # --- Prepare series on df_view (timeframe-aware) ---
    pnl_tf = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
    wins_m = pnl_tf > 0
    loss_m = pnl_tf < 0

    gross_profit = float(pnl_tf[wins_m].sum())
    gross_loss = float(pnl_tf[loss_m].sum())  # negative or 0
    net_profit = float(pnl_tf.sum())

    largest_win = float(pnl_tf[wins_m].max()) if wins_m.any() else 0.0
    largest_loss = float(pnl_tf[loss_m].min()) if loss_m.any() else 0.0  # most negative

    win_count = int(wins_m.sum())
    loss_count = int(loss_m.sum())

    # Win/Loss count ratio (avoid div by zero)
    wl_count_ratio = (win_count / loss_count) if loss_count > 0 else float("inf")

    # Profit Factor in timeframe
    pf_tf = (gross_profit / abs(gross_loss)) if gross_loss != 0 else float("inf")

    # Commission (if present)
    _fee_cols = [c for c in ["commission", "fee", "fees", "commissions"] if c in df_view.columns]
    commission_paid = (
        float(pd.to_numeric(df_view[_fee_cols[0]], errors="coerce").fillna(0.0).sum())
        if _fee_cols
        else 0.0
    )

    # --- Timeframe-aware risk KPIs ---
    # Equity over df_view so DD and balance match the selected Range
    dfv_perf = df_view.copy().reset_index(drop=True)
    dfv_perf["trade_no"] = np.arange(1, len(dfv_perf) + 1)
    dfv_perf["cum_pnl"] = pd.to_numeric(dfv_perf["pnl"], errors="coerce").fillna(0).cumsum()
    dfv_perf["equity"] = start_equity + dfv_perf["cum_pnl"]
    dfv_perf["peak"] = dfv_perf["equity"].cummax()

    max_dd_pct_tf = (
        float(((dfv_perf["equity"] / dfv_perf["peak"]) - 1.0).min() * 100.0)
        if len(dfv_perf) and (dfv_perf["peak"] > 0).any()
        else 0.0
    )
    current_balance_tf = float(dfv_perf["equity"].iloc[-1]) if len(dfv_perf) else start_equity

    # Expectancy per trade within the selected Range
    win_rate_frac_v = float(win_rate_v)  # win_rate_v is already in [0..1]
    loss_rate_frac_v = 1.0 - win_rate_frac_v
    expectancy_v = (win_rate_frac_v * float(avg_win_v)) + (loss_rate_frac_v * float(avg_loss_v))

    # --- KPI rows ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Gross Profit", f"${gross_profit:,.2f}")
    k2.metric("Gross Loss", f"${gross_loss:,.2f}")
    k3.metric("Net Profit", f"${net_profit:,.2f}")
    k4.metric("Profit Factor", "∞" if pf_tf == float("inf") else f"{pf_tf:.2f}")

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Largest Win", f"${largest_win:,.2f}")
    k6.metric("Largest Loss", f"${largest_loss:,.2f}")
    k7.metric(
        "Win/Loss (count)", "∞" if wl_count_ratio == float("inf") else f"{wl_count_ratio:.2f}"
    )
    k8.metric("Commission Paid", f"${commission_paid:,.2f}")

    k9, k10, k11 = st.columns(3)
    k9.metric("Max Drawdown % (Range)", f"{max_dd_pct_tf:.2f}%")
    k10.metric("Current Balance (Range)", f"${current_balance_tf:,.2f}")
    k11.metric("Expectancy / Trade", f"${expectancy_v:,.2f}")

    # --- Additional Risk KPIs (timeframe-aware) ---
    _p_tf = pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0)
    _eq = start_equity + _p_tf.cumsum()
    _peak = _eq.cummax()
    _dd_abs_series = _eq - _peak  # ≤ 0 in $
    _dd_pct_series = np.where(_peak > 0, (_eq / _peak) - 1.0, 0.0)

    def _longest_run(mask: np.ndarray) -> int:
        longest = cur = 0
        for v in mask:
            if v:
                cur += 1
                if cur > longest:
                    longest = cur
            else:
                cur = 0
        return int(longest)

    _max_dd_abs_usd = float(_dd_abs_series.min()) if len(_dd_abs_series) else 0.0  # negative or 0
    _max_dd_duration_trades = _longest_run(_dd_pct_series < 0) if len(_dd_pct_series) else 0
    _longest_losing_streak = _longest_run(_p_tf.values < 0) if len(_p_tf) else 0

    r1, r2, r3 = st.columns(3)
    r1.metric("Max DD ($)", f"${_max_dd_abs_usd:,.0f}")
    r2.metric("Max DD Duration", f"{_max_dd_duration_trades} trades")
    r3.metric("Longest Losing Streak", f"{_longest_losing_streak} trades")

    st.divider()

    # -------- Underwater (Drawdown %) [timeframe-aware] --------
    st.markdown("#### Underwater (Drawdown %)")

    show_vline = st.checkbox("Show Max DD vertical line", value=True, key="uw_show_maxdd_vline")
    show_label = st.checkbox("Show Max DD label", value=True, key="uw_show_maxdd_label")

    fig_dd, dd_stats = plot_underwater(
        df_view,
        start_equity=start_equity,
        date_col=date_col,
        show_vline=show_vline,
        show_label=show_label,
        height=220,
    )

    st.caption(
        f"Current DD: **{dd_stats['current_dd_pct']:.2f}%**  (${dd_stats['current_dd_abs']:,.0f})"
    )
    st.plotly_chart(fig_dd, use_container_width=True)
    st.caption(dd_stats["recover_msg"])

    st.divider()

    # -------- Daily Net PnL (timeframe-aware) --------
    st.markdown("#### Daily Net PnL")
    if date_col is not None and date_col in df_view.columns and len(df_view) > 0:
        _d = pd.to_datetime(df_view[date_col], errors="coerce")
        _daily = (
            pd.DataFrame(
                {
                    "day": _d.dt.date,
                    "pnl": pd.to_numeric(df_view["pnl"], errors="coerce").fillna(0.0),
                }
            )
            .groupby("day", as_index=False)["pnl"]
            .sum()
            .sort_values("day")
        )

        fig_daily = px.bar(
            _daily,
            x="day",
            y="pnl",
            title=None,
            labels={"day": "Day", "pnl": "Net PnL ($)"},
        )
        # zero line + compact styling
        fig_daily.add_hline(y=0, line_width=1, line_dash="dot", opacity=0.6)
        fig_daily.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        fig_daily.update_yaxes(tickprefix="$", separatethousands=True)
        st.plotly_chart(fig_daily, use_container_width=True)
    else:
        st.caption(
            "No date/timestamp column found — Daily Net PnL is unavailable for this dataset."
        )

    st.divider()

    # -------- Export filtered trades --------
    st.markdown("#### Export")
    _export_df = df_view.copy()
    # Optional: reorder common columns if present
    _preferred_cols = [
        c
        for c in [
            "datetime",
            "date",
            "timestamp",
            "symbol",
            "side",
            "qty",
            "price",
            "pnl",
            "commission",
            "fees",
            "tag",
            "note",
        ]
        if c in _export_df.columns
    ]
    _export_df = _export_df[
        _preferred_cols + [c for c in _export_df.columns if c not in _preferred_cols]
    ]

    _fname_tf = tf.lower().replace(" ", "_")  # all / this_week / this_month / this_year
    _fname = f"trades_filtered_{_fname_tf}.csv"

    _csv = _export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⤓ Download filtered trades (CSV)",
        data=_csv,
        file_name=_fname,
        mime="text/csv",
        use_container_width=True,
    )
