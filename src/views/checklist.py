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
            "type": "scale",
            "options": [str(i) for i in range(1, 11)],
            "enabled": True,
        },
        {
            "id": _uuid(),
            "label": "Liquidity Sweep",
            "type": "select",
            "options": [
                "Equal High/Low",
                "Data High/Low",
                "External High/Low",
                "ITH/ITL",
                "Inducement FVG",
                "Unfilled HTF FVG",
                "LRLR" "None",
            ],
            "enabled": True,
        },
        {
            "id": _uuid(),
            "label": "Draw on Liquidity",
            "type": "select",
            "options": [
                "External High/Low",
                "Data High/Low",
                "Equal High/Low",
                "ITH/ITL",
                "Inducement FVG",
                "Unfilled HTF FVG",
                "LRLR" "None",
            ],
            "enabled": True,
        },
        {
            "id": _uuid(),
            "label": "Momentum",
            "type": "select",
            "options": ["Yes", "No"],
            "enabled": True,
        },
        {
            "id": _uuid(),
            "label": "Obvious FVG",
            "type": "select",
            "options": ["Yes", "No"],
            "enabled": True,
        },
        {
            "id": _uuid(),
            "label": "Point of Interest / Delivery",
            "type": "select",
            "options": ["H4 FVG", "H1 FVG", "M15 FVG", "None"],
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
        st.markdown("<div style='margin-top:-0.75rem'></div>", unsafe_allow_html=True)
        st.subheader("Chart Examples")
        st.caption("Upload up to two reference images or paste image URLs.")

        # ensure state
        if "chart_examples" not in st.session_state:
            st.session_state["chart_examples"] = [
                {"img_bytes": None, "img_url": "https://www.tradingview.com/x/RMJesEwo/"},
                {"img_bytes": None, "img_url": ""},
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
