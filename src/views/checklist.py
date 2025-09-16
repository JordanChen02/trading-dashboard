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
        {
            "id": _uuid(),
            "label": "Bias Confidence",
            "type": "scale",  # scale | select | checkbox (future)
            "options": [str(i) for i in range(1, 11)],  # 1..10 as strings for selectbox
            "enabled": True,
        },
        {
            "id": _uuid(),
            "label": "Liquidity Sweep",
            "type": "select",
            "options": ["External liquidity", "Equal highs", "Equal lows", "Internal", "None"],
            "enabled": True,
        },
    ]


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


# ---------- Page Render ----------


def render(df: pd.DataFrame) -> None:
    _ensure_state()

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
    st.caption("Template editor (MVP). Choose or create a setup, then adjust its items & options.")

    # ===== Setup selector row =====
    left, mid, right = st.columns([5, 2, 2])
    with left:
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
            "Setup Checklist", setup_names, index=active_idx, key="checklist_setup_select"
        )
        if chosen != st.session_state["active_setup"]:
            st.session_state["active_setup"] = chosen

    with mid:
        # Create new setup via popover to collect a name
        try:
            pop = st.popover("＋ New", use_container_width=True)
        except TypeError:
            # older Streamlit fallback
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

    with right:
        # Placeholder for future scoring modal/page
        st.button("Score Settings", use_container_width=True, key="score_settings_btn")
        # (Later: open a modal/popover with per-option weights, must-haves, thresholds)

    st.divider()

    # ===== Template Items =====
    active_name = st.session_state["active_setup"]
    template = st.session_state["checklists"][active_name]
    items = template.get("items", [])

    if not items:
        st.info(
            "This setup has no items yet. We’ll seed two placeholders when you add the first one."
        )
        if st.button("Seed placeholders", key="seed_items_btn"):
            template["items"] = _default_template_items()
            st.rerun()
        return

    st.subheader("Items")

    for idx, item in enumerate(items):
        row_left, row_mid, row_add = st.columns([0.8, 3.2, 2.0], gap="small")
        with row_left:
            # Enabled checkbox (acts like the leading [ ] on each line)
            enabled = st.checkbox(
                "", value=item.get("enabled", True), key=f"itm_enabled_{item['id']}"
            )
            item["enabled"] = enabled

        with row_mid:
            # Label + current control (dropdown for both Bias & Liquidity Sweep in MVP)
            st.write(f"**{item['label']}**")
            # For MVP we're using dropdowns for both, with options shown below. (Scale = 1..10 pre-seeded)
            options = item.get("options", [])
            if not isinstance(options, list):
                options = []
                item["options"] = options

            # Render a dropdown to preview options (this is template-level, not responding)
            # We store the chosen preview value to keep the widget stable; it doesn't affect the template
            prev_key = f"preview_val_{item['id']}"
            st.selectbox(
                " ",
                options or [""],
                index=0 if options else 0,
                key=prev_key,
                label_visibility="collapsed",
            )

        with row_add:
            # Inline "+ Add option" control per item (to extend the dropdown list)
            with st.container(border=True):
                st.caption("Add option")
                # For scale: you might add 11, 12 later; for select: add new category text
                if item["type"] == "scale":
                    new_val = st.number_input(
                        f"num_{item['id']}",
                        value=None,
                        min_value=1,
                        step=1,
                        placeholder="1-10",
                        label_visibility="collapsed",
                    )
                    add = st.button("＋", key=f"add_opt_{item['id']}", use_container_width=True)
                    if add:
                        if new_val is None:
                            st.toast("Enter a number first")
                        else:
                            sval = str(int(new_val))
                            if sval not in item["options"]:
                                item["options"].append(sval)
                                item["options"].sort(
                                    key=lambda x: int(x) if str(x).isdigit() else 9999
                                )
                                st.rerun()
                            else:
                                st.toast("Already exists")
                else:
                    new_txt = st.text_input(
                        f"txt_{item['id']}",
                        value="",
                        placeholder="e.g., External / Equal highs",
                        label_visibility="collapsed",
                    )
                    add = st.button("＋", key=f"add_opt_{item['id']}", use_container_width=True)
                    if add:
                        val = (new_txt or "").strip()
                        if not val:
                            st.toast("Enter a value first")
                        else:
                            if val not in item["options"]:
                                item["options"].append(val)
                                st.rerun()
                            else:
                                st.toast("Already exists")

    st.divider()
    st.caption("This page defines the template only. Scoring & live use will come next.")
