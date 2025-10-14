# src/views/checklist.py
from __future__ import annotations

from typing import Dict, List, Tuple

import plotly.graph_objects as go
import streamlit as st
from streamlit.components.v1 import iframe  # <- added for embedding non-image URLs


# --- modal fallback (works whether st.modal exists or not) ---
def modal_or_inline(title: str, render_body):
    """
    Open a real modal/dialog if available; otherwise render a simple overlay.
    `render_body` is a function that draws the modal content.
    """
    dlg = getattr(st, "modal", None) or getattr(st, "dialog", None)
    if callable(dlg):
        decorator = dlg(title)

        @decorator
        def _show():
            render_body()

        _show()
    else:
        # Fallback overlay
        st.markdown(
            f"""
            <div style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;display:flex;align-items:center;justify-content:center;">
              <div style="background:#111827;border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:16px;min-width:480px;max-width:90vw;">
                <div style="font-weight:700;margin-bottom:8px;">{title}</div>
            """,
            unsafe_allow_html=True,
        )
        render_body()
        st.markdown("</div></div>", unsafe_allow_html=True)


# ---- Theme (fallbacks if module not present) ----
try:
    from src.theme import BLUE, CARD_BG
except Exception:
    BLUE = "#3AA4EB"
    CARD_BG = "#0d121f"

RED = "#E06B6B"
FG = "#E5E7EB"
FG_MUTED = "#9AA4B2"

# Distinct card bg so inputs don’t blend with cards
LOCAL_CARD_BG = "#0F1829"


# ==============================
# Session init & data defaults
# ==============================
# Default option→points mappings (adjustable here)
BIAS_POINTS = {str(i): float(i) for i in range(1, 11)}

SWEEP_DOL_POINTS = {
    "Equal High/Low": 10.0,
    "Internal High/Low": 9.0,
    "External High/Low": 9.7,
    "Data High/Low": 10.0,
    "ITH/ITL": 9.5,
    "LRLR >3": 10.0,
    "LRLR <3": 9.2,
}

MOMENTUM_POINTS = {"Low": 8.0, "Medium": 8.8, "High": 9.5, "Very High": 10.0}
IFVG_POINTS = {"Small": 8.8, "Medium": 9.6, "Large": 10.0}
POI_POINTS = {"Daily FVG": 10.0, "H4 FVG": 10.0, "H1 FVG": 9.8, "M15 FVG": 9.5}

DEFAULT_CHECKLIST: List[Dict] = [
    {
        "name": "Bias Confidence",
        "type": "select",
        "options": list(BIAS_POINTS.keys()),
        "options_points": BIAS_POINTS,
        "value": "10",
    },
    {
        "name": "Liquidity Sweep",
        "type": "select",
        "options": list(SWEEP_DOL_POINTS.keys()),
        "options_points": SWEEP_DOL_POINTS,
        "value": "External High/Low",
    },
    {
        "name": "Draw on Liquidity",
        "type": "select",
        "options": list(SWEEP_DOL_POINTS.keys()),
        "options_points": SWEEP_DOL_POINTS,
        "value": "LRLR >3",
    },
    {
        "name": "Momentum",
        "type": "select",
        "options": list(MOMENTUM_POINTS.keys()),
        "options_points": MOMENTUM_POINTS,
        "value": "High",
    },
    {
        "name": "iFVG",
        "type": "select",
        "options": list(IFVG_POINTS.keys()),
        "options_points": IFVG_POINTS,
        "value": "Large",
    },
    {
        "name": "Point of Interest",
        "type": "select",
        "options": list(POI_POINTS.keys()),
        "options_points": POI_POINTS,
        "value": "H4 FVG",
    },
]

# Confluences default OFF
DEFAULT_CONFS: List[Dict] = [
    {"name": "12 EMA (1H)", "on": False, "pts": 1},
    {"name": "12 EMA (4H)", "on": False, "pts": 2},
    {"name": "12 EMA (15m)", "on": False, "pts": 1},
    {"name": "12 EMA (Daily)", "on": False, "pts": 2},
    {"name": "Fundamentals", "on": False, "pts": 3},
    {"name": "CVD", "on": False, "pts": 1},
    {"name": "TSO, TDO", "on": False, "pts": 2},
    {"name": "Key levels", "on": False, "pts": 2},
    {"name": "Stairstep", "on": False, "pts": 2},
]

TEMPLATE_NAMES = ["A+ iFVG Setup", "Custom Template 1"]


def _ensure_state():
    st.session_state.setdefault("cl_templates", TEMPLATE_NAMES[:])
    st.session_state.setdefault("cl_template_sel", TEMPLATE_NAMES[0])
    st.session_state.setdefault("cl_items", [dict(x) for x in DEFAULT_CHECKLIST])
    st.session_state.setdefault("cl_confs", [dict(x) for x in DEFAULT_CONFS])
    st.session_state.setdefault("cl_chart_1", {"url": "", "file": None})
    st.session_state.setdefault("cl_chart_2", {"url": "", "file": None})
    st.session_state.setdefault("ex1_menu_open", False)
    st.session_state.setdefault("ex2_menu_open", False)

    # Add-item modal state
    st.session_state.setdefault("add_item_open", False)
    st.session_state.setdefault("add_item_title", "")
    st.session_state.setdefault("add_item_rows", [{"opt": "", "pts": 0.0}])

    # Flags to control lifecycle & clean reset
    st.session_state.setdefault(
        "add_item_force_show_once", False
    )  # show only when explicitly opened
    st.session_state.setdefault("add_item_should_reset", False)  # defer reset to next run
    st.session_state.setdefault(
        "add_item_keep_open", False
    )  # keep modal open across reruns after +Add / delete


# ==============================
# Scoring / grade helpers
# ==============================
def _score(items: List[Dict], confs: List[Dict]) -> Tuple[int, str]:
    """
    Checklist always tops out at 100% regardless of count:
      For N items, each item contributes 100/N at max.
      Contribution = (selected / max_for_item) * (100/N)

    Confluences: flat bonus = sum(pts). Cap final at 100.
    """
    n = max(1, len(items))
    per_item_weight = 100.0 / n

    base_pct = 0.0
    for it in items:
        opts_pts: Dict[str, float] = it.get("options_points", {}) or {}
        if not opts_pts:
            continue
        max_pts = max(opts_pts.values())
        sel_pts = float(opts_pts.get(str(it.get("value", "")), 0.0))
        part = 0.0 if max_pts <= 0 else (sel_pts / max_pts) * per_item_weight
        base_pct += part

    conf_bonus = sum(float(c.get("pts", 0)) for c in confs if c.get("on"))
    pct = int(round(min(100.0, base_pct + conf_bonus)))

    if pct >= 96:
        grade = "S"
    elif pct >= 90:
        grade = "A+"
    elif pct >= 85:
        grade = "A"
    elif pct >= 80:
        grade = "A-"
    elif pct >= 75:
        grade = "B+"
    elif pct >= 70:
        grade = "B"
    elif pct >= 65:
        grade = "B-"
    else:
        grade = "C"
    return pct, grade


# ==============================
# UI helpers
# ==============================
def _inject_css():
    st.markdown(
        f"""
<style>
/* Blue outline buttons */
[data-testid="stButton"] > button,
[data-testid="stFormSubmitButton"] > button {{
  border: 1px solid {BLUE} !important;
  color: {BLUE} !important;
  background: transparent !important;
  box-shadow: none !important;
}}
/* Red danger buttons */
[data-testid="stButton"] .stTooltipHoverTarget > button {{
  border: 1px solid {RED} !important;
  color: {RED} !important;
  background: transparent !important;
  box-shadow: none !important;
}}
/* Inputs visible on dark cards */
[data-testid="stSelectbox"] .st-emotion-cache-1wivap2,
[data-testid="stSelectbox"] div[data-baseweb="select"],
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {{
  background-color: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 10px !important;
}}
/* Borderless kebab */
.kebab .stButton > button {{
  border: none !important;
  background: transparent !important;
  color: {FG_MUTED} !important;
  padding: 2px 6px !important;
  box-shadow: none !important;
}}
/* Card shells — match your reference */
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .chk-card),
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .conf-card),
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .score-card),
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .chart-card) {{
  background: {LOCAL_CARD_BG} !important;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px !important;
  padding: 12px !important;
  overflow: hidden;
}}
/* Scroll */
.conf-scroll {{ max-height: 420px; overflow: auto; padding-right: 4px; }}

/* Titles */
.card-title, .section-title {{ font-weight:700; font-size:16px; color:{FG}; }}
/* Checklist criteria labels */
.item-name {{ color:{FG}; font-weight:700; font-size:14px; }}

/* Wider header buttons */
.wide-btn .stButton > button {{ padding:8px 16px !important; min-width:120px; }}

/* Grade bigger */
.grade-pill {{ font-weight:900; font-size:40px; color:{FG}; }}
</style>
""",
        unsafe_allow_html=True,
    )


def _half_donut_fig(title: str, pct: int) -> go.Figure:
    """Half-gauge like overview Win Rate — same size & layout; % INSIDE the arc."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=max(0, min(int(pct), 100)),
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 100], "visible": False},
                "bar": {"color": "rgba(0,0,0,0)"},
                "borderwidth": 0,
                "steps": [
                    {"range": [0, pct], "color": "#2E86C1"},
                    {"range": [pct, 100.0], "color": "#212C47"},
                ],
            },
            domain={"x": [0, 1], "y": [0, 0.86]},
        )
    )
    fig.update_layout(
        margin=dict(l=8, r=8, t=34, b=8),
        height=160,
        paper_bgcolor=LOCAL_CARD_BG,
        plot_bgcolor=LOCAL_CARD_BG,
    )
    # Title above donut
    fig.add_annotation(
        x=0.5,
        y=1.24,
        xref="paper",
        yref="paper",
        text=f"<b>{title}</b>",
        showarrow=False,
        font=dict(size=14, color=FG),
        align="center",
    )
    # % inside donut
    fig.add_annotation(
        x=0.5,
        y=0.10,
        xref="paper",
        yref="paper",
        text=f"{pct:.0f}%",
        showarrow=False,
        font=dict(size=30, color=FG),
        align="center",
    )
    return fig


# ==============================
# Add Item Modal
# ==============================
def _add_item_modal():
    def _body():
        st.text_input("Title", key="add_item_title", placeholder="e.g., Session Context")

        st.write("Options & Points")
        rows = st.session_state.add_item_rows
        remove = None
        for idx, row in enumerate(rows):
            c1, c2, c3 = st.columns([0.65, 0.25, 0.10])
            with c1:
                row["opt"] = st.text_input(
                    "",
                    value=row.get("opt", ""),
                    key=f"add_row_opt_{idx}",
                    label_visibility="collapsed",
                    placeholder="Option text",
                )
            with c2:
                row["pts"] = st.number_input(
                    "",
                    value=float(row.get("pts", 0.0)),
                    key=f"add_row_pts_{idx}",
                    label_visibility="collapsed",
                    step=0.1,
                )
            with c3:
                if st.button("🗑", key=f"add_row_del_{idx}", help="danger"):
                    remove = idx
        if remove is not None:
            rows.pop(remove)
            st.session_state.add_item_keep_open = True  # keep modal open on rerun
            st.rerun()  # reflect removal instantly

        if st.button("+ Add option", key="add_row_add"):
            rows.append({"opt": "", "pts": 0.0})
            st.session_state.add_item_keep_open = True  # keep modal open on rerun
            st.rerun()  # reflect new row instantly

        st.markdown("---")
        cols = st.columns([0.7, 0.3])
        with cols[1]:
            if st.button("Save item", key="add_item_save"):
                title = (
                    st.session_state.add_item_title.strip()
                    or f"Custom ({len(st.session_state.cl_items)+1})"
                )
                opts = [r["opt"].strip() for r in rows if r["opt"].strip()]
                pts = [float(r["pts"]) for r in rows if r["opt"].strip()]
                if opts and len(pts) == len(opts):
                    options_points = {o: float(p) for o, p in zip(opts, pts)}
                    st.session_state.cl_items.append(
                        {
                            "name": title,
                            "type": "select",
                            "options": opts,
                            "options_points": options_points,
                            "value": opts[0],
                        }
                    )
                    # close dialog now; defer resetting widget keys to next run
                    st.session_state.add_item_open = False
                    st.session_state.add_item_should_reset = True
                    st.rerun()

    modal_or_inline("Add Checklist Item", _body)


# ==============================
# Main render
# ==============================
def render(*_args, **_kwargs):
    _ensure_state()
    _inject_css()

    # Ensure the dialog does NOT auto-open when navigating back
    if st.session_state.get("add_item_open") and not st.session_state.get(
        "add_item_force_show_once", False
    ):
        st.session_state["add_item_open"] = False

    # Handle deferred reset after save (avoid mutating widget keys during dialog render)
    if st.session_state.get("add_item_should_reset"):
        st.session_state["add_item_title"] = ""
        st.session_state["add_item_rows"] = [{"opt": "", "pts": 0.0}]
        st.session_state["add_item_should_reset"] = False

    # If we just added/deleted an option, keep the modal open on the next run
    if st.session_state.get("add_item_keep_open"):
        st.session_state["add_item_open"] = True
        st.session_state["add_item_force_show_once"] = True
        st.session_state["add_item_keep_open"] = False

    # Top bar: dropdown + New button next to it (same row)
    topL, _ = st.columns([0.3, 0.7], gap="small")
    with topL:
        dd_col, new_col = st.columns([0.82, 0.18])
        with dd_col:
            st.selectbox(
                "Setup Checklist",
                st.session_state.cl_templates,
                index=0,
                key="cl_template_sel",
                label_visibility="collapsed",
            )
        with new_col:
            st.button("New", key="cl_new_template")

    # Main split 0.6 / 0.4
    left, right = st.columns([0.55, 0.5], gap="large")

    # ---------------- LEFT: each section in its OWN card (unchanged structure) ----------------
    with left:
        # Row 1: Checklist & Confluences (separate cards)
        cL, cR = st.columns([1, 1], gap="small")

        # Checklist card
        with cL:
            st.markdown('<div class="chk-card"></div>', unsafe_allow_html=True)
            with st.container(border=False):
                st.markdown('<div class="card-title">Checklist</div>', unsafe_allow_html=True)

                a1, a2, _ = st.columns([1.5, 1.9, 4])
                with a1:
                    st.markdown('<div class="wide-btn">', unsafe_allow_html=True)
                    if st.button("+ Add item", key="cl_add_item"):
                        st.session_state.add_item_open = True
                        st.session_state.add_item_force_show_once = (
                            True  # ensure it shows once only when clicked
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
                with a2:
                    st.markdown('<div class="wide-btn">', unsafe_allow_html=True)
                    if st.button("🗑 Delete last", key="cl_del_item", help="danger"):
                        if st.session_state.cl_items:
                            st.session_state.cl_items.pop()
                    st.markdown("</div>", unsafe_allow_html=True)

                # Modal for adding item
                if st.session_state.add_item_open:
                    _add_item_modal()
                # After rendering once, drop the force flag
                if st.session_state.get("add_item_force_show_once"):
                    st.session_state["add_item_force_show_once"] = False

                # Render each checklist row
                for i, it in enumerate(st.session_state.cl_items):
                    ncol, selcol = st.columns([1.2, 3.0], gap="small")
                    with ncol:
                        st.markdown(
                            f"<div class='item-name'>{it['name']}</div>", unsafe_allow_html=True
                        )
                    with selcol:
                        idx = (
                            it["options"].index(it["value"])
                            if it.get("value") in it["options"]
                            else 0
                        )
                        it["value"] = st.selectbox(
                            f"{it['name']}_sel",
                            it["options"],
                            index=idx,
                            key=f"cl_sel_{i}",
                            label_visibility="collapsed",
                        )

        # Confluences card
        with cR:
            st.markdown('<div class="conf-card"></div>', unsafe_allow_html=True)
            with st.container(border=False):
                hL, hR = st.columns([1, 0.1])
                with hL:
                    st.markdown('<div class="card-title">Confluences</div>', unsafe_allow_html=True)
                    st.caption("Optional boosts. Each adds a small bonus; total bonus is capped.")
                with hR:
                    st.markdown('<div class="kebab">', unsafe_allow_html=True)
                    st.button("⋯", key="cl_conf_kebab")
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown('<div class="conf-scroll">', unsafe_allow_html=True)
                remove_idx = None
                for i, c in enumerate(st.session_state.cl_confs):
                    r1, r2, r3, r4 = st.columns([0.12, 1.5, 0.35, 0.23], gap="small")
                    with r1:
                        c["on"] = bool(
                            st.checkbox("", value=bool(c.get("on", False)), key=f"conf_on_{i}")
                        )
                    with r2:
                        c["name"] = st.text_input(
                            "", value=c["name"], key=f"conf_name_{i}", label_visibility="collapsed"
                        )
                    with r3:
                        c["pts"] = int(
                            st.number_input(
                                "pts",
                                value=int(c.get("pts", 1)),
                                min_value=0,
                                max_value=5,
                                step=1,
                                key=f"conf_pts_{i}",
                                label_visibility="collapsed",
                            )
                        )
                    with r4:
                        if st.button("🗑", key=f"conf_del_{i}", help="danger"):
                            remove_idx = i
                if remove_idx is not None:
                    st.session_state.cl_confs.pop(remove_idx)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

                aL, _ = st.columns([1, 1])
                with aL:
                    if st.button("Add", key="cl_conf_add"):
                        st.session_state.cl_confs.append(
                            {"name": "New Confluence", "on": False, "pts": 1}
                        )
                        st.rerun()

        # -------- Score & Grade shifted left: [0.6, 0.4] [score, empty] --------
        sc_left, sc_right = st.columns([0.6, 0.4], gap="large")
        with sc_left:
            # NEW: narrow the card by putting it in an inner column
            narrow, _ = st.columns([0.8, 0.2])  # ← tweak 0.8 smaller/bigger to taste
            with narrow:
                st.markdown('<div class="score-card"></div>', unsafe_allow_html=True)
                with st.container(border=False):
                    pct, grade = _score(st.session_state.cl_items, st.session_state.cl_confs)
                    gL, gR = st.columns([2.2, 1], gap="small")
                    with gL:
                        fig = _half_donut_fig("Overall Score", pct)
                        st.plotly_chart(
                            fig, use_container_width=True, config={"displayModeBar": False}
                        )
                    with gR:
                        st.markdown(
                            "<div class='ui-subtle' style='text-align:center'>Grade</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"<div class='grade-pill' style='text-align:center'>{grade}</div>",
                            unsafe_allow_html=True,
                        )

        # Save for Journal under the score card (still left side)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)  # tiny spacer
        btn_col, _ = st.columns([0.35, 0.65])  # keep it tucked under the card
        with btn_col:
            if st.button("Save for Journal", key="cl_save_for_journal"):
                items = {it["name"]: it["value"] for it in st.session_state.cl_items}
                lines = [
                    f"[{items.get('Bias Confidence','')}] Bias",
                    f"{items.get('Liquidity Sweep','')} Sweep",
                    f"{items.get('Draw on Liquidity','')} DOL",
                    f"{items.get('Momentum','')} Momentum",
                    f"{items.get('iFVG','')} iFVG",
                    f"{items.get('Point of Interest','')} POI",
                ]
                for c in st.session_state.cl_confs:
                    if c.get("on"):
                        lines.append(c["name"])

                pct, grade = _score(st.session_state.cl_items, st.session_state.cl_confs)
                st.session_state["pending_checklist"] = {
                    "overall_pct": pct,
                    "overall_grade": grade,
                    "journal_checklist": lines,
                    "journal_confirms": lines,
                }
                st.toast("Saved to Journal loader ✅")
    # ---------------- RIGHT: Chart Examples (unchanged except rendering) ----------------
    with right:
        st.markdown('<div class="section-title">Chart Examples</div>', unsafe_allow_html=True)

        # Example 1
        st.markdown('<div class="chart-card"></div>', unsafe_allow_html=True)
        with st.container(border=False):
            h1, k1 = st.columns([1, 0.06])
            with h1:
                st.markdown("<div class='card-title'>Example 1</div>", unsafe_allow_html=True)
            with k1:
                st.markdown('<div class="kebab">', unsafe_allow_html=True)
                if st.button("⋯", key="ex1_kebab"):
                    st.session_state.ex1_menu_open = not st.session_state.ex1_menu_open
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.ex1_menu_open:
                u1, f1 = st.columns([1.2, 1], gap="small")
                with u1:
                    st.session_state.cl_chart_1["url"] = st.text_input(
                        "Paste image URL",
                        value=st.session_state.cl_chart_1.get("url", ""),
                        key="ex1_url",
                        placeholder="https://www.tradingview.com/x/RMJesEwo/",
                    )
                with f1:
                    st.session_state.cl_chart_1["file"] = st.file_uploader(
                        "or Upload", key="ex1_file", type=["png", "jpg", "jpeg"]
                    )

            # NEW: render image if direct image; otherwise embed page (e.g., TradingView)
            if st.session_state.cl_chart_1.get("file") is not None:
                st.image(st.session_state.cl_chart_1["file"], use_container_width=True)
            else:
                url1 = st.session_state.cl_chart_1.get("url", "").strip()
                if url1:
                    is_img = url1.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
                    if is_img:
                        st.image(url1, use_container_width=True)
                    else:
                        iframe(url1, height=600)
                else:
                    st.caption("No image yet.")

        # Example 2
        st.markdown('<div class="chart-card"></div>', unsafe_allow_html=True)
        with st.container(border=False):
            h2, k2 = st.columns([1, 0.06])
            with h2:
                st.markdown("<div class='card-title'>Example 2</div>", unsafe_allow_html=True)
            with k2:
                st.markdown('<div class="kebab">', unsafe_allow_html=True)
                if st.button("⋯", key="ex2_kebab"):
                    st.session_state.ex2_menu_open = not st.session_state.ex2_menu_open
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.ex2_menu_open:
                u2, f2 = st.columns([1.2, 1], gap="small")
                with u2:
                    st.session_state.cl_chart_2["url"] = st.text_input(
                        "Paste image URL ",
                        value=st.session_state.cl_chart_2.get("url", ""),
                        key="ex2_url",
                        placeholder="https://www.tradingview.com/x/fvMNs5k2/",
                    )
                with f2:
                    st.session_state.cl_chart_2["file"] = st.file_uploader(
                        "or Upload ", key="ex2_file", type=["png", "jpg", "jpeg"]
                    )

            # NEW: render image if direct image; otherwise embed page (e.g., TradingView)
            if st.session_state.cl_chart_2.get("file") is not None:
                st.image(st.session_state.cl_chart_2["file"], use_container_width=True)
            else:
                url2 = st.session_state.cl_chart_2.get("url", "").strip()
                if url2:
                    is_img = url2.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
                    if is_img:
                        st.image(url2, use_container_width=True)
                    else:
                        iframe(url2, height=600)
                else:
                    st.caption("No image yet.")
