# src/components/last_trades.py
from __future__ import annotations

import datetime as dt
from typing import Dict, Iterable, List

import streamlit as st

# Light theme-friendly colors; tweak if you have theme constants you prefer
POS = "#61D0A8"  # greenish for gains
NEG = "#E06B6B"  # red for losses
ACCENT = "#AFC7F2"  # soft blue for labels


def placeholder_last_trades() -> List[Dict]:
    """Five mocked trades (Sept 2025), until journal wiring is done."""
    return [
        {
            "symbol": "NQ",
            "side": "LONG",
            "entry_type": "m1 iFVG",
            "date_from": dt.datetime(2025, 9, 10),
            "date_to": dt.datetime(2025, 9, 10),
            "rr": 1.8,
            "pct": 0.62,
            "pnl": 185.40,
        },
        {
            "symbol": "SUIUSDT",
            "side": "LONG",
            "entry_type": "4H EMA 12",
            "date_from": dt.datetime(2025, 9, 9),
            "date_to": dt.datetime(2025, 9, 9),
            "rr": 0.9,
            "pct": 0.35,
            "pnl": 72.15,
        },
        {
            "symbol": "SOLUSDT",
            "side": "SHORT",
            "entry_type": "m15 iFVG",
            "date_from": dt.datetime(2025, 9, 6),
            "date_to": dt.datetime(2025, 9, 6),
            "rr": -1.1,
            "pct": -0.43,
            "pnl": -126.70,
        },
        {
            "symbol": "ASTERUSDT",
            "side": "LONG",
            "entry_type": "Sweep",
            "date_from": dt.datetime(2025, 9, 4),
            "date_to": dt.datetime(2025, 9, 4),
            "rr": 2.6,
            "pct": 0.88,
            "pnl": 241.92,
        },
        {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "entry_type": "m1 OB",
            "date_from": dt.datetime(2025, 9, 3),
            "date_to": dt.datetime(2025, 9, 3),
            "rr": 0.3,
            "pct": 0.12,
            "pnl": 38.55,
        },
    ]


def _side_badge(side: str) -> str:
    side = (side or "").upper()
    if side.startswith("L"):
        bg = "rgba(97,208,168,.18)"  # light green
        fg = POS
        label = "LONG"
    else:
        bg = "rgba(224,107,107,.18)"  # light red
        fg = NEG
        label = "SHORT"
    return f"<span style='padding:2px 8px;border-radius:10px;background:{bg};color:{fg};font-size:.75rem;font-weight:600'>{label}</span>"


def _fmt_range(a: dt.datetime, b: dt.datetime) -> str:
    if a.date() == b.date():
        return a.strftime("%A, %d %b %Y")
    return f"{a.strftime('%A, %d %b %Y')} – {b.strftime('%A, %d %b %Y')}"


def _fmt_rr(x: float) -> str:
    sign = "" if x >= 0 else "−"
    return f"{sign}{abs(x):.2f} R:R"


def _fmt_pct(x: float) -> str:
    sign = "" if x >= 0 else "−"
    return f"{sign}{abs(x):.2f}%"


def _fmt_pnl(x: float) -> str:
    sign = "" if x >= 0 else "−"
    return f"{sign}${abs(x):,.2f}"


def render_last_trades(
    trades: Iterable[Dict], *, title: str = "Last 5 Trades", key_prefix: str = "last5"
) -> None:
    """Render a compact list like your screenshot."""
    trades = list(trades)[:5]

    with st.container(border=False):
        st.markdown(
            f"<div style='font-weight:600;margin:0 0 8px 4px;'>{title}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<hr style='opacity:.12;margin:6px 0 10px'>", unsafe_allow_html=True)

        if not trades:
            st.info("No trades yet. Your last five closed trades will appear here.")
            return

        for i, t in enumerate(trades):
            sym = t.get("symbol", "")
            side = t.get("side", "")
            etype = t.get("entry_type", "")
            a = t.get("date_from")
            b = t.get("date_to", a)
            rr = float(t.get("rr", 0.0))
            pct = float(t.get("pct", 0.0))
            pnl = float(t.get("pnl", 0.0))

            rr_color = POS if rr >= 0 else NEG
            pct_color = POS if pct >= 0 else NEG
            pnl_color = POS if pnl >= 0 else NEG

            # Row layout
            left, r_rr, r_pct, r_pnl = st.columns([5, 1.3, 1.2, 1.6], gap="small")

            with left:
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px'>"
                    f"<span style='font-weight:700;letter-spacing:.2px'>{sym}</span>"
                    f"{_side_badge(side)}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.caption(f"{etype}")
                st.caption(f"{_fmt_range(a, b)}")
                st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

            with r_rr:
                st.markdown(
                    f"<div style='text-align:right;color:{rr_color};font-weight:700'>{_fmt_rr(rr)}</div>",
                    unsafe_allow_html=True,
                )
            with r_pct:
                st.markdown(
                    f"<div style='text-align:right;color:{pct_color};opacity:.9'>{_fmt_pct(pct)}</div>",
                    unsafe_allow_html=True,
                )
            with r_pnl:
                st.markdown(
                    f"<div style='text-align:right;color:{pnl_color};font-weight:700'>{_fmt_pnl(pnl)}</div>",
                    unsafe_allow_html=True,
                )

            if i < len(trades) - 1:
                st.markdown("<hr style='opacity:.12;margin:12px 0'>", unsafe_allow_html=True)
