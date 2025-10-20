# login.py
import re

import streamlit as st

from src import theme

st.set_page_config(page_title="Login | Edgeboard", page_icon="💠", layout="centered")

# -------------------- manual logo nudge (edit these) --------------------
LOGO_WIDTH = 220  # px
LOGO_NUDGE_X = 0  # px (positive => move right, negative => left)
LOGO_NUDGE_Y = 0  # px (positive => move down, negative => up)
# ------------------------------------------------------------------------

# If already logged-in, go straight to the app
if st.session_state.get("authenticated", False):
    st.switch_page("app.py")

# ----------------------------- CSS -----------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"] * {{
      font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif !important;
    }}
    body {{ background: {theme.BG}; color: {theme.FG}; }}

    .login-scope {{ --logo-x: {LOGO_NUDGE_X}px; --logo-y: {LOGO_NUDGE_Y}px; }}

    /* Center column wrapper */
    .login-scope .login-wrap {{
      max-width: 560px;
      margin: 7vh auto 0;
      padding: 0 16px;
    }}

    /* Center the logo and allow fine positioning via CSS vars */
    .login-scope .login-logo {{
      text-align: center;
      margin-bottom: 6px;
      transform: translate(var(--logo-x), var(--logo-y));
      position: relative;
    }}
    .login-scope .login-logo img {{
      display: block;
      margin: 0 auto;
    }}
    /* Hide the small fullscreen button Streamlit overlays on images */
    .login-scope [data-testid="StyledFullScreenButton"] {{ display: none !important; }}

    /* Lighter input look (slightly lighter than page bg) */
    .login-scope .login-fields [data-testid="stTextInput"] > div > div {{
      background: {theme.BLUE_DARK};                 /* lighter tone */
      border: 1px solid {theme.AXIS_WEAK};
      border-radius: 10px;
    }}
    .login-scope .login-fields input {{
      color: {theme.FG};
      background: transparent;
      padding: 10px 12px;
    }}
    .login-scope label, .login-scope .stTextInput label p {{
      color: {theme.FG_MUTED} !important;
      font-weight: 600 !important;
    }}

    /* Buttons row – not full width */
    .login-scope .btn-row {{
      display: flex;
      gap: 14px;
      justify-content: center;
      align-items: center;
      margin-top: 12px;
    }}
    .login-scope .btn-row .stButton > button {{
      width: auto !important;            /* no full-width */
      min-width: 168px;                  /* tidy minimum */
      padding: 8px 14px !important;
      border-radius: 10px !important;
      font-weight: 800 !important;
      box-shadow: none !important;
    }}

    /* ===== EXACT same blue-outline pattern you use elsewhere ===== */
    .login-scope [data-testid="stButton"] > button {{
      border: 1px solid var(--blue, {theme.BLUE}) !important;
      color: var(--blue, {theme.BLUE}) !important;
      background: transparent !important;
      box-shadow: none !important;
    }}
    .login-scope [data-testid="stFormSubmitButton"] > button {{
      border: 1px solid var(--blue, {theme.BLUE}) !important;
      color: var(--blue, {theme.BLUE}) !important;
      background: transparent !important;
      box-shadow: none !important;
    }}
    /* Popover trigger button (it’s also an stButton under the hood) */
    .login-scope .stPopover > div > button {{
      border: 1px solid var(--blue, {theme.BLUE}) !important;
      color: var(--blue, {theme.BLUE}) !important;
      background: transparent !important;
      box-shadow: none !important;
      border-radius: 10px !important;
      font-weight: 800 !important;
      padding: 8px 14px !important;
      min-width: 168px;
    }}
    /* Optional hover tint (same vibe as rest of app) */
    .login-scope [data-testid="stButton"] > button:hover,
    .login-scope .stPopover > div > button:hover {{
      background: {theme.BLUE_FILL} !important;
      color: var(--blue, {theme.BLUE}) !important;
      border-color: var(--blue, {theme.BLUE}) !important;
    }}

    /* Popover inputs use same lighter style */
    .login-scope .signup-pop [data-testid="stTextInput"] > div > div {{
      background: {theme.BLUE_DARK};
      border: 1px solid {theme.AXIS_WEAK};
      border-radius: 10px;
    }}
    .login-scope .signup-pop input {{
      color: {theme.FG};
      background: transparent;
      padding: 10px 12px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- UI -----------------------------
st.markdown('<div class="login-scope">', unsafe_allow_html=True)
st.markdown('<div class="login-wrap">', unsafe_allow_html=True)

# Centered logo only (no welcome text)
st.markdown('<div class="login-logo">', unsafe_allow_html=True)
st.image("assets/edgeboard_blue.png", width=LOGO_WIDTH)
st.markdown("</div>", unsafe_allow_html=True)

# Inputs (lighter background)
st.markdown('<div class="login-fields">', unsafe_allow_html=True)
username = st.text_input("Username", placeholder="Enter your username", key="login_user")
password = st.text_input(
    "Password", placeholder="Enter your password", type="password", key="login_pass"
)
st.markdown("</div>", unsafe_allow_html=True)

# Buttons: Log In + Create Account (popover) — blue outline + blue text
st.markdown('<div class="btn-row">', unsafe_allow_html=True)
col_login, col_create = st.columns([1, 1])

with col_login:
    login_click = st.button("Log In")

with col_create:
    pop = st.popover("Create Account")
    with pop:
        st.markdown('<div class="signup-pop">', unsafe_allow_html=True)
        st.caption("Create an Edgeboard account")
        new_user = st.text_input("New username", key="signup_user")
        new_pass = st.text_input("New password", type="password", key="signup_pass")
        new_pass2 = st.text_input("Confirm password", type="password", key="signup_pass2")

        def _valid_username(u: str) -> bool:
            return bool(re.fullmatch(r"[A-Za-z0-9._-]{3,32}", u or ""))

        if st.button("Create account", key="signup_btn"):
            if not _valid_username(new_user):
                st.error("Username must be 3–32 chars (letters, numbers, . _ -).")
            elif len(new_pass) < 8:
                st.error("Password must be at least 8 characters.")
            elif new_pass != new_pass2:
                st.error("Passwords do not match.")
            else:
                # Persist to the same session keys used by Account → Profile
                st.session_state["profile_username"] = (new_user or "").strip()
                st.session_state["profile_password"] = new_pass
                st.success("✅ Account created (saved to Profile).")
                st.session_state["authenticated"] = True
                st.switch_page("app.py")
        st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)  # .btn-row


# ----------------------------- Logic -----------------------------
def _verify_user(u: str, p: str) -> bool:
    saved_u = st.session_state.get("profile_username", "")
    saved_p = st.session_state.get("profile_password", "")
    return (u or "").strip() == (saved_u or "").strip() and (p or "") == (saved_p or "")


if login_click:
    if _verify_user(username, password):
        st.success("✅ Login successful!")
        st.session_state["authenticated"] = True
        st.switch_page("app.py")
    else:
        st.error("❌ Invalid credentials.")

st.markdown("</div>", unsafe_allow_html=True)  # .login-wrap
st.markdown("</div>", unsafe_allow_html=True)  # .login-scope
