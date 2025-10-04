# src/views/account.py
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# -------------------------------------------------------------------
# Settings storage
#   settings.json lives next to app.py (repo root). Safe no-op if missing.
# -------------------------------------------------------------------
SETTINGS_PATH = Path(__file__).resolve().parents[2] / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "profile": {
        "username": "",
        "password_hash": "",  # sha256
        "created_at": None,
        "updated_at": None,
    },
    "starting_equity": {"__default__": 5000.0},  # per-account equity
    "journal_groups": {
        # "Crypto ALL": ["Crypto (Live)", "Crypto (Prop)"]
    },
    "defaults": {
        "timeframe": "All Dates",  # topbar default
        "account": "ALL",  # topbar default
        "journal_view": "Styled",  # Journal page default
    },
}


# ------------ settings helpers ------------
def _merge_settings(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = json.loads(json.dumps(base))
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_settings(out[k], v)
        else:
            out[k] = v
    return out


def _load_settings() -> Dict[str, Any]:
    if SETTINGS_PATH.exists():
        try:
            return _merge_settings(
                DEFAULT_SETTINGS, json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            )
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def _save_settings(data: Dict[str, Any]) -> None:
    try:
        SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# -----------------------------------------


# ------------ session helpers ------------
def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def _accounts_from_state() -> List[str]:
    opts = [str(x).strip() for x in st.session_state.get("accounts_options", []) if str(x).strip()]
    extra: List[str] = []
    for key in ("journal_df", "df_view", "df"):
        df = st.session_state.get(key)
        if isinstance(df, pd.DataFrame) and "Account" in df.columns and len(df):
            extra.extend(df["Account"].astype(str).str.strip().dropna().unique().tolist())
    out = list(dict.fromkeys(["ALL"] + opts + extra))
    return [x for x in out if x]


def _sync_to_session(settings: Dict[str, Any]) -> None:
    st.session_state["starting_equity"] = settings.get("starting_equity", {"__default__": 5000.0})
    st.session_state["journal_groups"] = settings.get("journal_groups", {})
    dfl = settings.get("defaults", {})
    st.session_state.setdefault("recent_select", dfl.get("timeframe", "All Dates"))
    st.session_state.setdefault("global_journal_sel", dfl.get("account", "ALL"))
    st.session_state.setdefault("journal_view_mode", dfl.get("journal_view", "Styled"))


# -----------------------------------------


# ------------------ UI helpers ------------------
CSS = """
<style>
/* Centering scaffold: 20% | 60% | 20% */
.acc-wrap { width: 100%; }
.acc-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 18px 18px 8px 18px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25);
}
.acc-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: .2px;
  margin-bottom: 8px;
}
.acc-subtle {
  font-size: 12px;
  opacity: .75;
}

/* Tabs polish */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.stTabs [data-baseweb="tab"] {
  padding: 10px 14px;
  border-radius: 10px 10px 0 0;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-bottom: none;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(180deg, rgba(100,125,255,0.20), rgba(100,125,255,0.05));
}

/* Badges & hints */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.06);
  font-size: 12px;
  color: #d1d5db;
}

/* Section spacing inside the 60% column */
.section-gap { margin-top: 10px; margin-bottom: 10px; }

/* Button subtle hover (keeps your palette) */
button[kind="primary"] {
  transition: transform .06s ease;
}
button[kind="primary"]:hover { transform: translateY(-1px); }

</style>
"""
# ------------------------------------------------


def render_account():
    st.markdown(CSS, unsafe_allow_html=True)

    # load settings once per session, mirror into state
    if "app_settings" not in st.session_state:
        st.session_state["app_settings"] = _load_settings()
        _sync_to_session(st.session_state["app_settings"])
    settings = st.session_state["app_settings"]

    # Centered grid: 20% | 60% | 20%
    left, center, right = st.columns([3, 4, 3])
    with center:
        st.markdown(
            """
            <div style="text-align:center; margin: 0 0 80px 0;">
            <div style="font-size:32px; font-weight:800; letter-spacing:.2px;">
                Account
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        tabs = st.tabs(["Profile", "Starting Equity", "Group Options", "Preferences"])

        # ---------------------- Profile ----------------------
        with tabs[0]:
            with st.container():
                st.markdown('<div class="acc-card">', unsafe_allow_html=True)
                st.markdown('<div class="acc-title">Profile</div>', unsafe_allow_html=True)
                st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

                c1, c2 = st.columns([1, 1])
                with c1:
                    username = st.text_input(
                        "Username",
                        value=settings["profile"].get("username", ""),
                        max_chars=64,
                    )
                with c2:
                    pw = st.text_input(
                        "Password",
                        value="",
                        type="password",
                        help="Leave blank to keep existing password.",
                    )

                # New full-width row just for the button
                PROFILE_BTN_SHIFT = 12  # ← adjust vertical spacing here
                st.markdown(
                    f"<div style='height:{PROFILE_BTN_SHIFT}px'></div>", unsafe_allow_html=True
                )
                if st.button("Save Profile", type="primary", key="acc_save_profile"):
                    now = datetime.utcnow().isoformat()
                    settings["profile"]["username"] = username
                    if pw.strip():
                        settings["profile"]["password_hash"] = _hash_password(pw.strip())
                    settings["profile"]["updated_at"] = now
                    if not settings["profile"]["created_at"]:
                        settings["profile"]["created_at"] = now
                    _save_settings(settings)
                    st.session_state["app_settings"] = settings
                    st.success("Profile saved.")

        # ------------------ Starting Equity ------------------
        with tabs[1]:
            with st.container():
                st.markdown('<div class="acc-card">', unsafe_allow_html=True)
                st.markdown(
                    '<div class="acc-title">Starting Equity (per Account)</div>',
                    unsafe_allow_html=True,
                )

                existing_accounts = _accounts_from_state()
                equity_map = settings.get("starting_equity", {"__default__": 5000.0}).copy()

                rows = []
                for acc in sorted([a for a in existing_accounts if a != "ALL"]):
                    rows.append(
                        {
                            "Account": acc,
                            "Starting Equity ($)": float(
                                equity_map.get(acc, equity_map.get("__default__", 5000.0))
                            ),
                        }
                    )
                df_equity = pd.DataFrame(
                    rows
                    or [
                        {
                            "Account": "NQ",
                            "Starting Equity ($)": float(equity_map.get("__default__", 5000.0)),
                        }
                    ]
                )

                edited = st.data_editor(
                    df_equity,
                    num_rows="dynamic",
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Account": st.column_config.TextColumn(validate="^.{1,64}$"),
                        "Starting Equity ($)": st.column_config.NumberColumn(
                            min_value=0.0, step=100.0, format="%.2f"
                        ),
                    },
                    key="equity_editor",
                )

                c1, c2 = st.columns([1, 1])
                with c1:
                    default_eq = st.number_input(
                        "Default Starting Equity ($) for accounts not listed",
                        min_value=0.0,
                        value=float(equity_map.get("__default__", 5000.0)),
                        step=100.0,
                    )
                with c2:
                    SAVE_EQUITY_BTN_SHIFT = 29  # ← adjust this
                    st.markdown(
                        f"<div style='height:{SAVE_EQUITY_BTN_SHIFT}px'></div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("Save Starting Equity", type="primary", key="acc_save_equity"):
                        new_map = {"__default__": float(default_eq)}
                        for _, r in edited.iterrows():
                            acc = str(r.get("Account", "")).strip()
                            if acc:
                                new_map[acc] = float(r.get("Starting Equity ($)", default_eq))
                        settings["starting_equity"] = new_map
                        _save_settings(settings)
                        st.session_state["app_settings"] = settings
                        st.session_state["starting_equity"] = new_map  # live impact to KPIs
                        st.success("Starting equity saved. KPIs will reflect immediately.")
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

        # ------------------ Group Options --------------------
        with tabs[2]:
            with st.container():
                st.markdown('<div class="acc-card">', unsafe_allow_html=True)
                st.markdown('<div class="acc-title">Journal Groups</div>', unsafe_allow_html=True)
                st.caption(
                    "Create groups that appear in the topbar Account selector (e.g., Crypto ALL → Crypto (Live), Crypto (Prop))."
                )

                accounts = [a for a in _accounts_from_state() if a != "ALL"]
                groups: Dict[str, List[str]] = settings.get("journal_groups", {}).copy()

                gcol1, gcol2 = st.columns([1, 1])
                with gcol1:
                    group_name = st.text_input(
                        "Group name", value="", placeholder="e.g., Crypto ALL"
                    )
                with gcol2:
                    group_members = st.multiselect("Group members", options=accounts, default=[])

                gbtn1, gbtn2, gbtn3 = st.columns([1, 1, 1])

                with gbtn1:
                    # ⬇️ nudge Add/Update button (px)
                    ADD_BTN_SHIFT = 29
                    st.markdown(
                        f"<div style='height:{ADD_BTN_SHIFT}px'></div>", unsafe_allow_html=True
                    )
                    if st.button(
                        "Add / Update Group",
                        type="primary",
                        disabled=not group_name.strip(),
                        key="acc_group_add",
                    ):
                        gname = group_name.strip()
                        groups[gname] = group_members
                        settings["journal_groups"] = groups
                        _save_settings(settings)
                        st.session_state["app_settings"] = settings
                        st.session_state["journal_groups"] = groups
                        st.success(f"Group '{gname}' saved.")
                        st.rerun()

                with gbtn2:
                    del_name = st.selectbox(
                        "Delete group",
                        options=["(pick)"] + sorted(groups.keys()),
                        index=0,
                        key="acc_del_group_sel",
                    )

                with gbtn3:
                    # ⬇️ nudge Delete button (px)
                    DEL_BTN_SHIFT = 29
                    st.markdown(
                        f"<div style='height:{DEL_BTN_SHIFT}px'></div>", unsafe_allow_html=True
                    )
                    if st.button("Delete", disabled=(del_name == "(pick)"), key="acc_group_delete"):
                        if del_name in groups:
                            groups.pop(del_name, None)
                            settings["journal_groups"] = groups
                            _save_settings(settings)
                            st.session_state["app_settings"] = settings
                            st.session_state["journal_groups"] = groups
                            st.success(f"Group '{del_name}' deleted.")
                            st.rerun()

                if groups:
                    st.markdown("**Existing groups**")
                    show = [
                        {"Group": g, "Members": ", ".join(members) if members else "—"}
                        for g, members in groups.items()
                    ]
                    st.dataframe(pd.DataFrame(show), hide_index=True, use_container_width=True)

                st.markdown("</div>", unsafe_allow_html=True)

        # -------------------- Preferences --------------------
        with tabs[3]:
            with st.container():
                st.markdown('<div class="acc-card">', unsafe_allow_html=True)
                st.markdown(
                    '<div class="acc-title">Defaults & Preferences</div>', unsafe_allow_html=True
                )

                tf_options = [
                    "All Dates",
                    "Year to Date (YTD)",
                    "Recent 7 Days",
                    "Recent 30 Days",
                    "Recent 60 Days",
                    "Recent 90 Days",
                ]

                groups = settings.get("journal_groups", {})
                acct_options = (
                    ["ALL"]
                    + sorted(list(groups.keys()))
                    + [a for a in _accounts_from_state() if a != "ALL"]
                )
                acct_options = list(dict.fromkeys(acct_options))  # de-dupe, keep order

                jview_options = ["Styled", "Raw"]

                # current defaults
                d = settings.get("defaults", {})

                # safe indices (don’t crash if value missing)
                _tf_value = d.get("timeframe", "All Dates")
                try:
                    _tf_idx = tf_options.index(_tf_value)
                except ValueError:
                    _tf_idx = 0

                _ac_value = d.get("account", "ALL")
                try:
                    _ac_idx = acct_options.index(_ac_value)
                except ValueError:
                    _ac_idx = 0

                _jv_value = d.get("journal_view", "Styled")
                try:
                    _jv_idx = jview_options.index(_jv_value)
                except ValueError:
                    _jv_idx = 0

                # the widgets (keys on the selectboxes, not on dict.get)
                d_tf = st.selectbox(
                    "Default Timeframe", tf_options, index=_tf_idx, key="acc_pref_tf"
                )
                d_ac = st.selectbox(
                    "Default Account", acct_options, index=_ac_idx, key="acc_pref_acct"
                )
                d_jv = st.selectbox(
                    "Journal default view", jview_options, index=_jv_idx, key="acc_pref_jview"
                )

                if st.button("Save Defaults", type="primary", key="acc_save_defaults"):
                    settings["defaults"] = {
                        "timeframe": d_tf,
                        "account": d_ac,
                        "journal_view": d_jv,
                    }
                    _save_settings(settings)
                    st.session_state["app_settings"] = settings

                    # mirror to live session for immediate effect (will also persist on next boot)
                    st.session_state["recent_select"] = d_tf
                    st.session_state["global_journal_sel"] = d_ac
                    st.session_state["journal_view_mode"] = d_jv

                    st.success("Defaults saved.")
                    st.rerun()

                st.caption(
                    '<span class="badge">Changes persist to settings.json and update the running session.</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)
