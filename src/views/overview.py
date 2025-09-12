# src/views/overview.py
from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from src.charts.equity import plot_equity
import src.views.calendar_panel as cal_view


def render_overview(
    df_view: pd.DataFrame,
    start_equity: float,
    date_col: Optional[str],
    month_start: pd.Timestamp,
    win_rate_v: float,
    avg_win_loss_ratio_v: float,
    avg_win_v: float,
    avg_loss_v: float,
    pnl_v: pd.Series,
    wins_mask_v: pd.Series,
    losses_mask_v: pd.Series,
) -> None:
    """Renders the full Overview tab (left/right split, KPIs, equity curve tabs, daily/weekly PnL, win streak, calendar, filter button)."""

    # ======= LAYOUT FRAME: 40/60 main split (left=40%, right=60%) =======
    s_left, s_right = st.columns([2, 3], gap="small")  # 2:3 ≈ 40%:60%

    with s_left:
        # === Prep values used in these KPIs (Range-aware) ===
        gross_profit_v = float(pnl_v[wins_mask_v].sum())
        gross_loss_v   = float(pnl_v[losses_mask_v].sum())
        pf_v = (gross_profit_v / abs(gross_loss_v)) if gross_loss_v != 0 else float("inf")

        _side_dist_local = (
            df_view["side"].str.lower().value_counts(normalize=True)
                .reindex(["long", "short"]).fillna(0.0)
            if "side" in df_view.columns else pd.Series(dtype=float)
        )

        st.markdown("""
        <style>
        /* Pull everything inside the KPI card up by N pixels */
        .kpi-pack{
          margin-top:12px;
          margin-bottom:12px;   /* ← adds space at the bottom INSIDE the card */
        }
        .kpi-card-vh{ padding-bottom:18px; }
        .kpi-number{ margin:1; line-height:1; }
        .kpi-label{  margin:1.05; line-height:1.05; }
        .pillbar{    margin-top:8px; }   /* keep a small gap above the bar */
        /* vertical centering wrapper for KPI cards */
        .kpi-card-vh{
          min-height:130px;              /* adjust height to taste */
          display:flex;
          flex-direction:column;
          justify-content:center;        /* vertical center */
          align-items:center;            /* keep contents centered horizontally */
          gap:8px;                       /* tight vertical spacing */
        }

        /* center the headline/label group */
        .kpi-center{ text-align:center; margin:0; }

        /* tighten text spacing so vertical centering is true */
        .kpi-number{ font-size:32px; font-weight:800; line-height:1.5; margin:0; }
        .kpi-label{  font-size:14px; color:#cbd5e1; line-height:1.2; margin:0; }

        /* progress pill */
        .pillbar{
          width:100%;
          height:18px;
          background:#1b2433;
          border-radius:999px;
          overflow:hidden;
          margin:1px 0 17px 0;  /* top | right | bottom | left */
        }
        .pillbar .win{  height:100%; background:#2E86C1; display:inline-block; }
        .pillbar .loss{ height:100%; background:#2f3a52; display:inline-block; }
        </style>
        """, unsafe_allow_html=True)

        # === KPI GRID (2x2) ===
        kpi_row1 = st.columns([1, 1], gap="small")
        with kpi_row1[0]:
            with st.container(border=True):
                st.markdown('<div style="text-align:center; font-weight:600; margin:0 0 6px; transform: translateX(6px);">Win Rate</div>',
                            unsafe_allow_html=True)

                wr_pct = float(win_rate_v * 100.0)         # win_rate_v is 0..1
                win_color   = "#2E86C1"
                loss_color  = "#212C47"
                panel_bg    = "#0b0f19"

                fig_win = go.Figure(go.Indicator(
                    mode="gauge",
                    value=wr_pct,
                    gauge={
                        "shape": "angular",
                        "axis": {"range": [0, 100], "visible": False},
                        "bar": {"color": "rgba(0,0,0,0)"},
                        "borderwidth": 0,
                        "steps": [
                            {"range": [0, wr_pct],     "color": win_color},
                            {"range": [wr_pct, 100.0], "color": loss_color},
                        ],
                    },
                    domain={"x": [0, 1], "y": [0, 1]},
                ))
                fig_win.update_layout(
                    margin=dict(l=8, r=8, t=6, b=0),
                    height=90,
                    paper_bgcolor=panel_bg,
                )
                fig_win.add_annotation(
                    x=0.5, y=0.10,
                    xref="paper", yref="paper",
                    text=f"{wr_pct:.0f}%",
                    showarrow=False,
                    font=dict(size=30, color="#e5e7eb", family="Inter, system-ui, sans-serif"),
                    align="center"
                )
                st.plotly_chart(fig_win, use_container_width=True)

        with kpi_row1[1]:
            with st.container(border=True):
                st.markdown('<div class="kpi-pack">', unsafe_allow_html=True)

                _aw_al_num = "∞" if avg_win_loss_ratio_v == float("inf") else f"{avg_win_loss_ratio_v:.2f}"
                st.markdown(
                    f"""
                    <div class="kpi-center">
                      <div class="kpi-number">{_aw_al_num}</div>
                      <div class="kpi-label">Avg Win / Avg Loss</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # --- Blue/Red ratio pill (Avg Win vs Avg Loss) ---
                _aw = float(max(avg_win_v, 0.0))
                _al = float(abs(avg_loss_v))
                _total = _aw + _al
                _blue_pct = 50.0 if _total <= 0 else (_aw / _total) * 100.0
                _red_pct  = 100.0 - _blue_pct

                st.markdown(
                    f"""
                    <div class="pillbar" style="margin-top:6px;">
                      <div class="win"  style="width:{_blue_pct:.2f}%"></div>
                      <div class="loss" style="width:{_red_pct:.2f}%"></div>
                    </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # --- KPI row 2 (Profit Factor left, Long vs Short right) ---
        kpi_row2 = st.columns([1, 1], gap="small")

        # LEFT: Profit Factor — half donut
        with kpi_row2[0]:
            with st.container(border=True):
                st.markdown(
                    '<div style="text-align:center; font-weight:600; margin:0 0 6px; transform: translateX(6px);">'
                    'Profit Factor</div>',
                    unsafe_allow_html=True
                )

                pf_display = "∞" if pf_v == float("inf") else f"{pf_v:.2f}"
                max_pf = 4.0
                pf_clamped = max(0.0, min(float(pf_v if pf_v != float("inf") else max_pf), max_pf))
                pct = (pf_clamped / max_pf) * 100.0

                panel_bg  = "#0b0f19"
                fill_col  = "#2E86C1"
                rest_col  = "#212C47"

                fig_pf = go.Figure(go.Indicator(
                    mode="gauge",
                    value=pct,
                    gauge={
                        "shape": "angular",
                        "axis": {"range": [0, 100], "visible": False},
                        "bar": {"color": "rgba(0,0,0,0)"},
                        "borderwidth": 0,
                        "steps": [
                            {"range": [0, pct],     "color": fill_col},
                            {"range": [pct, 100.0], "color": rest_col},
                        ],
                    },
                    domain={"x": [0, 1], "y": [0, 1]},
                ))
                fig_pf.update_layout(
                    margin=dict(l=8, r=8, t=6, b=0),
                    height=90,
                    paper_bgcolor=panel_bg,
                    showlegend=False,
                )
                fig_pf.add_annotation(
                    x=0.5, y=0.10, xref="paper", yref="paper",
                    text=pf_display, showarrow=False,
                    font=dict(size=28, color="#e5e7eb", family="Inter, system-ui, sans-serif"),
                    align="center"
                )
                st.plotly_chart(fig_pf, use_container_width=True)

        # RIGHT: Long vs Short — pillbar
        with kpi_row2[1]:
            with st.container(border=True):
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div style="text-align:center; font-weight:600; margin:0 0 16px; transform: translateX(6px);">'
                    'Long vs Short</div>',
                    unsafe_allow_html=True
                )

                if "side" in df_view.columns:
                    _side_lower = df_view["side"].astype(str).str.lower()
                    long_ct  = int((_side_lower == "long").sum())
                    short_ct = int((_side_lower == "short").sum())
                    total_ct = long_ct + short_ct

                    long_pct = (long_ct / total_ct * 100.0) if total_ct > 0 else 50.0
                    short_pct = 100.0 - long_pct

                    st.markdown(
                        f'''
                        <div class="pillbar" style="margin:20px 0 42px;">
                          <div class="win"  style="width:{long_pct:.2f}%"></div>
                          <div class="loss" style="width:{short_pct:.2f}%"></div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
                else:
                    st.caption("No side column found.")

        # === Equity Curve (bottom of s_left) — with tabs and date x-axis ===
        with st.container(border=True):
            st.markdown("""
            <style>
            div[data-testid="stTabs"] div[role="tablist"]{
              justify-content: flex-end;
              gap: 4px;
              margin-top: -4px;
            }
            div[data-testid="stTabs"] button[role="tab"]{
              padding: 4px 10px;
            }
            </style>
            """, unsafe_allow_html=True)

            _has_date = (date_col is not None and date_col in df_view.columns and len(df_view) > 0)
            df_ec = df_view.copy()
            pnl_num = pd.to_numeric(df_ec["pnl"], errors="coerce").fillna(0.0)
            df_ec["cum_pnl"] = pnl_num.cumsum()
            df_ec["equity"]  = float(start_equity) + df_ec["cum_pnl"]

            if _has_date:
                _dt = pd.to_datetime(df_ec[date_col], errors="coerce")
                df_ec = df_ec.assign(_date=_dt).sort_values("_date")
            else:
                df_ec = df_ec.reset_index(drop=True).assign(_date=pd.RangeIndex(start=0, stop=len(df_ec)))

            def _slice_window(df_in: pd.DataFrame, label: str) -> pd.DataFrame:
                if not _has_date or len(df_in) == 0 or label == "All":
                    return df_in
                last_ts = pd.to_datetime(df_in["_date"].iloc[-1])
                if label == "1D":
                    start = last_ts - pd.Timedelta(days=1)
                elif label == "1W":
                    start = last_ts - pd.Timedelta(weeks=1)
                elif label == "1M":
                    start = last_ts - pd.DateOffset(months=1)
                elif label == "6M":
                    start = last_ts - pd.DateOffset(months=6)
                elif label == "1Y":
                    start = last_ts - pd.DateOffset(years=1)
                else:
                    start = df_in["_date"].min()
                return df_in[df_in["_date"] >= start]

            st.markdown('<div class="eq-tabs">', unsafe_allow_html=True)

            hdr_l, hdr_r = st.columns([1, 3], gap="small")
            with hdr_l:
                st.markdown(
                    '<div style="color:#d5deed; font-weight:600; letter-spacing:.2px; font-size:32px; margin:0;">Equity Curve</div>',
                    unsafe_allow_html=True
                )
            with hdr_r:
                st.empty()

            eq_tabs = st.tabs(["All", "1D", "1W", "1M", "6M", "1Y"])

            for _label, _tab in zip(["All","1D","1W","1M","6M","1Y"], eq_tabs):
                with _tab:
                    _dfw = _slice_window(df_ec, _label)
                    if len(_dfw) == 0:
                        st.caption("No data in this window.")
                    else:
                        fig_eq = plot_equity(
                            _dfw,
                            start_equity=start_equity,
                            has_date=_has_date,
                            height=590,
                        )
                        # Use a unique key prefix so it won't collide with other tabs
                        st.plotly_chart(fig_eq, use_container_width=True, key=f"ov_eq_curve_{_label}")

    # === Right column top row (split in 2) ===
    with s_right:
        st.markdown("<div style='margin-bottom:-12px'></div>", unsafe_allow_html=True)
        right_top = st.columns([2, 1], gap="small")

        # ----- Left side: Daily / Weekly PnL -----
        with right_top[0]:
            with st.container(border=True):
                # Header spacing knobs
                TITLE_TOP_PAD = 10
                CTRL_TOP_PAD  = 4

                r1l, r1r = st.columns([3, 1], gap="small")
                with r1l:
                    st.markdown(f"<div style='height:{TITLE_TOP_PAD}px'></div>", unsafe_allow_html=True)
                    current_mode = st.session_state.get("_dpnl_mode", "Daily")
                    st.markdown("<div style='font-size:28px; font-weight:600; margin:0'>"
                                f"{current_mode} PnL</div>", unsafe_allow_html=True)
                with r1r:
                    st.markdown(f"<div style='height:{CTRL_TOP_PAD}px'></div>", unsafe_allow_html=True)
                    mode = st.segmented_control(options=["Daily","Weekly"], default=current_mode, label="")
                    st.session_state["_dpnl_mode"] = mode

                if date_col and date_col in df_view.columns:
                    _dt = pd.to_datetime(df_view[date_col], errors="coerce")
                else:
                    _fallbacks = ["_date", "date", "datetime", "timestamp", "time", "entry_time", "exit_time"]
                    _cand = next((c for c in _fallbacks if c in df_view.columns), None)
                    _dt = pd.to_datetime(df_view[_cand], errors="coerce") if _cand else pd.to_datetime(pd.Series([], dtype="float64"))

                _pnl = pd.to_numeric(df_view.get("pnl", df_view.get("net_pnl")), errors="coerce").fillna(0.0)
                _tmp = pd.DataFrame({"_date": _dt, "pnl": _pnl}).dropna(subset=["_date"])
                if _tmp.empty:
                    st.info("No dated PnL rows available.")
                else:
                    _tmp["_day"] = _tmp["_date"].dt.floor("D")
                    _last_day = pd.to_datetime(_tmp["_day"].max())

                    panel_bg = "#0b0f19"
                    pos_color = "#2E86C1"
                    neg_color = "#2E86C1"
                    bar_line  = "rgba(255,255,255,0.12)"

                    if mode == "Daily":
                        idx = pd.date_range(end=_last_day, periods=14, freq="D")
                        daily = (_tmp.groupby("_day", as_index=False)["pnl"].sum()
                                .set_index("_day").reindex(idx, fill_value=0.0)
                                .rename_axis("_day").reset_index())
                        x_vals = daily["_day"]; y_vals = daily["pnl"]
                        tickvals = x_vals[::2]
                        ticktext = [d.strftime("%m/%d/%Y") for d in tickvals]
                    else:
                        wk = _tmp.set_index("_day")["pnl"].resample("W-SUN").sum()
                        widx = pd.date_range(end=wk.index.max(), periods=8, freq="W-SUN")
                        weekly = wk.reindex(widx, fill_value=0.0).reset_index()
                        weekly.columns = ["_week", "pnl"]
                        x_vals = weekly["_week"]; y_vals = weekly["pnl"]
                        tickvals = x_vals; ticktext = [d.strftime("%m/%d/%Y") for d in x_vals]

                    st.markdown("<div style='margin-bottom:-12px'></div>", unsafe_allow_html=True)

                    fig = go.Figure()
                    fig.add_bar(
                        x=x_vals, y=y_vals,
                        marker=dict(color=[pos_color if v >= 0 else neg_color for v in y_vals],
                                    line=dict(color=bar_line, width=1)),
                        hovertemplate="%{x|%b %d, %Y}<br>PNL: $%{y:,.2f}<extra></extra>",
                    )
                    fig.add_hline(y=0, line_width=1, line_color="rgba(255,255,255,0.25)")

                    # annotate biggest profit/loss bars
                    annotations = []
                    if len(y_vals) > 0:
                        max_idx = int(y_vals.idxmax())
                        min_idx = int(y_vals.idxmin())
                        y_max = float(y_vals[max_idx])
                        y_min = float(y_vals[min_idx])
                        span = max(1.0, float(abs(y_vals.max()) + abs(y_vals.min())))
                        pad  = span * 0.04
                        annotations.append(dict(
                            x=x_vals[max_idx], y=(y_max + pad if y_max >= 0 else y_max - pad),
                            xref="x", yref="y", text=f"${y_max:,.2f}", showarrow=False,
                            font=dict(size=12, color="#ffffff")
                        ))
                        annotations.append(dict(
                            x=x_vals[min_idx], y=(y_min - pad if y_min < 0 else y_min + pad),
                            xref="x", yref="y", text=f"${y_min:,.2f}", showarrow=False,
                            font=dict(size=12, color="#ffffff")
                        ))
                    fig.update_layout(annotations=annotations)

                    fig.update_layout(
                        height=250,
                        margin=dict(l=16, r=16, t=8, b=10),
                        paper_bgcolor=panel_bg, plot_bgcolor=panel_bg,
                        showlegend=False,
                        bargap=0.5,
                        bargroupgap=0.1
                    )
                    fig.update_yaxes(
                        zeroline=False, showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                        tickprefix="$", separatethousands=True,
                    )
                    fig.update_xaxes(
                        showgrid=False, tickangle=-35,
                        tickmode="array", tickvals=tickvals, ticktext=ticktext,
                    )
                    st.plotly_chart(fig, use_container_width=True)

        # Right side: Win Streak box
        with right_top[1]:
            with st.container(border=True):
                days_streak        = 9
                trades_streak      = 19
                best_days_streak   = 21
                resets_days_count  = 1
                best_trades_streak = 19
                resets_trades_ct   = 7

                st.markdown("""
                <style>
                .ws-wrap { --brand:#2E86C1; --pillGood:#1e3a8a; --pillBad:#6b1d1d; }
                .ws-title{ font-weight:800; font-size:20px; letter-spacing:.2px; margin:0 0 8px 0; }
                .ws-row{ display:flex; gap:28px; justify-content:space-between; }
                .ws-col{ flex:1; display:flex; flex-direction:column; align-items:center; }
                .ws-main{ display:flex; align-items:center; gap:10px; }
                .ws-big{ font-size:38px; font-weight:800; color:var(--brand); line-height:1; }
                .ws-icon{
                    width:28px; height:28px; background-color:var(--brand); opacity:.95;
                    -webkit-mask: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path fill='black' d='M13.5 0c.9 4.4-1.8 6.8-3.6 8.6C8.1 10.4 7 12 7 14.5 7 18.1 9.9 21 13.5 21S20 18.1 20 14.5c0-3.2-1.7-5.4-3.2-6.9-.9-.9-1.7-1.6-2.1-2.7C14.1 3.5 14 1.8 13.5 0zM12 14c.5 1.8-.8 2.8-1.6 3.6-.6.6-1 1.2-1 2.2 0 1.9 1.5 3.2 3.4 3.2s3.4-1.3 3.4-3.2c0-1.5-.8-2.5-1.5-3.2-.5-.5-1-.9-1.2-1.6-.2-.6-.2-1.3-.5-2z'/></svg>") no-repeat center / contain;
                            mask: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path fill='black' d='M13.5 0c.9 4.4-1.8 6.8-3.6 8.6C8.1 10.4 7 12 7 14.5 7 18.1 9.9 21 13.5 21S20 18.1 20 14.5c0-3.2-1.7-5.4-3.2-6.9-.9-.9-1.7-1.6-2.1-2.7C14.1 3.5 14 1.8 13.5 0zM12 14c.5 1.8-.8 2.8-1.6 3.6-.6.6-1 1.2-1 2.2 0 1.9 1.5 3.2 3.4 3.2s3.4-1.3 3.4-3.2c0-1.5-.8-2.5-1.5-3.2-.5-.5-1-.9-1.2-1.6-.2-.6-.2-1.3-.5-2z'/>") no-repeat center / contain;
                }
                .ws-badges{ display:flex; flex-direction:column; gap:6px; margin-left:6px; }
                .ws-pill{ min-width:36px; padding:2px 8px; border-radius:10px; text-align:center; font-size:12px; font-weight:700; color:#cbd5e1; }
                .ws-pill.ws-good{ background:rgba(46,134,193,.25); border:1px solid rgba(46,134,193,.4); }
                .ws-pill.ws-bad{ background:rgba(202,82,82,.25);  border:1px solid rgba(202,82,82,.4); }
                .ws-foot{ margin-top:6px; font-size:13px; color:#cbd5e1; }
                </style>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="ws-wrap">
                  <div class="ws-title">Winstreak</div>
                  <div class="ws-row">
                    <div class="ws-col">
                      <div class="ws-main">
                        <span class="ws-big">{days_streak}</span>
                        <span class="ws-icon"></span>
                        <span class="ws-badges">
                          <span class="ws-pill ws-good">{best_days_streak}</span>
                          <span class="ws-pill ws-bad">{resets_days_count}</span>
                        </span>
                      </div>
                      <div class="ws-foot">Days</div>
                    </div>
                    <div class="ws-col">
                      <div class="ws-main">
                        <span class="ws-big">{trades_streak}</span>
                        <span class="ws-icon"></span>
                        <span class="ws-badges">
                          <span class="ws-pill ws-good">{best_trades_streak}</span>
                          <span class="ws-pill ws-bad">{resets_trades_ct}</span>
                        </span>
                      </div>
                      <div class="ws-foot">Trades</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<div style='margin-bottom:-32px'></div>", unsafe_allow_html=True)

        # --- Right column bottom: Calendar panel ---
        with st.container(border=True):
            cal_view.render_calendar_panel(df_view, date_col, month_start)

    # ======= END LAYOUT FRAME =======

    # ===================== CHARTS (card layout) =====================
    _, btn_col = st.columns([8, 1], gap="small")
    with btn_col:
        clicked = False
        try:
            clicked = st.button("Filters", key="filters_btn", icon=":material/filter_list:", use_container_width=True)
        except TypeError:
            clicked = st.button("🔎 Filters", key="filters_btn", use_container_width=True)

        if clicked:
            st.toast("Filters are in the left sidebar.")
            st.session_state["_filters_prompted"] = True
