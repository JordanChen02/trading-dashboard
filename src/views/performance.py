# src/views/performance.py
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.styles import inject_plot_rounding_css
from src.theme import AXIS_WEAK, BLUE, BLUE_FILL, BLUE_LIGHT, CARD_BG, FG, FG_MUTED, GRID_WEAK, RED

# ========= Adjustable UI tokens =========
PAGE_TOP_PADDING_PX = 20  # pushes the whole Performance page down a bit
KPI_TOP_PADDING_PX = 16  # space above the KPI block (below page padding)
KPI_VRULE_HEIGHT_PX = 190  # height of vertical dividers between KPI columns
DIVIDER_MARGIN_PX = 12  # extra space above & below the horizontal divider
CHART_HEIGHT_PX = 370  # overall height for each chart
TITLE_TOP_MARGIN = 52  # inside-figure space reserved for the title
TITLE_X = 0.04  # try 0.03–0.06; 0 = hard left, 0.5 = center


TEAL = "#4FD1C5"  # accent line color


# ================ Small helpers ================
def _fmt_duration_minutes(total_min: float | None) -> str:
    if total_min is None:
        return "—"
    m = max(0, int(round(float(total_min))))
    d, m = divmod(m, 1440)
    h, m = divmod(m, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m or not parts:
        parts.append(f"{m}m")
    return " ".join(parts)


def _money(x: float) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "—"


def _int(x) -> str:
    try:
        return f"{int(x):,d}"
    except Exception:
        return "—"


def _exists_any(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _colorize(val: float, mode: str = "signed") -> str:
    """
    signed : positive -> green, negative -> RED
    ratio  : >1 -> green, <1 -> RED (∞ stays neutral)
    risk   : always RED (for DD, streaks text, etc.)
    """
    if mode == "signed":
        return "#61D0A8" if val > 0 else (RED if val < 0 else FG)
    if mode == "ratio":
        if np.isinf(val):
            return FG
        return "#61D0A8" if val > 1 else (RED if val < 1 else FG)
    if mode == "risk":
        return RED
    return FG


def _line(label: str, value_html: str) -> None:
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;margin:2px 0'>"
        f"<span style='color:{FG_MUTED}'>{label}</span>"
        f"<span style='font-weight:700'>{value_html}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _rolling(values: pd.Series, window: int) -> pd.Series:
    if len(values) == 0:
        return values
    return values.rolling(window=window, min_periods=1).mean()


def _longest_losing_streak(pnl: pd.Series) -> int:
    streak = longest = 0
    for v in pnl:
        if v < 0:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 0
    return int(longest)


# ================ R / Risk helpers ================
def _risk_series(df: pd.DataFrame) -> Optional[pd.Series]:
    risk_col = _exists_any(
        df,
        ["Dollars Risked", "Dollar Risk", "Risk $", "risk_usd", "risk", "max_loss", "planned_loss"],
    )
    if risk_col is None:
        return None
    return pd.to_numeric(df[risk_col], errors="coerce").abs()


def _r_series(df: pd.DataFrame, pnl: pd.Series, risk: Optional[pd.Series]) -> Optional[pd.Series]:
    r_col = _exists_any(df, ["R Ratio", "r_ratio", "R", "r"])
    if r_col is not None:
        return pd.to_numeric(df[r_col], errors="coerce")
    if risk is not None:
        _risk = risk.replace(0, np.nan)
        return (pnl / _risk).replace([np.inf, -np.inf], np.nan)
    return None


# ================ Date-based aggregations ================
def _normalize_date(s: pd.Series) -> pd.Series:
    dt = pd.to_datetime(s, errors="coerce")
    return pd.to_datetime(dt.dt.date)


def _daily_pnl(dates: pd.Series, pnl: pd.Series) -> pd.DataFrame:
    d = pd.DataFrame({"date": _normalize_date(dates), "pnl": pnl})
    d = d.dropna(subset=["date"])
    by = d.groupby("date", as_index=False)["pnl"].sum()
    return by.sort_values("date")


def _daily_win_loss(dates: pd.Series, pnl: pd.Series) -> pd.DataFrame:
    d = pd.DataFrame({"date": _normalize_date(dates), "pnl": pnl})
    d = d.dropna(subset=["date"])
    d["win"] = (d["pnl"] > 0).astype(int)
    agg = d.groupby("date", as_index=False).agg(
        trades=("pnl", "size"), wins=("win", "sum"), exp=("pnl", "mean")
    )
    return agg.sort_values("date")


def _daily_r(dates: pd.Series, r: pd.Series) -> pd.DataFrame:
    d = pd.DataFrame({"date": _normalize_date(dates), "R": pd.to_numeric(r, errors="coerce")})
    d = d.dropna(subset=["date", "R"])
    by = d.groupby("date", as_index=False)["R"].sum()
    return by.sort_values("date")


# ================ Base figure styling ================
def _base_layout(fig: go.Figure, title_text: str, height: int = CHART_HEIGHT_PX) -> go.Figure:
    fig.update_layout(
        title=dict(text=title_text, x=TITLE_X, xanchor="left", font=dict(size=15, color=FG)),
        height=height,
        margin=dict(l=8, r=8, t=TITLE_TOP_MARGIN, b=12),  # extra headroom for title
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
    )
    fig.update_xaxes(color=FG_MUTED, showgrid=False)
    fig.update_yaxes(color=FG_MUTED, gridcolor=GRID_WEAK)
    return fig


# ================ Figures ================
def _fig_underwater_daily(start_equity: float, daily_pnl_df: pd.DataFrame) -> go.Figure:
    if daily_pnl_df.empty:
        return _base_layout(go.Figure(), "Underwater (Drawdown %)")
    eq = start_equity + daily_pnl_df["pnl"].cumsum()
    peak = eq.cummax()
    dd_pct = np.where(peak > 0, (eq / peak) - 1.0, 0.0) * 100.0
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily_pnl_df["date"],
            y=dd_pct,
            mode="lines",
            line=dict(color=BLUE_LIGHT, width=2.8),
            fill="tozeroy",
            fillcolor=BLUE_FILL,
            name="Drawdown %",
        )
    )
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color=AXIS_WEAK)
    # Axis titles
    fig.update_yaxes(title_text="Drawdown (%)")
    fig.update_xaxes(title_text="Date")
    return _base_layout(fig, "Underwater (Drawdown %)")


def _fig_cum_r_by_date(daily_r_df: pd.DataFrame) -> go.Figure:
    if daily_r_df.empty:
        return _base_layout(go.Figure(), "Cumulative R")
    cum_r = daily_r_df["R"].cumsum()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=daily_r_df["date"], y=cum_r, mode="lines", line=dict(color=BLUE, width=2))
    )
    # Axis titles
    fig.update_yaxes(title_text="Cumulative R")
    fig.update_xaxes(title_text="Date")
    return _base_layout(fig, "Cumulative R")


def _fig_rolling_20d(daily_stats: pd.DataFrame) -> go.Figure:
    if daily_stats.empty:
        return _base_layout(go.Figure(), "Rolling Metrics")
    s = daily_stats.set_index("date").sort_index()
    daily_wr = (s["wins"] / s["trades"]).replace([np.inf, -np.inf], np.nan)
    roll_wr = daily_wr.rolling(20, min_periods=1).mean() * 100.0
    roll_exp = s["exp"].rolling(20, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=roll_wr.index,
            y=roll_wr.values,
            mode="lines",
            name="Rolling Win %",
            line=dict(color=BLUE, width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=roll_exp.index,
            y=roll_exp.values,
            mode="lines",
            name="Rolling Expectancy $",
            yaxis="y2",
            line=dict(color=TEAL, width=2),
        )
    )
    fig.update_layout(
        yaxis=dict(title="Win %", range=[0, 100], color=FG_MUTED, gridcolor=GRID_WEAK),
        yaxis2=dict(
            title="Exp ($)", overlaying="y", side="right", color=FG_MUTED, gridcolor="rgba(0,0,0,0)"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
    )
    return _base_layout(fig, "Rolling Metrics")


def _fig_trade_scatter_r(
    dates: pd.Series, r: pd.Series, risk: Optional[pd.Series] = None
) -> go.Figure:
    if dates is None:
        return _base_layout(go.Figure(), "Trades (R) over Time")
    d = pd.DataFrame(
        {
            "date": pd.to_datetime(dates, errors="coerce"),
            "R": pd.to_numeric(r, errors="coerce"),
        }
    )
    if risk is not None:
        d["risk"] = pd.to_numeric(risk, errors="coerce").abs()
    d["outcome"] = np.where(d["R"] >= 0, "Win", "Loss")
    d = d.dropna(subset=["date", "R"])
    fig = px.scatter(
        d,
        x="date",
        y="R",
        color="outcome",
        size=("risk" if "risk" in d.columns else None),
        color_discrete_map={"Win": BLUE, "Loss": RED},
    )
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color=AXIS_WEAK)
    fig.update_traces(marker=dict(opacity=0.9, line=dict(width=0)))
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0)
    )
    return _base_layout(fig, "Trades (R) over Time")


def _fig_profit_by_symbol(df: pd.DataFrame, sym_col: str) -> go.Figure:
    d = df.copy()
    d[sym_col] = d[sym_col].astype(str)
    agg = d.groupby(sym_col, as_index=False)["pnl"].sum().sort_values("pnl", ascending=False)
    if len(agg) > 5:
        top5 = agg.head(5)
        others_sum = pd.DataFrame({sym_col: ["Others"], "pnl": [agg["pnl"].iloc[5:].sum()]})
        agg = pd.concat([top5, others_sum], ignore_index=True)
    agg = agg.sort_values("pnl", ascending=True)

    fig = px.bar(agg, x="pnl", y=sym_col, orientation="h", labels={"pnl": "Net PnL ($)"})
    fig.add_vline(x=0, line_width=1, line_dash="dot", line_color=AXIS_WEAK)
    fig.update_traces(marker_color=BLUE, marker_line_color="rgba(255,255,255,0.12)", opacity=0.9)
    return _base_layout(fig, "Profit by Symbol (Top 5 + Others)")


def _fig_pnl_histogram(pnl_per_trade: pd.Series, nbins: int = 40) -> go.Figure:
    """
    PnL per Trade — simple histogram that's immediately readable.
    Shows mean/median markers and a subtle 1σ band.
    """
    s = pd.to_numeric(pnl_per_trade, errors="coerce").dropna()
    title = "PnL per Trade"
    fig = go.Figure()

    if len(s) == 0:
        return _base_layout(fig, title)

    # Summary stats
    mean_v = float(np.mean(s))
    med_v = float(np.median(s))
    std_v = float(np.std(s)) if len(s) > 1 else 0.0

    # 1σ band (drawn under the bars)
    if std_v > 0:
        fig.add_shape(
            type="rect",
            x0=mean_v - std_v,
            x1=mean_v + std_v,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            fillcolor="rgba(79,209,197,0.10)",  # TEAL at low alpha
            line=dict(width=0),
            layer="below",
        )

    # Histogram bars
    fig.add_trace(
        go.Histogram(
            x=s,
            nbinsx=nbins,
            name="Trades",
            marker=dict(color=BLUE_LIGHT, line=dict(width=0)),
            opacity=0.9,
        )
    )

    # Reference lines: zero, median, mean
    fig.add_vline(x=0, line_width=1, line_dash="dot", line_color=AXIS_WEAK)
    fig.add_vline(x=med_v, line_width=1, line_dash="solid", line_color="rgba(255,255,255,0.28)")
    fig.add_vline(x=mean_v, line_width=1, line_dash="solid", line_color="rgba(255,255,255,0.28)")

    # Labels for mean/median (placed near the top)
    fig.add_annotation(
        x=med_v,
        y=1.02,
        xref="x",
        yref="paper",
        text="Median",
        showarrow=False,
        font=dict(size=10, color=FG_MUTED),
        yanchor="bottom",
    )
    fig.add_annotation(
        x=mean_v,
        y=1.02,
        xref="x",
        yref="paper",
        text="Mean",
        showarrow=False,
        font=dict(size=10, color=FG_MUTED),
        yanchor="bottom",
    )

    fig.update_layout(
        bargap=0.15,
        showlegend=False,
        xaxis_title="PnL per trade ($)",
        yaxis_title="Count",
    )
    fig.update_xaxes(tickprefix="$", separatethousands=True)

    return _base_layout(fig, title)


# ================ MAIN (6 charts, rounded containers; KPI dividers + padding) ================
def render(
    df_view: pd.DataFrame,
    start_equity: float,
    date_col: Optional[str],
    tf: str,
    win_rate_v: float,  # 0..1
    avg_win_v: float,
    avg_loss_v: float,
) -> None:
    """
    PERFORMANCE – 6-chart Executive View
      Row1: Underwater (by Date) | Cumulative R (by Date) | Rolling Metrics (20D)
      Row2: Trades (R) over Time | Profit by Symbol (Top5+Others) | R:R Ranges (Win/Loss stacked)
    """

    # Page top padding
    if PAGE_TOP_PADDING_PX > 0:
        st.markdown(f"<div style='height:{PAGE_TOP_PADDING_PX}px'></div>", unsafe_allow_html=True)

    # Make sure rounded corners CSS is present on every render
    inject_plot_rounding_css(radius_px=12, add_shadow=False)

    st.markdown(
        f"""
    <style>
    /* Bordered card look for all Performance charts */
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .perf-underwater),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .perf-cumr),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .perf-rolling),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .perf-scatter),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .perf-sym),
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .perf-hist) {{
    background: {CARD_BG} !important;
    border-radius: 12px !important;
    padding: 12px !important;
    border: 1px solid rgba(255,255,255,0.06);
    overflow: hidden;
    }}

    /* keep Plotly canvas corners rounded (you already use this app-wide, but safe here too) */
    [data-testid="stPlotlyChart"] > div:first-child {{
    border-radius: 12px; overflow: hidden;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Core series
    pnl = pd.to_numeric(df_view.get("pnl", 0.0), errors="coerce").fillna(0.0)

    # Dates & day-level aggregates
    dates = None
    if date_col and date_col in df_view.columns:
        dates = pd.to_datetime(df_view[date_col], errors="coerce")

    daily = _daily_pnl(dates, pnl) if dates is not None else pd.DataFrame(columns=["date", "pnl"])
    daily_stats = (
        _daily_win_loss(dates, pnl)
        if dates is not None
        else pd.DataFrame(columns=["date", "trades", "wins", "exp"])
    )

    # Risk & R
    risk_series = _risk_series(df_view)
    r_series = _r_series(df_view, pnl, risk_series)

    # Equity / drawdown (trade-level for KPIs)
    equity = start_equity + pnl.cumsum()
    peak = equity.cummax()
    dd_abs = equity - peak
    dd_pct = np.where(peak > 0, (equity / peak) - 1.0, 0.0)
    max_dd_abs = float(dd_abs.min()) if len(dd_abs) else 0.0
    max_dd_pct = float(dd_pct.min()) * 100.0 if len(dd_pct) else 0.0

    net_profit = float(pnl.sum())
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(pnl[pnl < 0].sum())
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else float("inf")
    expectancy = float(win_rate_v) * float(avg_win_v) + (1.0 - float(win_rate_v)) * float(
        avg_loss_v
    )
    recovery = (net_profit / abs(max_dd_abs)) if max_dd_abs != 0 else float("inf")

    # Streaks & ratios
    longest_loser = _longest_losing_streak(pnl)
    wins, losses = int((pnl > 0).sum()), int((pnl < 0).sum())
    wl_ratio = (wins / max(1, losses)) if losses else float("inf")

    # Hold times (if available) for Activity
    entry_col = _exists_any(df_view, ["entry_time", "Entry Time"])
    exit_col = _exists_any(df_view, ["exit_time", "Exit Time"])
    avg_hold_min = total_hold_min = None
    if entry_col and exit_col:
        _mins = (
            (
                pd.to_datetime(df_view[exit_col], errors="coerce")
                - pd.to_datetime(df_view[entry_col], errors="coerce")
            )
            .dt.total_seconds()
            .div(60.0)
        )
        if _mins.notna().any():
            avg_hold_min = float(_mins.mean(skipna=True))
            total_hold_min = float(_mins.sum(skipna=True))

    # ---- padding above KPI row
    if KPI_TOP_PADDING_PX > 0:
        st.markdown(f"<div style='height:{KPI_TOP_PADDING_PX}px'></div>", unsafe_allow_html=True)

    # ---- KPIs (no containers). Vertical rules via slim columns of fixed height.
    k1, vr1, k2, vr2, k3 = st.columns([1, 0.02, 1, 0.02, 1], gap="small")

    with k1:
        st.markdown("**Profitability**")
        _line(
            "Net Profit", f"<span style='color:{_colorize(net_profit)}'>{_money(net_profit)}</span>"
        )
        _line(
            "Profit Factor",
            f"<span style='color:{_colorize(profit_factor,'ratio')}'>{'∞' if np.isinf(profit_factor) else f'{profit_factor:.2f}'}</span>",
        )
        _line(
            "Expectancy / Trade",
            f"<span style='color:{_colorize(expectancy)}'>{_money(expectancy)}</span>",
        )
        _line(
            "Gross Profit",
            f"<span style='color:{_colorize(gross_profit)}'>{_money(gross_profit)}</span>",
        )
        _line(
            "Gross Loss", f"<span style='color:{_colorize(gross_loss)}'>{_money(gross_loss)}</span>"
        )

    with vr1:
        st.markdown(
            f"<div style='height:{KPI_VRULE_HEIGHT_PX}px;border-left:1px solid rgba(255,255,255,0.10)'></div>",
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown("**Risk & Consistency**")
        _line(
            "Max DD ($)", f"<span style='color:{_colorize(-1,'risk')}'>{_money(max_dd_abs)}</span>"
        )
        _line("Max DD (%)", f"<span style='color:{_colorize(-1,'risk')}'>{max_dd_pct:.2f}%</span>")
        _line(
            "Win/Loss Ratio",
            f"<span style='color:{_colorize(wl_ratio,'ratio')}'>{'∞' if np.isinf(wl_ratio) else f'{wl_ratio:.2f}'}</span>",
        )
        _line(
            "Recovery Factor",
            f"<span style='color:{_colorize(recovery,'ratio')}'>{'∞' if np.isinf(recovery) else f'{recovery:.2f}'}</span>",
        )
        _line(
            "Longest Losing Streak",
            f"<span style='color:{_colorize(-1,'risk')}'>{_int(longest_loser)} trades</span>",
        )

    with vr2:
        st.markdown(
            f"<div style='height:{KPI_VRULE_HEIGHT_PX}px;border-left:1px solid rgba(255,255,255,0.10)'></div>",
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown("**Activity**")
        _line("Trades", _int(len(df_view)))
        if dates is not None and dates.notna().any():
            trading_days = int(pd.to_datetime(dates).dt.date.nunique())
            _line("Trading Days", _int(trading_days))
            _line("Trades / Day", f"{(len(df_view)/max(1,trading_days)):.2f}")
        if avg_hold_min is not None:
            _line("Avg Hold Time", _fmt_duration_minutes(avg_hold_min))
        if total_hold_min is not None:
            _line("Total Hold Time", _fmt_duration_minutes(total_hold_min))

    # ---- roomy divider between KPIs and charts
    if DIVIDER_MARGIN_PX > 0:
        st.markdown(f"<div style='height:{DIVIDER_MARGIN_PX}px'></div>", unsafe_allow_html=True)
    st.divider()
    if DIVIDER_MARGIN_PX > 0:
        st.markdown(f"<div style='height:{DIVIDER_MARGIN_PX}px'></div>", unsafe_allow_html=True)

    # ---- Charts (2×3), each inside a rounded bordered container
    r1c1, r1c2, r1c3 = st.columns(3, gap="small")
    with r1c1:
        with st.container(border=False):
            st.markdown('<div class="perf-underwater"></div>', unsafe_allow_html=True)
            st.plotly_chart(
                _fig_underwater_daily(start_equity, daily),
                use_container_width=True,
                key="perf_underwater_date",
            )

    with r1c2:
        with st.container(border=False):
            st.markdown(
                '<div class="perf-cumr"></div>', unsafe_allow_html=True
            )  # keep same card chrome
            from src.charts.tier_wr import figure_tier_wr  # top-level import is fine too

            fig = figure_tier_wr(df_view, date_col=(date_col or "date"), height=CHART_HEIGHT_PX)
            st.plotly_chart(fig, use_container_width=True, key="perf_tier_wr")

    with r1c3:
        with st.container(border=False):
            st.markdown('<div class="perf-rolling"></div>', unsafe_allow_html=True)
            st.plotly_chart(
                _fig_rolling_20d(daily_stats), use_container_width=True, key="perf_roll20d"
            )

    r2c1, r2c2, r2c3 = st.columns(3, gap="small")
    with r2c1:
        with st.container(border=False):
            if (dates is not None) and (r_series is not None):
                st.markdown('<div class="perf-scatter"></div>', unsafe_allow_html=True)
                st.plotly_chart(
                    _fig_trade_scatter_r(dates, r_series, risk_series),
                    use_container_width=True,
                    key="perf_trade_scatter",
                )
                # ...and in the else branch, right before the fallback chart too

            else:
                st.plotly_chart(
                    _base_layout(go.Figure(), "Trades (R) over Time"), use_container_width=True
                )
                st.caption("Requires 'R Ratio' or ('PnL' + 'Dollars Risked') to compute R.")
    with r2c2:
        with st.container(border=False):
            sym_col = _exists_any(
                df_view, ["Symbol", "symbol", "Asset", "asset", "Ticker", "ticker", "Pair", "pair"]
            )
            if sym_col:
                st.markdown('<div class="perf-sym"></div>', unsafe_allow_html=True)
                st.plotly_chart(
                    _fig_profit_by_symbol(df_view, sym_col),
                    use_container_width=True,
                    key="perf_sym",
                )
                # ...and in the else branch before the fallback chart too

            else:
                st.plotly_chart(
                    _base_layout(go.Figure(), "Profit by Symbol (Top 5 + Others)"),
                    use_container_width=True,
                )
                st.caption("No symbol/ticker column found.")
    with r2c3:
        with st.container(border=False):
            st.markdown('<div class="perf-hist"></div>', unsafe_allow_html=True)
            st.plotly_chart(
                _fig_pnl_histogram(pnl, nbins=40), use_container_width=True, key="perf_pnl_hist"
            )
