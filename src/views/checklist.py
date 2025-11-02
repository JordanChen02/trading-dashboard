# src/views/checklist.py
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import plotly.graph_objects as go
import streamlit as st
from PIL import Image


def _new_checklist_dialog():
    def _body():
        new_name = st.text_input("Name", key="cl_new_name", placeholder="e.g., London Session Plan")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Create", type="primary", key="cl_create_btn"):
                name = (new_name or "").strip()
                if not name:
                    st.warning("Enter a name.")
                    return
                if name in st.session_state.cl_templates:
                    st.info("That name already exists.")
                    return
                st.session_state.cl_templates.append(name)
                st.session_state.cl_template_sel = name
                _save_checklist_state()
                st.success(f"Created “{name}”.")
                st.rerun()
        with c2:
            if st.button("Cancel", key="cl_create_cancel"):
                # just close dialog; no state flag needed
                return

    # Use dialog/modal if available, else inline fallback
    dlg = getattr(st, "dialog", None) or getattr(st, "modal", None)
    if callable(dlg):
        decorator = dlg("Create new checklist")

        @decorator
        def _show():
            _body()

        _show()
    else:
        modal_or_inline("Create new checklist", _body)


def _delete_current_template():
    cur = st.session_state.get("cl_template_sel", "")
    lst = st.session_state.get("cl_templates", [])
    if not cur or cur not in lst:
        return
    if len(lst) <= 1:
        st.warning("Keep at least one template.")
        return
    # remove and pick next
    idx = lst.index(cur)
    lst.pop(idx)
    st.session_state.cl_templates = lst
    next_sel = lst[min(idx, len(lst) - 1)]
    st.session_state["cl_template_sel_pending"] = next_sel  # <-- set pending
    _save_checklist_state()
    st.rerun()  # <-- rerun so we can apply before widget renders


# Resolve repo root -> checklist.py is src/views/checklist.py, so parents[2] is repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]

PH_EX1 = _REPO_ROOT / "assets" / "chart_example1.png"
PH_EX2 = _REPO_ROOT / "assets" / "chart_example2.png"


def _img_html_from_bytes(b: bytes) -> str:
    """Return an <img> tag with base64 bytes embedded to avoid first-paint collapse."""
    b64 = base64.b64encode(b).decode("ascii")
    return f'<img src="data:image/png;base64,{b64}" style="width:100%;display:block;" />'


@st.cache_data(show_spinner=False)
def _load_local_img_bytes(p: str | Path) -> bytes | None:
    try:
        p = Path(p)
        if p.exists():
            return p.read_bytes()
    except Exception:
        pass
    return None


# Reserve space so the area doesn't collapse before HTML renders (adjust to taste)
CHART_IMG_MINH = 220
st.markdown(
    f"<style>.chart-img-slot{{min-height:{CHART_IMG_MINH}px}}</style>",
    unsafe_allow_html=True,
)


def _show_local_image(path: Path) -> bool:
    """Open a local image safely and display it. Returns True if shown."""
    try:
        if path and Path(path).exists():
            img = Image.open(path)  # avoids path-resolution hiccups
            st.image(img, use_container_width=True)
            return True
    except Exception:
        pass
    return False


# reserve space so the area doesn't collapse before the image paints
CHART_IMG_MINH = 220  # tweak to taste

st.markdown(
    f"""
    <style>
      .chart-img-slot {{ min-height: {CHART_IMG_MINH}px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def _load_local_img_bytes(p: str | Path):
    try:
        p = Path(p)
        if p.exists():
            return p.read_bytes()
    except Exception:
        pass
    return None


def _ensure_none_for_targets():
    targets = {"point of interest", "poi", "liquidity sweep", "draw on liquidity"}
    for it in st.session_state.get("cl_items", []):
        nm = str(it.get("name", "")).strip().lower()
        if nm in targets:
            opts = list(it.get("options", []))
            pts = dict(it.get("options_points", {}) or {})
            if "None" not in opts:
                opts.append("None")
            if "None" not in pts:
                pts["None"] = 6.0
            it["options"] = opts
            it["options_points"] = pts


# --- modal fallback (unchanged) ---
def modal_or_inline(title: str, render_body):
    dlg = getattr(st, "modal", None) or getattr(st, "dialog", None)
    if callable(dlg):
        decorator = dlg(title)

        @decorator
        def _show():
            render_body()

        _show()
    else:
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


# ---- Theme (fallbacks) ----
try:
    from src.theme import BLUE, CARD_BG
except Exception:
    BLUE = "#3AA4EB"
    CARD_BG = "#0d121f"

RED = "#E06B6B"
FG = "#E5E7EB"
FG_MUTED = "#9AA4B2"
LOCAL_CARD_BG = "#0F1829"
# Local placeholder images to show for TradingView links (add these files to your repo)
PLACEHOLDER_EX1 = "assets/placeholder_tv_ex1.png"
PLACEHOLDER_EX2 = "assets/placeholder_tv_ex2.png"

DATA_DIR = Path(os.environ.get("EDGEBOARD_DATA_DIR", Path.home() / ".edgeboard"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHECKLIST_PATH = DATA_DIR / "checklist.json"


def _load_checklist_state() -> dict:
    if CHECKLIST_PATH.exists():
        try:
            with open(CHECKLIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_checklist_state() -> None:
    payload = {
        "cl_templates": st.session_state.get("cl_templates", []),
        "cl_template_sel": st.session_state.get("cl_template_sel", ""),
        "cl_items": st.session_state.get("cl_items", []),
        "cl_confs": st.session_state.get("cl_confs", []),
        "cl_chart_1": st.session_state.get("cl_chart_1", {"url": "", "file": None}),
        "cl_chart_2": st.session_state.get("cl_chart_2", {"url": "", "file": None}),
        "cl_label_offset": int(st.session_state.get("cl_label_offset", 10)),
    }
    with open(CHECKLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _snapshot_state() -> dict:
    """Lightweight snapshot of the persistent pieces for change-detection."""
    return {
        "cl_templates": list(st.session_state.get("cl_templates", [])),
        "cl_template_sel": st.session_state.get("cl_template_sel", ""),
        "cl_items": list(st.session_state.get("cl_items", [])),
        "cl_confs": list(st.session_state.get("cl_confs", [])),
        "cl_label_offset": int(st.session_state.get("cl_label_offset", 10)),
        "cl_chart_1": dict(st.session_state.get("cl_chart_1", {"url": "", "file": None})),
        "cl_chart_2": dict(st.session_state.get("cl_chart_2", {"url": "", "file": None})),
    }


def _autosave_if_changed(before: dict):
    """Persist to JSON only if something actually changed."""
    after = _snapshot_state()
    if json.dumps(before, sort_keys=True, default=str) != json.dumps(
        after, sort_keys=True, default=str
    ):
        _save_checklist_state()


# ==============================
# Session init & data defaults
# ==============================
BIAS_POINTS = {str(i): float(i) for i in range(1, 11)}
SWEEP_DOL_POINTS = {
    "Equal High/Low": 10.0,
    "Internal High/Low": 9.0,
    "External High/Low": 9.7,
    "Data High/Low": 10.0,
    "ITH/ITL": 9.5,
    "LRLR >3": 10.0,
    "LRLR <3": 9.2,
    "None": 6.0,
    "Unfilled FVG": 9.0,
}
MOMENTUM_POINTS = {"Low": 8.0, "Medium": 8.8, "High": 9.5, "Very High": 10.0}
IFVG_POINTS = {"Small": 8.8, "Medium": 9.6, "Large": 10.0}
POI_POINTS = {
    "Daily FVG": 10.0,
    "H4 FVG": 10.0,
    "H1 FVG": 9.8,
    "M15 FVG": 9.5,
    "M5 FVG >": 9.0,
    "None": 6.0,
}

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

DEFAULT_CONFS: List[Dict] = [
    {"name": "12 EMA (1H)", "on": False, "pts": 2},
    {"name": "12 EMA (4H)", "on": False, "pts": 3},
    {"name": "12 EMA (15m)", "on": False, "pts": 1},
    {"name": "12 EMA (Daily)", "on": False, "pts": 2},
    {"name": "Fundamentals", "on": False, "pts": 2},
    {"name": "CVD", "on": False, "pts": 1},
    {"name": "TSO, TDO", "on": False, "pts": 1},
    {"name": "Key levels", "on": False, "pts": 1},
    {"name": "Stairstep", "on": False, "pts": 2},
]

TEMPLATE_NAMES = ["A+ iFVG Setup", "Custom Template 1"]


def _sync_item_options_to_latest():
    """Ensure session items include any newly added options from constants."""
    name_map = {
        "Liquidity sweep": ("Unfilled FVG", 9.0),
        "draw on liquidity": ("Unfilled FVG", 9.0),
        "point of interest": ("M5 FVG>", 9.0),
        "poi": ("M5 FVG>", 9.0),
    }
    changed = False
    for it in st.session_state.get("cl_items", []):
        nm = str(it.get("name", "")).strip().lower()
        if nm in name_map:
            opt, pts = name_map[nm]
            opts = list(it.get("options", []))
            opp = dict(it.get("options_points", {}) or {})
            if opt not in opts:
                opts.append(opt)
                changed = True
            if opt not in opp:
                opp[opt] = float(pts)
                changed = True
            it["options"] = opts
            it["options_points"] = opp
    if changed:
        _save_checklist_state()


def _ensure_state():
    saved = _load_checklist_state()

    st.session_state.setdefault("cl_templates", saved.get("cl_templates", TEMPLATE_NAMES[:]))
    st.session_state.setdefault("cl_template_sel", saved.get("cl_template_sel", TEMPLATE_NAMES[0]))
    st.session_state.setdefault(
        "cl_items", saved.get("cl_items", [dict(x) for x in DEFAULT_CHECKLIST])
    )
    _ensure_none_for_targets()
    _sync_item_options_to_latest()

    st.session_state.setdefault("cl_confs", saved.get("cl_confs", [dict(x) for x in DEFAULT_CONFS]))
    st.session_state.setdefault(
        "cl_chart_1",
        saved.get("cl_chart_1", {"url": "https://www.tradingview.com/x/RMJesEwo/", "file": None}),
    )
    st.session_state.setdefault(
        "cl_chart_2",
        saved.get("cl_chart_2", {"url": "https://www.tradingview.com/x/fvMNs5k2/", "file": None}),
    )
    st.session_state.setdefault("ex1_menu_open", False)
    st.session_state.setdefault("ex2_menu_open", False)

    st.session_state.setdefault("add_item_open", False)
    st.session_state.setdefault("add_item_title", "")
    st.session_state.setdefault("add_item_rows", [{"opt": "", "pts": 0.0}])

    st.session_state.setdefault("cl_label_offset", int(saved.get("cl_label_offset", 10)))

    st.session_state.setdefault("add_item_force_show_once", False)
    st.session_state.setdefault("add_item_should_reset", False)
    st.session_state.setdefault("add_item_keep_open", False)


# ==============================
# Scoring / grade helpers
# ==============================
def _score(items: List[Dict], confs: List[Dict]) -> Tuple[int, str]:
    n = max(1, len(items))
    per_item_weight = 100.0 / n

    base_pct = 0.0
    for it in items:
        opts_pts: Dict[str, float] = it.get("options_points", {}) or {}
        if not opts_pts:
            continue
        max_pts = max(opts_pts.values())
        sel_key = str(it.get("value", ""))
        sel_pts = float(opts_pts.get(sel_key, 0.0))
        part = 0.0 if max_pts <= 0 else (sel_pts / max_pts) * per_item_weight
        base_pct += part

    # clamp confluence points to >= 0 and numeric
    conf_bonus = 0.0
    for c in confs:
        if c.get("on"):
            try:
                conf_bonus += max(0.0, float(c.get("pts", 0)))
            except Exception:
                pass

    pct = int(round(min(100.0, base_pct + conf_bonus)))

    if pct >= 96:
        grade = "S"
    elif pct >= 94:
        grade = "A+"
    elif pct >= 91:
        grade = "A"
    elif pct >= 89:
        grade = "A-"
    elif pct >= 86:
        grade = "B+"
    elif pct >= 82:
        grade = "B"
    elif pct >= 79:
        grade = "B-"
    else:
        grade = "C"
    return pct, grade


# ==============================
# UI helpers
# ==============================
def _inject_css():
    offset = int(st.session_state.get("cl_label_offset", 10))
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
/* Card shells */
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

/* Checklist criteria labels — nudged DOWN; adjustable via 'cl_label_offset' */
.item-name {{
  color:{FG};
  font-weight:700;
  font-size:14px;
  position: relative;
  top: {offset}px;
}}

.wide-btn .stButton > button {{ padding:8px 18px !important; min-width:{min_w}px; }}

/* laptop top bar vertical alignment */
.tb-down {{ margin-top: 8px; }}               /* lowers the selectbox */
.tb-center .wide-btn .stButton > button {{   /* tiny balance for the button */
  margin-top: 2px;
}}


/* Grade bigger */
.grade-pill {{ font-weight:800; font-size:60px; color:{FG}; }}
</style>
""",
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
      /* lower the selectbox a hair in laptop top bar */
      .tb-center [data-baseweb="select"] { margin-top: 6px; }
      .tb-center [data-testid="stSelectbox"] > div { margin-top: 6px; }
      .tb-center [data-baseweb="select"] { margin-top: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _half_donut_fig(title: str, pct: int) -> go.Figure:
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
# Add Item Modal (unchanged)
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
            st.session_state.add_item_keep_open = True
            st.rerun()

        if st.button("+ Add option", key="add_row_add"):
            rows.append({"opt": "", "pts": 0.0})
            st.session_state.add_item_keep_open = True
            st.rerun()

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
                    st.session_state.add_item_open = False
                    st.session_state.add_item_should_reset = True
                    _save_checklist_state()
                    st.rerun()

    modal_or_inline("Add Checklist Item", _body)


# Fixed button width
min_w = 140


# ==============================
# Main render
# ==============================
def render(*_args, **_kwargs):
    _ensure_state()
    _inject_css()

    # Snapshot state for end-of-run autosave
    _state_before = _snapshot_state()

    # Prevent auto-open
    if st.session_state.get("add_item_open") and not st.session_state.get(
        "add_item_force_show_once", False
    ):
        st.session_state["add_item_open"] = False

    if st.session_state.get("add_item_should_reset"):
        st.session_state["add_item_title"] = ""
        st.session_state["add_item_rows"] = [{"opt": "", "pts": 0.0}]
        st.session_state["add_item_should_reset"] = False

    if st.session_state.get("add_item_keep_open"):
        st.session_state["add_item_open"] = True
        st.session_state["add_item_force_show_once"] = True
        st.session_state["add_item_keep_open"] = False

    # apply pending selection before rendering the widget
    pend = st.session_state.pop("cl_template_sel_pending", None)
    if pend:
        st.session_state["cl_template_sel"] = pend

    # --- Layout mode
    LAPTOP = bool(st.session_state.get("laptop_mode", False))

    # Top bar (centered); laptop removes side gutters
    padL, mid, padR = (
        st.columns([0.01, 0.98, 0.01], gap="small")  # laptop: almost full-bleed
        if LAPTOP
        else st.columns([0.3, 0.6, 0.3], gap="small")  # desktop: centered with gutters
    )
    with mid:
        st.markdown('<div class="tb-center">', unsafe_allow_html=True)

        # two zones: selector (wide) + actions (tight)
        sel_col, actions_col = st.columns([0.84, 0.16], gap="small")

    with sel_col:
        # Make sure current selection is valid before rendering the widget
        templates = st.session_state.get("cl_templates", [])
        if not templates:
            templates = TEMPLATE_NAMES[:]
            st.session_state["cl_templates"] = templates

        cur_sel = st.session_state.get("cl_template_sel")
        if cur_sel not in templates:
            st.session_state["cl_template_sel"] = templates[0] if templates else ""

        # IMPORTANT: no `index=` when using a `key` bound to session_state
        st.selectbox(
            "Setup Checklist",
            templates,
            key="cl_template_sel",
            label_visibility="collapsed",
        )

        with actions_col:
            a1, a2 = st.columns([0.5, 0.6], gap="small")
            with a1:
                if st.button("New", key="cl_new_template"):
                    _new_checklist_dialog()
                st.markdown("</div>", unsafe_allow_html=True)
            with a2:
                if st.button("🗑", key="cl_del_template", help="danger"):
                    _delete_current_template()

        st.markdown("</div>", unsafe_allow_html=True)

    pend = st.session_state.pop("cl_template_sel_pending", None)
    if pend:
        st.session_state["cl_template_sel"] = pend

    # --- Checklist & Confluences side-by-side ---
    if LAPTOP:
        # full width: remove outer gutters, keep a tight inner gap
        padL, checklist_col, confluence_col, padR = st.columns(
            [0.01, 0.495, 0.495, 0.01], gap="small"
        )
    else:
        # centered layout with gutters
        padL, checklist_col, confluence_col, padR = st.columns([0.3, 0.4, 0.4, 0.3], gap="small")

    with checklist_col:
        # === BEGIN: Checklist card (moved out of _render_left_column) ===
        st.markdown('<div class="chk-card"></div>', unsafe_allow_html=True)
        with st.container(border=False):
            header_row = st.columns([2.7, 1, 1.2], gap="small")
            with header_row[0]:
                st.markdown('<div class="card-title">Checklist</div>', unsafe_allow_html=True)
            with header_row[1]:
                st.markdown('<div class="wide-btn">', unsafe_allow_html=True)
                if st.button("+ Add item", key="cl_add_item"):
                    st.session_state.add_item_open = True
                    st.session_state.add_item_force_show_once = True
                st.markdown("</div>", unsafe_allow_html=True)
            with header_row[2]:
                st.markdown('<div class="wide-btn">', unsafe_allow_html=True)
                if st.button("🗑 Delete last", key="cl_del_item", help="danger"):
                    if st.session_state.cl_items:
                        st.session_state.cl_items.pop()
                        _save_checklist_state()
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.add_item_open:
                _add_item_modal()
            if st.session_state.get("add_item_force_show_once"):
                st.session_state["add_item_force_show_once"] = False

            for i, it in enumerate(st.session_state.cl_items):
                ncol, selcol = st.columns([1.2, 3.0], gap="small")
                with ncol:
                    st.markdown(
                        f"<div class='item-name'>{it['name']}</div>", unsafe_allow_html=True
                    )
                with selcol:
                    idx = (
                        it["options"].index(it["value"]) if it.get("value") in it["options"] else 0
                    )
                    it["value"] = st.selectbox(
                        f"{it['name']}_sel",
                        it["options"],
                        index=idx,
                        key=f"cl_sel_{i}",
                        label_visibility="collapsed",
                    )
        st.markdown(
            "<hr style='margin:0.5rem 0; border:0.5px solid rgba(255,255,255,0.1)'>",
            unsafe_allow_html=True,
        )
        # === END: Checklist card ===

    with confluence_col:
        # === BEGIN: Confluences card (moved out of _render_left_column) ===
        st.markdown('<div class="conf-card"></div>', unsafe_allow_html=True)
        with st.container(border=False):
            hL, hR = st.columns([1, 0.18])
            with hL:
                st.markdown('<div class="card-title">Confluences</div>', unsafe_allow_html=True)
                st.caption("Optional boosts. Each adds a small bonus; total bonus is capped.")
            with hR:
                st.markdown('<div class="wide-btn">', unsafe_allow_html=True)
                if st.button("+ Add", key="cl_conf_add"):
                    st.session_state.cl_confs.append(
                        {"name": "New Confluence", "on": False, "pts": 1}
                    )
                    _save_checklist_state()
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="conf-scroll">', unsafe_allow_html=True)
            _changed = False
            remove_idx = None

            for i, c in enumerate(st.session_state.cl_confs):
                old_on = bool(c.get("on", False))
                old_nm = str(c.get("name", ""))
                old_pts = int(c.get("pts", 1))

                r1, r2, r3, r4 = st.columns([0.12, 1.5, 0.35, 0.23], gap="small")
                with r1:
                    new_on = st.checkbox("", value=old_on, key=f"conf_on_{i}")
                with r2:
                    new_nm = st.text_input(
                        "", value=old_nm, key=f"conf_name_{i}", label_visibility="collapsed"
                    )
                with r3:
                    new_pts = st.number_input(
                        "pts",
                        value=old_pts,
                        min_value=0,
                        max_value=5,
                        step=1,
                        key=f"conf_pts_{i}",
                        label_visibility="collapsed",
                    )
                    new_pts = int(new_pts)

                c["on"], c["name"], c["pts"] = bool(new_on), new_nm, int(new_pts)

                if (c["on"] != old_on) or (c["name"] != old_nm) or (c["pts"] != old_pts):
                    _changed = True

                with r4:
                    if st.button("🗑", key=f"conf_del_{i}", help="danger"):
                        remove_idx = i

            if remove_idx is not None:
                st.session_state.cl_confs.pop(remove_idx)
                _save_checklist_state()
                st.rerun()

            if _changed:
                _save_checklist_state()
        # === END: Confluences card ===

    # --- Score row below both cards ---
    padL2, center, padR2 = (
        st.columns([0.01, 0.98, 0.01], gap="small")  # laptop: full width
        if LAPTOP
        else st.columns([0.35, 0.30, 0.35], gap="small")  # desktop: centered
    )
    with center:
        st.markdown('<div class="score-card"></div>', unsafe_allow_html=True)
        with st.container(border=False):
            pct, grade = _score(st.session_state.cl_items, st.session_state.cl_confs)
            gL, gR = st.columns([2.2, 1], gap="small")
        with gL:
            fig = _half_donut_fig("Overall Score", pct)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with gR:
            st.markdown(
                "<div class='ui-subtle' style='text-align:center'>Grade</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='grade-pill' style='text-align:center'>{grade}</div>",
                unsafe_allow_html=True,
            )

    # ↓↓↓ OUTSIDE the score card, directly below it ↓↓↓
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    padL3, save_col, padR3 = (
        st.columns([0.01, 0.98, 0.01], gap="small")  # laptop
        if LAPTOP
        else st.columns([0.35, 0.30, 0.35], gap="small")  # desktop
    )
    with save_col:
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
            st.toast("Saved to Journal ✅")

    # Autosave if anything changed during this run
    _autosave_if_changed(_state_before)
