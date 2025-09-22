# src/views/performance.py
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.charts.drawdown import plot_underwater


def _fmt_duration_minutes(total_min: float | None) -> str:
    """Turn minutes into 'Xd Yh Zm'."""
    if total_min is None:
        return "—"
    m = max(0, int(round(total_min)))
    d, rem = divmod(m, 1440)  # 60*24
    h, mm = divmod(rem, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if mm or not parts:
        parts.append(f"{mm}m")
    return " ".join(parts)


# ---------- helpers ----------
def _money(x: float) -> str:
    return f"${x:,.2f}"


def _int(x: int) -> str:
    return f"{int(x):,}"


def _exists_any(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _colorize(val: float, mode: str = "signed") -> str:
    """
    'signed': green if >0, red if <0, default grey if 0
    'ratio':  green if >1, red if <1, grey if ==1
    'risk':   always red (for risk metrics like DD)
    """
    if mode == "signed":
        return "#61D0A8" if val > 0 else ("#ef4444" if val < 0 else "#e5e7eb")
    if mode == "ratio":
        if np.isinf(val):
            return "#e5e7eb"
        return "#61D0A8" if val > 1 else ("#ef4444" if val < 1 else "#e5e7eb")
    if mode == "risk":
        return "#E06B6B"
    return "#e5e7eb"


def _line(label: str, value_html: str) -> None:
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;margin:2px 0'>"
        f"<span style='color:#9aa6bd'>{label}</span>"
        f"<span style='font-weight:700'>{value_html}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------- main render ----------
def render(
    df_view: pd.DataFrame,
    start_equity: float,
    date_col: Optional[str],
    tf: str,
    win_rate_v: float,  # 0..1 already (from router)
    avg_win_v: float,
    avg_loss_v: float,
) -> None:
    """
    Performance tab – condensed KPIs (1 row, 3 cols) + 2x2 chart grid.
    Timeframe-aware: all stats computed from df_view.
    """

    st.subheader("Performance")
    st.caption(f"Using Range: **{tf}**")

    # ========= CORE SERIES (timeframe-aware) =========
    pnl = pd.to_numeric(df_view.get("pnl", 0.0), errors="coerce").fillna(0.0)
    wins_mask = pnl > 0
    losses_mask = pnl < 0

    gross_profit = float(pnl[wins_mask].sum())
    gross_loss = float(pnl[losses_mask].sum())  # negative or 0
    net_profit = float(pnl.sum())

    largest_win = float(pnl[wins_mask].max()) if wins_mask.any() else 0.0
    largest_loss = float(pnl[losses_mask].min()) if losses_mask.any() else 0.0

    win_ct = int(wins_mask.sum())
    loss_ct = int(losses_mask.sum())
    wl_ratio = (win_ct / loss_ct) if loss_ct > 0 else float("inf")

    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else float("inf")

    # commissions if present
    fee_col = _exists_any(df_view, ["commission", "commissions", "fee", "fees"])
    commission_paid = (
        float(pd.to_numeric(df_view[fee_col], errors="coerce").fillna(0.0).sum())
        if fee_col
        else 0.0
    )

    # equity + drawdown within the selected range
    equity = start_equity + pnl.cumsum()
    peak = equity.cummax()
    dd_abs = equity - peak
    dd_pct = np.where(peak > 0, (equity / peak) - 1.0, 0.0)

    max_dd_abs = float(dd_abs.min()) if len(dd_abs) else 0.0  # negative or 0
    max_dd_pct = float(dd_pct.min()) * 100.0 if len(dd_pct) else 0.0
    current_balance = float(equity.iloc[-1]) if len(equity) else float(start_equity)

    # recovery factor = net profit / |max DD $|
    recovery = (net_profit / abs(max_dd_abs)) if max_dd_abs != 0 else float("inf")

    # expectancy per trade (use avg_loss as negative)
    wr = float(win_rate_v)
    expectancy = wr * float(avg_win_v) + (1.0 - wr) * float(avg_loss_v)

    # activity (optional date/hold-time fields)
    total_trades = int(len(df_view))

    # trading days & trades/day
    date_like = (
        date_col
        if (date_col and date_col in df_view.columns)
        else _exists_any(
            df_view,
            [
                "date",
                "Date",
                "timestamp",
                "Timestamp",
                "time",
                "Time",
                "datetime",
                "Datetime",
                "entry_time",
            ],
        )
    )
    trading_days = None
    trades_per_day = None
    if date_like is not None and len(df_view) > 0:
        _dt = pd.to_datetime(df_view[date_like], errors="coerce")
        trading_days = int(_dt.dt.date.nunique())
        trades_per_day = (total_trades / trading_days) if trading_days > 0 else 0.0

    # avg hold time
    et_col = _exists_any(df_view, ["entry_time", "Entry Time"])
    xt_col = _exists_any(df_view, ["exit_time", "Exit Time"])
    avg_hold_min = None
    if et_col and xt_col:
        # --- avg & total hold time (only if both columns exist) ---
        et_col = _exists_any(df_view, ["entry_time", "Entry Time"])
        xt_col = _exists_any(df_view, ["exit_time", "Exit Time"])
        avg_hold_min = None
        total_hold_min = None
        if et_col and xt_col:
            try:
                dur_sec = (
                    pd.to_datetime(df_view[xt_col]) - pd.to_datetime(df_view[et_col])
                ).dt.total_seconds()
                dur_min = pd.to_numeric(dur_sec, errors="coerce").dropna() / 60.0
                if len(dur_min):
                    avg_hold_min = float(dur_min.mean())
                    total_hold_min = float(dur_min.sum())
            except Exception:
                pass

    # ========= KPI ROW (single container; 3 columns) =========
    with st.container(border=True):
        c1, c2, c3 = st.columns(3, gap="large")

        # --- Profitability (plain numbers, sign-colored) ---
        with c1:
            st.markdown("**Profitability**")
            _line(
                "Gross Profit",
                f"<span style='color:{_colorize(gross_profit)}'>{_money(gross_profit)}</span>",
            )
            _line(
                "Gross Loss",
                f"<span style='color:{_colorize(gross_loss)}'>{_money(gross_loss)}</span>",
            )
            _line(
                "Net Profit",
                f"<span style='color:{_colorize(net_profit)}'>{_money(net_profit)}</span>",
            )
            _line(
                "Largest Win",
                f"<span style='color:{_colorize(largest_win)}'>{_money(largest_win)}</span>",
            )
            _line(
                "Largest Loss",
                f"<span style='color:{_colorize(largest_loss)}'>{_money(largest_loss)}</span>",
            )
            pf_txt = "∞" if np.isinf(profit_factor) else f"{profit_factor:.2f}"
            _line(
                "Profit Factor",
                f"<span style='color:{_colorize(profit_factor,'ratio')}'>{pf_txt}</span>",
            )
            wl_txt = "∞" if np.isinf(wl_ratio) else f"{wl_ratio:.2f}"
            _line("Win/Loss (count)", wl_txt)
            _line(
                "Expectancy / Trade",
                f"<span style='color:{_colorize(expectancy)}'>{_money(expectancy)}</span>",
            )
            _line("Commission Paid", _money(commission_paid))

        # --- Activity ---
        with c2:
            st.markdown("**Activity**")
            _line("Total Trades", _int(total_trades))
            if trading_days is not None:
                _line("Trading Days", _int(trading_days))
                _line("Trades / Day", f"{trades_per_day:.2f}")
            if avg_hold_min is not None:
                _line("Avg Hold Time", f"{avg_hold_min:.1f} min")
            if total_hold_min is not None:
                _line("Total Hold Time", _fmt_duration_minutes(total_hold_min))

        # --- Risk & Consistency (compact lines) ---
        with c3:
            st.markdown("**Risk & Consistency**")
            _line(
                "Max DD ($)",
                f"<span style='color:{_colorize(-1,'risk')}'>{_money(max_dd_abs)}</span>",
            )
            _line(
                "Max DD (%)", f"<span style='color:{_colorize(-1,'risk')}'>{max_dd_pct:.2f}%</span>"
            )
            rec_txt = "∞" if np.isinf(recovery) else f"{recovery:.2f}"
            _line(
                "Recovery Factor",
                f"<span style='color:{_colorize(recovery,'ratio')}'>{rec_txt}</span>",
            )

            # durations/streaks (trade-based)
            def _longest(mask: np.ndarray) -> int:
                cur = best = 0
                for v in mask:
                    cur = cur + 1 if v else 0
                    best = max(best, cur)
                return int(best)

            longest_losing = _longest(pnl.values < 0) if len(pnl) else 0
            max_dd_duration = _longest(dd_pct < 0) if len(dd_pct) else 0
            _line("Max DD Duration", f"{_int(max_dd_duration)} trades")
            _line("Longest Losing Streak", f"{_int(longest_losing)} trades")
            _line("Current Balance", _money(current_balance))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ========= CHART GRID (2 columns) =========
    # Row 1: Underwater | Daily Net PnL
    colA, colB = st.columns(2, gap="large")

    with colA:
        st.markdown("#### Underwater (Drawdown %)")
        show_vline = st.checkbox("Show Max DD vertical line", value=True, key="uw_vline_perf")
        show_label = st.checkbox("Show Max DD label", value=True, key="uw_label_perf")
        fig_dd, dd_stats = plot_underwater(
            df_view,
            start_equity=start_equity,
            date_col=date_col,
            show_vline=show_vline,
            show_label=show_label,
            height=260,
        )
        st.caption(
            f"Current DD: **{dd_stats['current_dd_pct']:.2f}%** (${dd_stats['current_dd_abs']:,.0f})"
        )
        st.plotly_chart(fig_dd, use_container_width=True)

    with colB:
        st.markdown("#### Daily Net PnL")
        if date_col is not None and date_col in df_view.columns and len(df_view) > 0:
            _d = pd.to_datetime(df_view[date_col], errors="coerce")
            _daily = (
                pd.DataFrame({"day": _d.dt.date, "pnl": pnl})
                .groupby("day", as_index=False)["pnl"]
                .sum()
                .sort_values("day")
            )
            fig_daily = px.bar(
                _daily, x="day", y="pnl", title=None, labels={"day": "Day", "pnl": "Net PnL ($)"}
            )
            fig_daily.add_hline(y=0, line_width=1, line_dash="dot", opacity=0.6)
            fig_daily.update_layout(
                height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False
            )
            fig_daily.update_yaxes(tickprefix="$", separatethousands=True)
            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.caption(
                "No date/timestamp column found — Daily Net PnL is unavailable for this dataset."
            )

    # Row 2: PnL Distribution | Profit by Symbol (if present)
    colC, colD = st.columns(2, gap="large")

    with colC:
        st.markdown("#### PnL Distribution (per trade)")
        fig_hist = px.histogram(pnl, nbins=40)
        fig_hist.update_traces(hovertemplate="Count: %{y}<br>PnL: %{x:$,.0f}<extra></extra>")
        fig_hist.add_vline(x=0, line_width=1, line_dash="dot", opacity=0.7)
        pos = pnl[pnl > 0]
        if pos.size:
            fig_hist.add_vline(x=float(pos.mean()), line_width=1, line_dash="dash", opacity=0.4)
        neg = pnl[pnl < 0]
        if neg.size:
            fig_hist.add_vline(x=float(neg.mean()), line_width=1, line_dash="dash", opacity=0.4)
        fig_hist.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)

    with colD:
        if "symbol" in df_view.columns:
            st.markdown("#### Profit by Symbol")
            sym = (
                df_view.assign(_p=pnl)
                .groupby("symbol", as_index=False)["_p"]
                .sum()
                .sort_values("_p", ascending=True)
            )
            fig_sym = px.bar(
                sym,
                x="_p",
                y="symbol",
                orientation="h",
                labels={"_p": "Net PnL ($)", "symbol": "Symbol"},
            )
            fig_sym.add_vline(x=0, line_width=1, line_dash="dot", opacity=0.6)
            fig_sym.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            fig_sym.update_xaxes(tickprefix="$", separatethousands=True)
            st.plotly_chart(fig_sym, use_container_width=True)

    st.divider()

    # ========= Export (unchanged behavior) =========
    st.markdown("#### Export")
    _export_df = df_view.copy()
    preferred = [
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
    _cols = [c for c in preferred if c in _export_df.columns] + [
        c for c in _export_df.columns if c not in preferred
    ]
    _export_df = _export_df[_cols]
    _fname = f"trades_filtered_{tf.lower().replace(' ', '_')}.csv"
    st.download_button(
        label="⤓ Download filtered trades (CSV)",
        data=_export_df.to_csv(index=False).encode("utf-8"),
        file_name=_fname,
        mime="text/csv",
        use_container_width=True,
    )
