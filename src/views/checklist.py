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

    # === Two-pane layout: left = checklist, right = chart examples ===
    left_col, right_col = st.columns([5, 7], gap="large")

    # ------------- LEFT: Checklist editor -------------
    with left_col:
        # ===== Setup selector row (inside LEFT pane) =====
        row_l, row_m, row_r = st.columns([6, 2, 2])

        with row_l:
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
                st.rerun()

        with row_m:
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

        with row_r:
            st.button(
                "Score Settings", use_container_width=True, key="score_settings_btn"
            )  # placeholder

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
        else:
            st.subheader("Items")

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
                        f"<span style='font-size:32px; font-weight:700; line-height:1'>{item['label']}</span>",
                        unsafe_allow_html=True,
                    )

                # --- Compact control row: dropdown + tiny popover [+] on the right ---
                ctrl_col, plus_col = st.columns([10.5, 1.5], gap="small")

                with ctrl_col:
                    options = item.get("options", [])
                    if not isinstance(options, list):
                        options = []
                        item["options"] = options

                    st.selectbox(
                        " ",
                        options or [""],
                        index=0 if options else 0,
                        key=f"preview_val_{item['id']}",
                        label_visibility="collapsed",
                    )

                with plus_col:
                    # Single popover: add and manage options
                    add_pop = st.popover(
                        "＋"
                    )  # your Streamlit doesn't accept key/use_container_width

                    with add_pop:
                        # ---- Add option ----
                        st.caption("Add option")
                        if item["type"] == "scale":
                            new_val = st.number_input(
                                f"num_{item['id']}",
                                value=None,
                                min_value=1,
                                step=1,
                                placeholder="1-10",
                                label_visibility="collapsed",
                            )
                            if st.button(
                                "Add", key=f"add_opt_{item['id']}", use_container_width=True
                            ):
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
                        else:  # select-type
                            new_txt = st.text_input(
                                f"txt_{item['id']}",
                                value="",
                                placeholder="e.g., External / Equal highs",
                                label_visibility="collapsed",
                            )
                            if st.button(
                                "Add", key=f"add_opt_{item['id']}", use_container_width=True
                            ):
                                val = (new_txt or "").strip()
                                if not val:
                                    st.toast("Enter a value first")
                                elif val not in item["options"]:
                                    item["options"].append(val)
                                    st.rerun()
                                else:
                                    st.toast("Already exists")

                        st.markdown(
                            "<hr style='opacity:.15;margin:.5rem 0'>", unsafe_allow_html=True
                        )

                        # ---- Manage / delete existing options ----
                        st.caption("Delete an option")
                        opts = item.get("options", [])
                        sel_key = f"del_sel_{item['id']}"
                        if opts:
                            sel = st.selectbox(" ", opts, key=sel_key, label_visibility="collapsed")
                            if st.button(
                                "Delete",
                                key=f"del_btn_{item['id']}",
                                use_container_width=True,
                                help="Remove selected option",
                            ):
                                if sel in item["options"]:
                                    item["options"].remove(sel)
                                    st.rerun()
                        else:
                            st.write("No options yet.")

    # ------------- RIGHT: Chart Examples -------------
    with right_col:
        st.subheader("Chart Examples")
        st.caption("Upload up to two reference images.")

        u1, u2 = st.columns(2, gap="medium")

        with u1:
            img1 = st.file_uploader(
                "Image 1",
                type=["png", "jpg", "jpeg", "webp"],
                key="chk_img_1",
                label_visibility="collapsed",
            )
            if img1 is not None:
                st.image(img1, use_container_width=True)

        with u2:
            img2 = st.file_uploader(
                "Image 2",
                type=["png", "jpg", "jpeg", "webp"],
                key="chk_img_2",
                label_visibility="collapsed",
            )
            if img2 is not None:
                st.image(img2, use_container_width=True)

    st.divider()
    st.caption("This page defines the template only. Scoring & live use will come next.")
