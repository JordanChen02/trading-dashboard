# src/views/checklist.py
from __future__ import annotations

import uuid
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# ---------- Utilities / Defaults ----------


def _uuid() -> str:
    return uuid.uuid4().hex[:8]


def _default_template_items() -> List[Dict[str, Any]]:
    return [
        # 1) Bias: 1..10, weight equals the number itself
        {
            "id": _uuid(),
            "label": "Bias Confidence",
            "type": "scale",
            "options": [str(i) for i in range(1, 11)],
            "weights": {str(i): i for i in range(1, 11)},
            "enabled": True,
        },
        # 2) Liquidity Sweep (with LRLR split)
        {
            "id": _uuid(),
            "label": "Liquidity Sweep",
            "type": "select",
            "options": [
                "Data High/Low",
                "Equal High/Low",
                "External High/Low",
                "ITH/ITL",
                "Inducement FVG",
                "Unfilled HTF FVG",
                "LRLR >3",
                "LRLR <3",
                "Internal High/Low",
                "None",
            ],
            "weights": {
                "Data High/Low": 10,
                "Equal High/Low": 10,
                "External High/Low": 9.7,
                "ITH/ITL": 9.5,
                "Inducement FVG": 8.5,
                "Unfilled HTF FVG": 8,
                "LRLR >3": 10,
                "LRLR <3": 8.5,
                "Internal High/Low": 7.5,
                "None": 6,
            },
            "enabled": True,
        },
        # 3) Draw on Liquidity (same scale as above)
        {
            "id": _uuid(),
            "label": "Draw on Liquidity",
            "type": "select",
            "options": [
                "Data High/Low",
                "Equal High/Low",
                "External High/Low",
                "ITH/ITL",
                "Inducement FVG",
                "Unfilled HTF FVG",
                "LRLR >3",
                "LRLR <3",
                "None",
            ],
            "weights": {
                "Data High/Low": 10,
                "Equal High/Low": 10,
                "External High/Low": 9,
                "ITH/ITL": 9.5,
                "Inducement FVG": 8.7,
                "Unfilled HTF FVG": 8.5,
                "LRLR >3": 10,
                "LRLR <3": 8.5,
                "None": 6,
            },
            "enabled": True,
        },
        # 4) Momentum (Yes/No)
        {
            "id": _uuid(),
            "label": "Momentum",
            "type": "select",
            "options": ["Very High", "High", "Medium", "Low", "Very Low"],
            "weights": {"Very High": 10, "High": 9.5, "Medium": 8.7, "Low": 7, "Very Low": 3},
            "enabled": True,
        },
        # 5) Obvious FVG (Yes/No)
        {
            "id": _uuid(),
            "label": "iFVG",
            "type": "select",
            "options": ["Large", "Medium", "Small"],
            "weights": {"Large": 10, "Medium": 9, "Small": 7},
            "enabled": True,
        },
        # 6) Point of Interest
        {
            "id": _uuid(),
            "label": "Point of Interest",
            "type": "select",
            "options": ["Daily FVG", "H4 FVG", "H1 FVG", "M15 FVG", "M5 FVG >", "None"],
            "weights": {
                "Daily FVG": 10,
                "H4 FVG": 10,
                "H1 FVG": 9.5,
                "M15 FVG": 9,
                "M5 FVG >": 7,
                "None": 6,
            },
            "enabled": True,
        },
    ]


def _default_confluences() -> List[Dict[str, Any]]:
    return [
        {"id": _uuid(), "label": "12 EMA cross 26", "weight": 1, "enabled": True},
        {"id": _uuid(), "label": "12 EMA (4H)", "weight": 2, "enabled": True},
        {"id": _uuid(), "label": "12 EMA (15m)", "weight": 1, "enabled": True},
        {"id": _uuid(), "label": "12 EMA (Daily)", "weight": 2, "enabled": True},
        {"id": _uuid(), "label": "Fundamentals", "weight": 3, "enabled": True},
        {"id": _uuid(), "label": "CVD", "weight": 1, "enabled": True},
        {"id": _uuid(), "label": "OI", "weight": 1, "enabled": True},
        {"id": _uuid(), "label": "SMT", "weight": 1, "enabled": True},
        {"id": _uuid(), "label": "Macro", "weight": 2, "enabled": True},
        {"id": _uuid(), "label": "Stairstep", "weight": 2, "enabled": True},
    ]


def _ensure_confluence_state() -> None:
    if "_confluences" not in st.session_state:
        st.session_state["_confluences"] = _default_confluences()


def _ensure_state() -> None:
    if "checklists" not in st.session_state:
        st.session_state["checklists"] = {}  # name -> template dict
    if "active_setup" not in st.session_state:
        # Seed with a default template on first visit
        st.session_state["active_setup"] = "A+ iFVG Setup"
        st.session_state["checklists"]["A+ iFVG Setup"] = {
            "name": "A+ iFVG Setup",
            "items": _default_template_items(),
        }

    _ensure_confluence_state()

    st.markdown(
        """
        <style>
        /* Hide the little dropdown caret icon */
        div[data-testid="stPopover"] button svg {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------- Page Render ----------


def render(df: pd.DataFrame) -> None:
    _ensure_state()

    # === Two-pane layout: left = checklist, right = chart examples ===
    left_col, right_col = st.columns([5, 7], gap="large")

    # ------------- LEFT: Checklist editor -------------
    with left_col:

        # Header w/ simple SVG icon
        st.markdown(
            """
            <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:0.25rem;">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M9 11l3 3L22 4" stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"
                    stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <h2 style="margin:0;">Checklist</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "Template editor (MVP). Choose or create a setup, then adjust its items & options."
        )

        # ===== Setup selector row (aligned button) =====
        sel_l, sel_r = st.columns([6, 2], gap="small")

        # LEFT: dropdown
        with sel_l:
            setup_names = list(st.session_state["checklists"].keys())
            active_idx = max(
                (
                    setup_names.index(st.session_state["active_setup"])
                    if st.session_state["active_setup"] in setup_names
                    else 0
                ),
                0,
            )
            chosen = st.selectbox(
                "Setup Checklist",
                setup_names,
                index=active_idx,
                key="checklist_setup_select",
            )
            if chosen != st.session_state["active_setup"]:
                st.session_state["active_setup"] = chosen
                st.rerun()

        # RIGHT: “＋ New” (pushed down to align with dropdown input, below its label)
        with sel_r:
            st.markdown("<div style='margin-top:26px'></div>", unsafe_allow_html=True)
            try:
                pop = st.popover("＋ New", use_container_width=True)
            except TypeError:
                pop = st.container()
                st.info("Enter a new setup name below to create it:")
            with pop:
                new_name = st.text_input("New setup name", key="new_setup_name")
                create = st.button("Create", use_container_width=True, key="create_setup_btn")
                if create:
                    name = (new_name or "").strip()
                    if not name:
                        st.warning("Please enter a name.")
                    elif name in st.session_state["checklists"]:
                        st.warning("That setup already exists.")
                    else:
                        st.session_state["checklists"][name] = {
                            "name": name,
                            "items": _default_template_items(),
                        }
                        st.session_state["active_setup"] = name
                        st.rerun()

        st.markdown(
            "<hr style='border:0;height:1px;background:#2a3444;margin:2px 0 10px 0;'>",
            unsafe_allow_html=True,
        )
        # Two-up editor: Checklist (left) and Confluences (right)
        check_col, conf_col = st.columns([1.2, 1.0], gap="large")

        # ===== Template Items (Checklist) =====
        with check_col:
            active_name = st.session_state["active_setup"]
            template = st.session_state["checklists"][active_name]
            items = template.get("items", [])
            # Constrain checklist UI width (centered like the score card)

            if not items:
                st.info(
                    "This setup has no items yet. We’ll seed two placeholders when you add the first one."
                )
                if st.button("Seed placeholders", key="seed_items_btn"):
                    template["items"] = _default_template_items()
                    st.rerun()
            else:
                st.subheader("")

                for idx, item in enumerate(items):
                    # --- Top row: checkbox + BIG label (32px) ---
                    cb_col, label_col = st.columns([0.8, 11.2], gap="small")

                    with cb_col:
                        enabled = st.checkbox(
                            "",
                            value=item.get("enabled", True),
                            key=f"itm_enabled_{item['id']}",
                        )
                        item["enabled"] = enabled

                    with label_col:
                        st.markdown(
                            f"<span style='font-size:24px; font-weight:700; line-height:1'>{item['label']}</span>",
                            unsafe_allow_html=True,
                        )

                    # --- Compact control row: dropdown + tiny popover [+] on the right ---
                    ctrl_col, plus_col = st.columns([10.5, 1.5], gap="small")

                    with ctrl_col:
                        options = item.get("options", [])
                        if not isinstance(options, list):
                            options = []
                            item["options"] = options

                        item.setdefault("weights", {})
                        weights = item["weights"]

                        st.selectbox(
                            " ",
                            options or [""],
                            index=0 if options else 0,
                            key=f"preview_val_{item['id']}",
                            label_visibility="collapsed",
                        )

                    with plus_col:
                        add_pop = st.popover("＋")

                        with add_pop:
                            # --- Header row with caption + info popover ---
                            cap_l, cap_r = st.columns([6, 1], gap="small")
                            with cap_l:
                                st.caption("Add option")
                            with cap_r:
                                st.markdown("<div id='info-scope'>", unsafe_allow_html=True)
                                info = st.popover("ⓘ")
                                st.markdown("</div>", unsafe_allow_html=True)

                                st.markdown(
                                    """
                                    <style>
                                    /* ONLY style the ⓘ trigger inside this scope */
                                    #info-scope [data-testid="stPopover"] button,
                                    #info-scope [data-testid="stPopover"] button:hover,
                                    #info-scope [data-testid="stPopover"] button:focus,
                                    #info-scope [data-testid="stPopover"] button:active {
                                        background: transparent !important;
                                        border: none !important;
                                        box-shadow: none !important;
                                        padding: 0 .25rem !important;
                                        outline: none !important;
                                    }
                                    /* Hide the tiny caret on that one trigger */
                                    #info-scope [data-testid="stPopover"] button svg {
                                        display: none !important;
                                    }
                                    </style>
                                    """,
                                    unsafe_allow_html=True,
                                )

                                with info:
                                    st.markdown(
                                        """
                                        **Scoring 101**
                                        - Each option has a *weight* (points).
                                        - Your *Overall Score* will sum selected weights and can later be normalized.
                                        - Example: Bias=7, Equal High/Low=10 → subtotal = 17.
                                        """,
                                    )

                            # --- Add option: require a score ---
                            if item["type"] == "scale":
                                new_val = st.number_input(
                                    f"num_{item['id']}",
                                    value=None,
                                    min_value=1,
                                    step=1,
                                    placeholder="1-10",
                                    label_visibility="collapsed",
                                )
                                new_score = st.number_input(
                                    f"score_{item['id']}",
                                    value=None,
                                    min_value=0,
                                    step=1,
                                    placeholder="Score (points)",
                                    label_visibility="collapsed",
                                )
                                if st.button(
                                    "Add", key=f"add_opt_{item['id']}", use_container_width=True
                                ):
                                    if new_val is None or new_score is None:
                                        st.toast("Enter a value and its score")
                                    else:
                                        sval = str(int(new_val))
                                        if sval not in item["options"]:
                                            item["options"].append(sval)
                                            item["options"].sort(
                                                key=lambda x: int(x) if str(x).isdigit() else 9999
                                            )
                                        # always set/overwrite weight
                                        item["weights"][sval] = int(new_score)
                                        st.rerun()
                            else:  # select-type
                                new_txt = st.text_input(
                                    f"txt_{item['id']}",
                                    value="",
                                    placeholder="Option label (e.g., External High/Low)",
                                    label_visibility="collapsed",
                                )
                                new_score = st.number_input(
                                    f"score_{item['id']}",
                                    value=None,
                                    min_value=0,
                                    step=1,
                                    placeholder="Score (points)",
                                    label_visibility="collapsed",
                                )
                                if st.button(
                                    "Add", key=f"add_opt_{item['id']}", use_container_width=True
                                ):
                                    label = (new_txt or "").strip()
                                    if not label or new_score is None:
                                        st.toast("Enter an option label and its score")
                                    else:
                                        if label not in item["options"]:
                                            item["options"].append(label)
                                        item["weights"][label] = int(new_score)
                                        st.rerun()

                            st.markdown(
                                "<hr style='opacity:.15;margin:.5rem 0'>", unsafe_allow_html=True
                            )

                            # --- Manage existing options: edit score or delete ---
                            st.caption("Manage options")
                            opts = item.get("options", [])
                            if not opts:
                                st.write("No options yet.")
                            else:
                                sel_key = f"manage_sel_{item['id']}"
                                sel = st.selectbox(
                                    " ", opts, key=sel_key, label_visibility="collapsed"
                                )
                                # current score (fallback 0 if not set yet)
                                cur = item["weights"].get(sel, 0)
                                edit_col, del_col = st.columns([3, 1], gap="small")
                                with edit_col:
                                    new_w = st.number_input(
                                        f"edit_score_{item['id']}",
                                        value=float(cur),
                                        min_value=0.0,
                                        step=1.0,
                                        label_visibility="collapsed",
                                    )
                                    if st.button(
                                        "Update score",
                                        key=f"upd_{item['id']}",
                                        use_container_width=True,
                                    ):
                                        item["weights"][sel] = int(new_w)
                                        st.rerun()
                                with del_col:
                                    if st.button(
                                        "Delete", key=f"del_{item['id']}", use_container_width=True
                                    ):
                                        # remove from options and weights
                                        if sel in item["options"]:
                                            item["options"].remove(sel)
                                        item["weights"].pop(sel, None)
                                        st.rerun()

            # ===== Confluences (optional bonus) =====
            with conf_col:
                st.markdown("<div style='margin-top:60px'></div>", unsafe_allow_html=True)
                with st.container(border=True):
                    head_l, head_r = st.columns([7, 3], gap="small")
                    with head_l:
                        st.markdown("**Confluences**")
                        st.caption(
                            "Optional boosts. Each adds a small bonus; total bonus is capped."
                        )
                    with head_r:
                        addp = st.popover("＋ Add", use_container_width=True)
                        with addp:
                            _label = st.text_input("Label", placeholder="e.g., SMT (ES vs NQ)")
                            _w = st.number_input(
                                "Weight", min_value=1, max_value=4, value=2, step=1
                            )
                            if st.button("Add confluence", use_container_width=True):
                                if _label.strip():
                                    st.session_state["_confluences"].append(
                                        {
                                            "id": _uuid(),
                                            "label": _label.strip(),
                                            "weight": int(_w),
                                            "enabled": True,
                                        }
                                    )
                                    st.rerun()

                    confs = st.session_state["_confluences"]
                    if not confs:
                        st.info("No confluences yet. Use **＋ Add** to create one.")
                    else:
                        for c in confs:
                            row = st.columns([0.7, 6.8, 1.8, 1.2], gap="small")
                            with row[0]:
                                c["enabled"] = st.checkbox(
                                    "", value=c.get("enabled", True), key=f"c_en_{c['id']}"
                                )
                            with row[1]:
                                st.markdown(f"**{c['label']}**")
                            with row[2]:
                                c["weight"] = int(
                                    st.number_input(
                                        " ",
                                        value=int(c.get("weight", 2)),
                                        min_value=1,
                                        max_value=4,
                                        step=1,
                                        key=f"c_w_{c['id']}",
                                        label_visibility="collapsed",
                                    )
                                )
                            with row[3]:
                                if st.button("🗑", key=f"c_del_{c['id']}", use_container_width=True):
                                    st.session_state["_confluences"] = [
                                        x for x in confs if x["id"] != c["id"]
                                    ]
                                    st.rerun()

                    # # live bonus preview
                    # _bonus_pts = sum(int(c["weight"]) for c in st.session_state["_confluences"] if c.get("enabled", True"))
                    # MAX_BONUS_PCT = 8
                    # st.caption(f"Bonus potential: +{min(_bonus_pts, MAX_BONUS_PCT)}% (cap {MAX_BONUS_PCT}%)")

        # ===== Overall Score (card) =====
        def _grade_from_pct(p: float) -> str:
            # A+, A, A-, B+, B, B-, C+, C, C- ; below 70% = D/F
            if p >= 97:
                return "A+"
            if p >= 93:
                return "A"
            if p >= 90:
                return "A-"
            if p >= 87:
                return "B+"
            if p >= 83:
                return "B"
            if p >= 80:
                return "B-"
            if p >= 77:
                return "C+"
            if p >= 73:
                return "C"
            if p >= 70:
                return "C-"
            return "D/F"

        def compute_checklist_percent_and_grade(
            items: list[dict], selections: dict[str, str]
        ) -> tuple[float, str, int, int]:
            """
            items: checklist template items (with 'id','type','options','weights','enabled')
            selections: map of item['id'] -> selected option (string; numbers should be str for scales)
            Returns: (percent, letter_grade, total_points, max_points)
            """
            total = 0
            denom = 0
            for it in items:
                if not it.get("enabled", True):
                    continue

                options = it.get("options", []) or []
                weights = it.get("weights", {}) or {}
                sel = selections.get(it["id"], None)

                if it["type"] == "scale":
                    # scale: value is usually '1'..'10' as string; fallback to numeric sel
                    try:
                        sel_w = int(weights.get(str(sel), sel or 0) or 0)
                    except Exception:
                        sel_w = 0
                    if weights:
                        max_w = max(weights.values() or [0])
                    else:
                        try:
                            max_w = max(int(x) for x in options) if options else 0
                        except Exception:
                            max_w = 0
                else:
                    sel_w = int(weights.get(sel, 0)) if sel is not None else 0
                    max_w = max(list(weights.values()) or [0])

                total += sel_w
                denom += max_w

            pct = (total / denom * 100.0) if denom > 0 else 0.0
            return pct, _grade_from_pct(pct), total, denom

        # compute normalized score from current selections
        total = 0
        denom = 0
        for it in items:
            if not it.get("enabled", True):
                continue

            opts = it.get("options", []) or []
            weights = it.get("weights", {}) or {}

            sel_key = f"preview_val_{it['id']}"
            sel = st.session_state.get(sel_key, None)

            if it["type"] == "scale":
                try:
                    sel_w = int(weights.get(str(sel), sel or 0) or 0)
                except Exception:
                    sel_w = 0
                if weights:
                    max_w = max(weights.values() or [0])
                else:
                    try:
                        max_w = max(int(x) for x in opts) if opts else 0
                    except Exception:
                        max_w = 0
            else:
                sel_w = int(weights.get(sel, 0)) if sel is not None else 0
                max_w = max(list(weights.values()) or [0])

            total += sel_w
            denom += max_w

        percent = (total / denom * 100.0) if denom > 0 else 0.0
        # Base% (from checklist) already computed as `percent`
        base_pct = float(percent)

        # Bonus% from confluences (capped)
        MAX_BONUS_PCT = 8
        bonus_pct = min(
            sum(
                int(c["weight"]) for c in st.session_state["_confluences"] if c.get("enabled", True)
            ),
            MAX_BONUS_PCT,
        )

        # ----- Helpers to read selections by label (for gates/tiers) -----
        def _items_by_label(items_list):
            return {it.get("label", ""): it for it in items_list}

        def _sel_for_label(lbl: str) -> str:
            it = _items_by_label(items).get(lbl)
            if not it:
                return ""
            key = f"preview_val_{it['id']}"
            return str(st.session_state.get(key, "") or "")

        # ----- Tiering rules (S / A+ / A …) with gates & forgiveness -----
        def _final_tier(base_pct: float, adj_pct: float) -> str:
            # Must-have gates: Liquidity Sweep and Momentum thresholds
            sweep = _sel_for_label("Liquidity Sweep")
            momentum = _sel_for_label("Momentum")

            core_ok = (momentum in {"Very High", "High", "Medium"}) and (
                sweep
                in {
                    "Data High/Low",
                    "Equal High/Low",
                    "External High/Low",
                    "ITH/ITL",
                    "Inducement FVG",
                    "Unfilled HTF FVG",
                    "LRLR >3",
                    "LRLR <3",
                    "Internal High/Low",
                }
            )

            # one-soft-spot forgiveness: allow one non-must-have to be ≤3 pts from max
            # Identify non-must-have misses
            misses = []
            for it in items:
                if not it.get("enabled", True):
                    continue
                lbl = it.get("label", "")
                if lbl in {"Liquidity Sweep", "Momentum"}:
                    continue  # must-haves handled by gates
                weights = it.get("weights", {}) or {}
                opts = it.get("options", []) or []
                # get selected weight
                sel_key = f"preview_val_{it['id']}"
                sel = st.session_state.get(sel_key, None)
                if it["type"] == "scale":
                    try:
                        sel_w = int(weights.get(str(sel), sel or 0) or 0)
                    except Exception:
                        sel_w = 0
                    max_w = max(weights.values() or ([max(int(x) for x in opts)] if opts else [0]))
                else:
                    sel_w = int(weights.get(sel, 0)) if sel is not None else 0
                    max_w = max(list(weights.values()) or [0])
                if max_w > sel_w:
                    misses.append(max_w - sel_w)

            one_soft_spot = len(misses) == 1 and misses[0] <= 3

            # S-tier: elite sweep + momentum with near-perfect base
            if core_ok and (
                (
                    base_pct >= 96.0
                    and sweep in {"Data High/Low", "Equal High/Low", "External High/Low"}
                    and momentum in {"Very High", "High"}
                )
                or (base_pct >= 94.0 and one_soft_spot and momentum in {"Very High", "High"})
            ):
                return "S"

            # A+ tier from adjusted % (bonus allowed) + gates
            if core_ok and adj_pct >= 95.0:
                return "A+"

            # Else fall back to letter via adjusted %
            # (If gates fail, cap at B+)
            if not core_ok and adj_pct >= 87.0:
                return "B+"
            # use your existing thresholds for others
            return _grade_from_pct(adj_pct)

        adj_pct = min(100.0, base_pct + float(bonus_pct))
        grade = _final_tier(base_pct, adj_pct)

        def _score_gauge(percent: float, height: int = 110):
            import plotly.graph_objects as go

            pct = max(0.0, min(100.0, float(percent)))
            panel_bg = "#0b0f19"  # same panel tone as Overview KPIs
            fill_col = "#2E86C1"  # brand blue
            rest_col = "#212C47"  # unfilled arc

            fig = go.Figure(
                go.Indicator(
                    mode="gauge",
                    value=pct,
                    gauge={
                        "shape": "angular",  # half-donut
                        "axis": {"range": [0, 100], "visible": False},
                        "bar": {"color": "rgba(0,0,0,0)"},
                        "borderwidth": 0,
                        "steps": [
                            {"range": [0, pct], "color": fill_col},
                            {"range": [pct, 100], "color": rest_col},
                        ],
                    },
                    domain={"x": [0, 1], "y": [0, 1]},
                )
            )
            fig.update_layout(
                margin=dict(l=8, r=8, t=0, b=0),
                height=height,
                paper_bgcolor=panel_bg,
                showlegend=False,
            )
            # center the % inside the gauge
            fig.add_annotation(
                x=0.5,
                y=0.10,
                xref="paper",
                yref="paper",
                text=f"{pct:.0f}%",
                showarrow=False,
                font=dict(size=26, color="#e5e7eb", family="Inter, system-ui, sans-serif"),
                align="center",
            )
            return fig

        # --- Centered, compact score card ---
        pad_l, card, pad_r = st.columns([1, 3, 1])  # center the card; feel free to tweak 1,3,1
        with card:
            with st.container(border=True):
                left, right = st.columns([4, 1], gap="small")

                with left:
                    # label above the donut
                    st.markdown(
                        "<div style='text-align:center; font-size:18px; font-weight:600; margin:0 0 6px;'>Overall Score</div>",
                        unsafe_allow_html=True,
                    )

                    fig = _score_gauge(adj_pct, height=110)  # smaller half-donut
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

                with right:
                    st.markdown(
                        "<div style='font-size:18px; font-weight:600; margin:0 0 6px; text-align:center;'>Grade</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div style='font-size:44px; font-weight:700;  text-align:center;'>{grade}</div>",
                        unsafe_allow_html=True,
                    )

        # --- Save for Journal (button + build confirmations) ---
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Save for Journal", use_container_width=True, key="btn_save_for_journal"):
            # Grab current dropdown selections by label
            selections_by_label: dict[str, str] = {}
            for it in items:
                if not it.get("enabled", True):
                    continue
                lbl = it.get("label", "")
                key = f"preview_val_{it['id']}"
                val = str(st.session_state.get(key, "") or "")
                selections_by_label[lbl] = val

            # Mapper: Checklist → Confirmation text (exclude Bias Confidence)
            def _mk_confirms(sel: dict[str, str]) -> list[str]:
                out: list[str] = []
                v = sel.get("Liquidity Sweep", "")
                if v and v != "None":
                    out.append(f"{v} (Sweep)")  # e.g., "Equal High/Low (Sweep)"
                v = sel.get("Draw on Liquidity", "")
                if v and v != "None":
                    out.append(f"{v} (DOL)")  # e.g., "External High/Low (DOL)"
                v = sel.get("Momentum", "")
                if v:
                    out.append(f"{v} momentum")  # e.g., "High momentum"
                v = sel.get("iFVG", "")
                if v:
                    out.append(f"{v} iFVG")  # e.g., "Large iFVG"
                v = sel.get("Point of Interest", "")
                if v and v != "None":
                    out.append(v)  # e.g., "Daily FVG"
                return out

            conf_from_dropdowns = _mk_confirms(selections_by_label)

            # Confluences: include those that are checked/enabled
            checked_confs = [
                c["label"]
                for c in st.session_state.get("_confluences", [])
                if c.get("enabled", True)
            ]

            # Final list with order preserved and de-duped
            journal_confirms = list(dict.fromkeys(conf_from_dropdowns + checked_confs))

            st.session_state["pending_checklist"] = {
                "timestamp": pd.Timestamp.utcnow().isoformat(),
                "setup": st.session_state.get("active_setup", ""),
                "selections": selections_by_label,
                "confluences": checked_confs,
                "score_pct": float(adj_pct),
                "grade": grade,
                "journal_confirms": journal_confirms,  # <-- what Journal loads
            }
            st.toast("Checklist saved for Journal ✅")

    # ------------- RIGHT: Chart Examples -------------
    with right_col:
        st.markdown("<div style='margin-top:-0.75rem'></div>", unsafe_allow_html=True)
        st.subheader("Chart Examples")
        st.caption("Upload up to two reference images or paste image URLs.")

        # ensure state
        if "chart_examples" not in st.session_state:
            st.session_state["chart_examples"] = [
                {"img_bytes": None, "img_url": "https://www.tradingview.com/x/RMJesEwo/"},
                {"img_bytes": None, "img_url": "https://www.tradingview.com/x/fvMNs5k2/"},
            ]

        def _render_chart_card(i: int, title: str):
            state = st.session_state["chart_examples"][i]
            with st.container(border=True):
                # header: title + actions
                h_l, h_r = st.columns([8.5, 1.5])
                with h_l:
                    st.markdown(f"**{title}**")
                with h_r:
                    # small actions popover
                    menu = st.popover("⋯")
                    with menu:
                        st.caption("Manage")
                        # choose source
                        src = st.radio(
                            "Source",
                            ["Upload", "URL"],
                            index=0,
                            horizontal=True,
                            key=f"ce_src_{i}",
                        )

                        if src == "Upload":
                            up = st.file_uploader(
                                "Upload image",
                                type=["png", "jpg", "jpeg", "webp"],
                                key=f"ce_up_{i}",
                            )
                            if up is not None:
                                # store raw bytes so it persists across reruns
                                state["img_bytes"] = up.read()
                                state["img_url"] = ""
                                st.session_state["chart_examples"][i] = state
                                st.success("Image saved.")
                                st.rerun()
                        else:
                            url = st.text_input(
                                "Image URL (must point directly to an image)",
                                value=state.get("img_url", ""),
                                key=f"ce_url_{i}",
                                placeholder="https://.../chart.png",
                            )
                            if st.button(
                                "Save URL", key=f"ce_save_url_{i}", use_container_width=True
                            ):
                                state["img_url"] = url.strip()
                                state["img_bytes"] = None
                                st.session_state["chart_examples"][i] = state
                                st.success("URL saved.")
                                st.rerun()

                        st.markdown("---")
                        # delete
                        if st.button("🗑 Delete", key=f"ce_del_{i}", use_container_width=True):
                            state["img_bytes"] = None
                            state["img_url"] = ""
                            st.session_state["chart_examples"][i] = state
                            st.success("Removed.")
                            st.rerun()

                # body: preview or placeholder
                if state.get("img_bytes"):
                    st.image(state["img_bytes"], use_container_width=True)
                elif state.get("img_url"):
                    st.image(state["img_url"], use_container_width=True)
                else:
                    # neat placeholder with guidance
                    st.info(
                        "No image yet — use the ⋯ menu to upload or paste an image URL.", icon="🖼️"
                    )

        # stack cards vertically
        _render_chart_card(0, "Example 1")
        st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
        _render_chart_card(1, "Example 2")

    st.divider()
    st.caption("This page defines the template only. Scoring & live use will come next.")
