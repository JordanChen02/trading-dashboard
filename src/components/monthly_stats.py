# src/components/monthly_stats.py
from __future__ import annotations

import calendar
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

POS = "#61D0A8"  # green
NEG = "#E06B6B"  # red
MUTED = "rgba(229,231,235,0.7)"  # neutral text


def _month_name(i: int) -> str:
    return calendar.month_abbr[i]


def _ensure_rr(df: pd.DataFrame) -> pd.Series:
    """Return R multiples; if no 'rr' column, derive from pnl / median(|loss|)."""
    if "rr" in df.columns:
        return pd.to_numeric(df["rr"], errors="coerce").fillna(0.0)
    pnl = pd.to_numeric(df.get("pnl", 0.0), errors="coerce").fillna(0.0)
    losses = pnl[pnl < 0].abs()
    risk_proxy = float(losses.median()) if len(losses) else 1.0
    return pnl / (risk_proxy or 1.0)


def _compute_monthly(df: pd.DataFrame, date_col: Optional[str]) -> pd.DataFrame:
    """
    Return monthly stats: year, month, rr_sum, pnl_sum, wins, trades, win_rate.
    """
    if date_col and date_col in df.columns:
        dts = pd.to_datetime(df[date_col], errors="coerce")
    elif "_date" in df.columns:
        dts = pd.to_datetime(df["_date"], errors="coerce")
    else:
        df = df.copy()
        df["_date"] = pd.Timestamp.now()
        dts = pd.to_datetime(df["_date"], errors="coerce")

    base = df.copy()
    base["_dt"] = dts
    base = base.loc[base["_dt"].notna()].copy()
    if base.empty:
        today = pd.Timestamp.now()
        return pd.DataFrame(
            {
                "year": [today.year],
                "month": [today.month],
                "rr_sum": [0.0],
                "pnl_sum": [0.0],
                "wins": [0],
                "trades": [0],
                "win_rate": [0.0],
            }
        )

    base["year"] = base["_dt"].dt.year
    base["month"] = base["_dt"].dt.month

    pnl = pd.to_numeric(base.get("pnl", 0.0), errors="coerce").fillna(0.0)
    rr = _ensure_rr(base)
    win_mask = pnl > 0

    g = base.groupby(["year", "month"], as_index=False)
    agg = g.agg(
        rr_sum=("month", lambda s, rr_vals=rr: float(rr.loc[s.index].sum())),
        pnl_sum=("month", lambda s, pnl_vals=pnl: float(pnl.loc[s.index].sum())),
        wins=("month", lambda s, wm=win_mask: int(wm.loc[s.index].sum())),
        trades=("month", lambda s: int(len(s))),
    )
    agg["win_rate"] = np.where(agg["trades"] > 0, (agg["wins"] / agg["trades"]) * 100.0, 0.0)

    return agg[["year", "month", "rr_sum", "pnl_sum", "wins", "trades", "win_rate"]].sort_values(
        ["year", "month"]
    )


def _fmt_rr(x: float) -> str:
    s = f"{abs(x):.2f}"
    if x > 0:
        return f"+{s} R:R"
    if x < 0:
        return f"-{s} R:R"
    return "0.00 R:R"


def _fmt_pnl(x: float) -> str:
    sign = "-" if x < 0 else ""
    return f"{sign}${abs(x):,.2f}"


def _fmt_wr(x: float) -> str:
    return f"{x:.0f}%"


def _val_class(x: float) -> str:
    """Color class: positive -> green, negative -> red, zero -> muted."""
    if x > 0:
        return "ms-pos"
    if x < 0:
        return "ms-neg"
    return "ms-zero"


def render_monthly_stats(
    df: pd.DataFrame,
    *,
    date_col: Optional[str],
    years_back: int = 2,
    title: str = "Monthly Stats",
    key: str = "monthly_stats",
    cell_height: int = 64,  # control cell height
    total_col_width_px: int = 110,  # width of the "Total" column
) -> None:
    """
    Render a compact HTML grid:
    rows = last `years_back` years (most recent first),
    columns = Jan..Dec + Total.
    - Months with NO data render as a blank cell.
    - Months with data but exact 0 display 0 in neutral color.
    """
    stats = _compute_monthly(df, date_col)
    if stats.empty:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.info("No monthly data yet.")
        return

    most_recent_year = int(stats["year"].max())
    years = list(range(most_recent_year, most_recent_year - max(1, years_back), -1))

    # (year, month) -> (rr_sum, pnl_sum, win_rate)
    lut: Dict[Tuple[int, int], Tuple[float, float, float]] = {}
    for _, row in stats.iterrows():
        lut[(int(row["year"]), int(row["month"]))] = (
            float(row["rr_sum"]),
            float(row["pnl_sum"]),
            float(row["win_rate"]),
        )

    # yearly totals for Total column
    ytot = stats.groupby("year", as_index=False).agg(
        rr_sum=("rr_sum", "sum"),
        pnl_sum=("pnl_sum", "sum"),
        wins=("wins", "sum"),
        trades=("trades", "sum"),
    )
    ytot["win_rate"] = np.where(ytot["trades"] > 0, (ytot["wins"] / ytot["trades"]) * 100.0, 0.0)
    ytot_lut: Dict[int, Tuple[float, float, float]] = {
        int(r["year"]): (float(r["rr_sum"]), float(r["pnl_sum"]), float(r["win_rate"]))
        for _, r in ytot.iterrows()
    }

    with st.container(border=True):
        st.markdown(f"**{title}**", unsafe_allow_html=True)

        st.markdown(
            f"""
<style>
.ms-grid-{key} {{
  display: grid;
  grid-template-columns: 80px repeat(12, 1fr) {total_col_width_px}px;
  gap: 6px;
  font-family: 'Inter', system-ui, sans-serif;
}}
.ms-head, .ms-cell, .ms-year {{
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px;
  padding: 8px 10px;
}}
.ms-head {{
  font-weight: 700;
  color: {MUTED};
  min-height: {cell_height // 2}px;
  display:flex;align-items:center;justify-content:center;
}}
.ms-year {{
  display:flex;align-items:center;justify-content:center;
  color: {MUTED};
  min-height: {cell_height}px;
}}
.ms-cell {{
  min-height: {cell_height}px;
  display:flex;flex-direction:column;gap:4px;
}}
.ms-cell-line {{ display:block; line-height:1.15; }}
.ms-pos  {{ color:{POS};  font-weight:500; }}
.ms-neg  {{ color:{NEG};  font-weight:500; }}
.ms-zero {{ color:{MUTED}; font-weight:500; }}   /* neutral for zeros */
.ms-empty {{ background: rgba(255,255,255,0.02); }} /* truly empty months */
</style>
""",
            unsafe_allow_html=True,
        )

        # Header row (+ Total)
        header_html = (
            ["<div class='ms-head'>Year</div>"]
            + [f"<div class='ms-head'>{_month_name(m)}</div>" for m in range(1, 13)]
            + ["<div class='ms-head'>Total</div>"]
        )

        # Body rows
        body_html: List[str] = []
        for y in years:
            body_html.append(f"<div class='ms-year'>{y}</div>")
            for m in range(1, 13):
                if (y, m) not in lut:
                    # No data for this month -> blank cell
                    body_html.append("<div class='ms-cell ms-empty'></div>")
                    continue

                rr, pnl, wr = lut[(y, m)]
                rr_cls = _val_class(rr)
                pnl_cls = _val_class(pnl)

                body_html.append(
                    f"<div class='ms-cell'>"
                    f"<span class='ms-cell-line {rr_cls}'>{_fmt_rr(rr)}</span>"
                    f"<span class='ms-cell-line {pnl_cls}'>{_fmt_pnl(pnl)}</span>"
                    f"<span class='ms-cell-line ms-zero'>{_fmt_wr(wr)}</span>"
                    f"</div>"
                )

            # totals
            if y in ytot_lut:
                trr, tpnl, twr = ytot_lut[y]
                trr_cls = _val_class(trr)
                tpnl_cls = _val_class(tpnl)
                body_html.append(
                    f"<div class='ms-cell'>"
                    f"<span class='ms-cell-line {trr_cls}'>{_fmt_rr(trr)}</span>"
                    f"<span class='ms-cell-line {tpnl_cls}'>{_fmt_pnl(tpnl)}</span>"
                    f"<span class='ms-cell-line ms-zero'>{_fmt_wr(twr)}</span>"
                    f"</div>"
                )
            else:
                body_html.append("<div class='ms-cell ms-empty'></div>")

        st.markdown(
            f"<div class='ms-grid-{key}'>" + "".join(header_html + body_html) + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
