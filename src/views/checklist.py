# src/views/checklist.py
from __future__ import annotations

from typing import Dict, List, Tuple

import plotly.graph_objects as go  # for KPI-style half donut
import streamlit as st

# ---- Theme (fallbacks if module not present) ----
try:
    from src.theme import BLUE, CARD_BG
except Exception:
    BLUE = "#3AA4EB"
    CARD_BG = "#0d121f"

RED = "#E06B6B"
FG = "#E5E7EB"
FG_MUTED = "#9AA4B2"

# NEW: distinct card background so inputs don’t blend with cards
LOCAL_CARD_BG = "#0f1422"


# ==============================
# Session init & data defaults
# ==============================
DEFAULT_CHECKLIST: List[Dict] = [
    {
        "name": "Bias Confidence",
        "type": "select",
        "options": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        "value": "10",  # ← default (requested)
        "weight": 18,
    },
    {
        "name": "Liquidity Sweep",
        "type": "select",
        "options": [
            "None",
            "Equal High/Low",
            "Internal High/Low",
            "External High/Low",
            "Data High/Low",
        ],
        "value": "External High/Low",  # ← default (requested)
        "weight": 16,
    },
    {
        "name": "Draw on Liquidity",
        "type": "select",
        "options": ["None", "LRLR ≤3", "LRLR >3", "Equal Highs/Lows Cluster"],
        "value": "LRLR >3",  # ← default (requested)
        "weight": 12,
    },
    {
        "name": "Momentum",
        "type": "select",
        "options": ["Low", "Medium", "High", "Very High"],
        "value": "High",  # ← default (requested)
        "weight": 14,
    },
    {
        "name": "iFVG",
        "type": "select",
        "options": ["Small", "Medium", "Large"],
        "value": "Large",  # ← default (requested)
        "weight": 16,
    },
    {
        "name": "Point of Interest",
        "type": "select",
        "options": ["H1 OB", "H4 OB", "H1 FVG", "H4 FVG", "Daily FVG", "Weekly Level"],
        "value": "H4 FVG",  # ← default (requested)
        "weight": 14,
    },
]

# Confluences (scrollable, editable)
DEFAULT_CONFS: List[Dict] = [
    # Replaced
    {"name": "12 EMA (1H)", "on": True, "pts": 1},
    {"name": "12 EMA (4H)", "on": True, "pts": 2},
    {"name": "12 EMA (15m)", "on": True, "pts": 1},
    {"name": "12 EMA (Daily)", "on": True, "pts": 2},
    {"name": "Fundamentals", "on": False, "pts": 3},
    {"name": "CVD", "on": True, "pts": 1},
    # Removed: OI, SMT, Macro
    # Added:
    {"name": "TSO, TDO", "on": False, "pts": 2},
    {"name": "Key levels", "on": True, "pts": 2},
    {"name": "Stairstep", "on": True, "pts": 2},
]

TEMPLATE_NAMES = ["A+ iFVG Setup", "Custom Template 1"]


def _ensure_state():
    st.session_state.setdefault("cl_templates", TEMPLATE_NAMES[:])
    st.session_state.setdefault("cl_template_sel", TEMPLATE_NAMES[0])
    st.session_state.setdefault("cl_items", [dict(x) for x in DEFAULT_CHECKLIST])
    st.session_state.setdefault("cl_confs", [dict(x) for x in DEFAULT_CONFS])
    st.session_state.setdefault("cl_chart_1", {"url": "", "file": None})
    st.session_state.setdefault("cl_chart_2", {"url": "", "file": None})


# ==============================
# Scoring / grade helpers
# ==============================
def _score(items: List[Dict], confs: List[Dict]) -> Tuple[int, str]:
    # Base checklist: sum of item weights (non-empty selection)
    base = sum(int(i.get("weight", 0)) for i in items if str(i.get("value", "")).strip())
    # Confluence: sum of pts where on=True, cap confluence at 20
    conf_pts = sum(int(c.get("pts", 0)) for c in confs if c.get("on"))
    conf_pts = min(conf_pts, 20)

    raw = base + conf_pts
    total_cap = 100
    pct = max(0, min(int(round((raw / total_cap) * 100)), 100))

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
/* ---- Blue outline buttons (match Journal) ---- */
[data-testid="stButton"] > button,
[data-testid="stFormSubmitButton"] > button {{
  border: 1px solid {BLUE} !important;
  color: {BLUE} !important;
  background: transparent !important;
  box-shadow: none !important;
}}
/* Red 'danger' buttons (trash) — use tooltip wrapper path like Journal */
[data-testid="stButton"] .stTooltipHoverTarget > button {{
  border: 1px solid {RED} !important;
  color: {RED} !important;
  background: transparent !important;
  box-shadow: none !important;
}}
/* Borderless tiny buttons (kebab, "⋯") */
.kebab .stButton > button {{
  border: none !important;
  background: transparent !important;
  color: {FG_MUTED} !important;
  padding: 2px 6px !important;
  box-shadow: none !important;
}}
/* ----- Cards: use LOCAL_CARD_BG (different from CARD_BG) ----- */
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
/* Scrollable confluences list */
.conf-scroll {{
  max-height: 420px;
  overflow: auto;
  padding-right: 4px;
}}
/* Small muted headers */
.ui-subtle {{
  color: {FG_MUTED};
  font-size: 12px;
  margin: 0 0 8px 0;
  font-weight: 600;
}}
/* Row styling */
.row {{
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  column-gap: 8px;
}}
.item-row {{
  display: grid;
  grid-template-columns: 160px 1fr auto;
  column-gap: 10px;
  align-items: center;
  margin: 6px 0;
}}
/* Slightly larger titles for Checklist/Confluences; Chart Examples matches */
.card-title, .section-title {{ font-weight:700; font-size:16px; color:{FG}; }}
/* Checklist criteria labels slightly larger */
.item-name {{ color: {FG}; font-weight: 700; font-size: 14px; }}

/* Slightly wider checklist header buttons */
.wide-btn .stButton > button {{ padding: 8px 14px !important; }}
</style>
""",
        unsafe_allow_html=True,
    )


def _half_donut_fig(title: str, pct: int) -> go.Figure:
    """Half-gauge like overview KPIs, % INSIDE the arc, caption above. Made slightly bigger."""
    pct = max(0, min(int(pct), 100))
    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=pct,
            gauge={
                "shape": "angular",
                "axis": {"range": [0, 100], "visible": False},
                "bar": {"color": "rgba(0,0,0,0)"},
                "borderwidth": 0,
                "steps": [
                    {"range": [0, pct], "color": BLUE},
                    {"range": [pct, 100.0], "color": "rgba(255,255,255,0.10)"},
                ],
            },
            domain={"x": [0, 1], "y": [0, 0.86]},
        )
    )
    fig.update_layout(
        margin=dict(l=8, r=8, t=38, b=8),
        height=160,  # bigger to match overview Win Rate size
        paper_bgcolor=LOCAL_CARD_BG,
        plot_bgcolor=LOCAL_CARD_BG,
    )
    # Title above (Overall Score)
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
    # % inside
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
# Main render
# ==============================
def render(*_args, **_kwargs):
    _ensure_state()
    _inject_css()

    # ====== Top Bar: dropdown left (0.3) + the SAME "New" button on the right ======
    topL, _ = st.columns([0.3, 0.7], gap="small")  # keep the outer layout
    with topL:
        dd_col, new_col = st.columns([0.82, 0.18])  # dropdown + button side-by-side
        with dd_col:
            st.selectbox(
                "Setup Checklist",
                st.session_state.cl_templates,
                index=0,
                label_visibility="collapsed",
            )
        with new_col:
            st.button("New", key="cl_new_template")

    # ====== Two-column frame 0.5 / 0.5 ======
    left, right = st.columns([0.5, 0.5], gap="large")

    # ----------------------------------------
    # LEFT SIDE (Checklist + Confluences, each in its own card)
    # ----------------------------------------
    with left:
        # Checklist + Confluences side-by-side
        cL, cR = st.columns([1, 1], gap="small")

        # ---- Checklist card ----
        with cL:
            st.markdown('<div class="chk-card"></div>', unsafe_allow_html=True)
            with st.container(border=False):
                st.markdown('<div class="card-title">Checklist</div>', unsafe_allow_html=True)
                # Slightly wider Add/Delete controls
                add_c, del_c, _ = st.columns([0.4, 0.5, 1])
                with add_c:
                    st.markdown('<div class="wide-btn">', unsafe_allow_html=True)
                    if st.button("+ Add item", key="cl_add_item"):
                        st.session_state.cl_items.append(
                            {
                                "name": f"Custom ({len(st.session_state.cl_items)+1})",
                                "type": "select",
                                "options": ["No", "Yes"],
                                "value": "Yes",
                                "weight": 6,
                            }
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
                with del_c:
                    st.markdown('<div class="wide-btn">', unsafe_allow_html=True)
                    if st.button("🗑 Delete last", key="cl_del_item", help="danger"):
                        if st.session_state.cl_items:
                            st.session_state.cl_items.pop()
                    st.markdown("</div>", unsafe_allow_html=True)

                # Render each checklist row
                for i, it in enumerate(st.session_state.cl_items):
                    ncol, selcol, wcol = st.columns([1.2, 2.2, 0.7], gap="small")
                    with ncol:
                        st.markdown(
                            f"<div class='item-name'>{it['name']}</div>", unsafe_allow_html=True
                        )
                    with selcol:
                        idx = (
                            it["options"].index(it["value"]) if it["value"] in it["options"] else 0
                        )
                        new_val = st.selectbox(
                            f"{it['name']}_sel",
                            options=it["options"],
                            index=idx,
                            key=f"cl_sel_{i}",
                            label_visibility="collapsed",
                        )
                        it["value"] = new_val
                    with wcol:
                        it["weight"] = int(
                            st.number_input(
                                f"{it['name']}_w",
                                value=int(it.get("weight", 8)),
                                step=1,
                                min_value=0,
                                max_value=30,
                                key=f"cl_w_{i}",
                                label_visibility="collapsed",
                            )
                        )

        # ---- Confluences card (scrollable) ----
        with cR:
            st.markdown('<div class="conf-card"></div>', unsafe_allow_html=True)
            with st.container(border=False):
                headL, headR = st.columns([1, 0.12])
                with headL:
                    st.markdown('<div class="card-title">Confluences</div>', unsafe_allow_html=True)
                    st.caption("Optional boosts. Each adds a small bonus; total bonus is capped.")
                with headR:
                    st.markdown('<div class="kebab">', unsafe_allow_html=True)
                    st.button("⋯", key="cl_conf_kebab")  # borderless
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown('<div class="conf-scroll">', unsafe_allow_html=True)
                remove_idx = None
                for i, c in enumerate(st.session_state.cl_confs):
                    row1, row2, row3, row4 = st.columns([0.12, 1.5, 0.35, 0.23], gap="small")
                    with row1:
                        c["on"] = bool(
                            st.checkbox("", value=bool(c.get("on", True)), key=f"conf_on_{i}")
                        )
                    with row2:
                        c["name"] = st.text_input(
                            "", value=c["name"], key=f"conf_name_{i},", label_visibility="collapsed"
                        )
                    with row3:
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
                    with row4:
                        if st.button("🗑", key=f"conf_del_{i}", help="danger"):
                            remove_idx = i
                if remove_idx is not None:
                    st.session_state.cl_confs.pop(remove_idx)
                st.markdown("</div>", unsafe_allow_html=True)

                addL, addR = st.columns([1, 1])
                with addL:
                    if st.button("Add", key="cl_conf_add"):
                        st.session_state.cl_confs.append(
                            {"name": "New Confluence", "on": True, "pts": 1}
                        )
                with addR:
                    pass  # spacer

        # ---- Overall Score & Grade in its OWN card BELOW ----
        st.markdown('<div class="score-card"></div>', unsafe_allow_html=True)
        with st.container(border=False):
            pct, grade = _score(st.session_state.cl_items, st.session_state.cl_confs)

            dL, dM = st.columns([2.2, 1], gap="small")
            with dL:
                fig = _half_donut_fig("Overall Score", pct)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with dM:
                st.markdown("<div class='ui-subtle center'>Grade</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='center grade-pill'>{grade}</div>", unsafe_allow_html=True)

            # Save for Journal (unchanged logic)
            s1, s2, s3 = st.columns([0.3, 0.4, 0.3])
            with s2:
                if st.button("Save for Journal", key="cl_save_for_journal"):
                    # Build exact checklist lines in fixed order
                    items = {it["name"]: it["value"] for it in st.session_state.cl_items}
                    lines = [
                        f"[{items.get('Bias Confidence','')}] Bias",
                        f"{items.get('Liquidity Sweep','')} Sweep",
                        f"{items.get('Draw on Liquidity','')} DOL",
                        f"{items.get('Momentum','')} Momentum",
                        f"{items.get('iFVG','')} iFVG",
                        f"{items.get('Point of Interest','')} POI",
                    ]
                    st.session_state["pending_checklist"] = {
                        "overall_pct": pct,
                        "overall_grade": grade,
                        "journal_checklist": lines,
                        "journal_confirms": lines,  # legacy key
                    }
                    st.toast("Saved to Journal loader ✅")

    # ----------------------------------------
    # RIGHT SIDE (Chart Examples column) — unchanged functionality
    # ----------------------------------------
    with right:
        # Title size aligned with left card titles
        st.markdown('<div class="section-title">Chart Examples</div>', unsafe_allow_html=True)

        # Card 1
        st.markdown('<div class="chart-card"></div>', unsafe_allow_html=True)
        with st.container(border=False):
            head, keb = st.columns([1, 0.06])
            with head:
                st.markdown("<div class='card-title'>Example 1</div>", unsafe_allow_html=True)
            with keb:
                st.markdown('<div class="kebab">', unsafe_allow_html=True)
                st.button("⋯", key="ex1_kebab")
                st.markdown("</div>", unsafe_allow_html=True)

            u1, f1 = st.columns([1.2, 1], gap="small")
            with u1:
                st.session_state.cl_chart_1["url"] = st.text_input(
                    "Paste image URL",
                    value=st.session_state.cl_chart_1.get("url", ""),
                    key="ex1_url",
                    help="Image renders immediately when a valid URL is provided.",
                )
            with f1:
                st.session_state.cl_chart_1["file"] = st.file_uploader(
                    "or Upload", key="ex1_file", type=["png", "jpg", "jpeg"]
                )

            st.markdown("<div class='img-wrap'>", unsafe_allow_html=True)
            if st.session_state.cl_chart_1.get("file") is not None:
                st.image(st.session_state.cl_chart_1["file"], use_container_width=True)
            elif st.session_state.cl_chart_1.get("url", "").strip():
                st.image(st.session_state.cl_chart_1["url"].strip(), use_container_width=True)
            else:
                st.caption("No image yet.")
            st.markdown("</div>", unsafe_allow_html=True)

        # Card 2
        st.markdown('<div class="chart-card"></div>', unsafe_allow_html=True)
        with st.container(border=False):
            head2, keb2 = st.columns([1, 0.06])
            with head2:
                st.markdown("<div class='card-title'>Example 2</div>", unsafe_allow_html=True)
            with keb2:
                st.markdown('<div class="kebab">', unsafe_allow_html=True)
                st.button("⋯", key="ex2_kebab")
                st.markdown("</div>", unsafe_allow_html=True)

            u2, f2 = st.columns([1.2, 1], gap="small")
            with u2:
                st.session_state.cl_chart_2["url"] = st.text_input(
                    "Paste image URL ",
                    value=st.session_state.cl_chart_2.get("url", ""),
                    key="ex2_url",
                )
            with f2:
                st.session_state.cl_chart_2["file"] = st.file_uploader(
                    "or Upload ", key="ex2_file", type=["png", "jpg", "jpeg"]
                )

            st.markdown("<div class='img-wrap'>", unsafe_allow_html=True)
            if st.session_state.cl_chart_2.get("file") is not None:
                st.image(st.session_state.cl_chart_2["file"], use_container_width=True)
            elif st.session_state.cl_chart_2.get("url", "").strip():
                st.image(st.session_state.cl_chart_2["url"].strip(), use_container_width=True)
            else:
                st.caption("No image yet.")
            st.markdown("</div>", unsafe_allow_html=True)
