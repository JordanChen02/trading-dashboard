import streamlit as st

from src.theme import BLUE, BLUE_FILL


def inject_overview_css() -> None:
    st.markdown(
        """
    <style>
      /* --- KPI grid & labels --- */
      .kpi-pack{ margin-top:12px; margin-bottom:12px; }
      .kpi-card-vh{ padding-bottom:18px; min-height:130px; display:flex; flex-direction:column;
                    justify-content:center; align-items:center; gap:8px; }
      .kpi-center{ text-align:center; margin:0; }
      .kpi-number{ font-size:32px; font-weight:800; line-height:1.5; margin:0; }
      .kpi-label{  font-size:14px; color:#cbd5e1; line-height:1.2; margin:0; }

      /* --- progress pill (Win/Loss & Long/Short) --- */
      .pillbar{ width:100%; height:18px; background:#1b2433; border-radius:999px; overflow:hidden; margin:6px 0 17px; }
      .pillbar .win{  height:100%; background:#2E86C1; display:inline-block; }
      .pillbar .loss{ height:100%; background:#212C47; display:inline-block; }

      /* --- Tabs header (Equity Curve) --- */
      div[data-testid="stTabs"] div[role="tablist"]{
        justify-content:flex-end; gap:4px; margin-top:-4px;
      }
      div[data-testid="stTabs"] button[role="tab"]{
        padding:4px 10px;
      }
    </style>
    """,
        unsafe_allow_html=True,
    )


def inject_winstreak_css(brand_color: str = "#2E86C1") -> None:
    st.markdown(
        f"""
    <style>
      .ws-wrap {{ --brand:{brand_color}; }}
      .ws-title{{ font-weight:800; font-size:20px; margin:0 0 8px 0; }}
      .ws-row{{ display:flex; gap:28px; justify-content:space-between; }}
      .ws-col{{ flex:1; display:flex; flex-direction:column; align-items:center; }}
      .ws-main{{ display:flex; align-items:center; gap:10px; }}
      .ws-big{{ font-size:38px; font-weight:800; color:var(--brand); line-height:1; }}
      .ws-badges{{ display:flex; flex-direction:column; gap:6px; margin-left:6px; }}
      .ws-pill{{ min-width:36px; padding:2px 8px; border-radius:10px; text-align:center;
                 font-size:12px; font-weight:700; color:#cbd5e1; }}
      .ws-pill.ws-good{{ background:rgba(46,134,193,.25); border:1px solid rgba(46,134,193,.4); }}
      .ws-pill.ws-bad{{  background:rgba(202,82,82,.25);  border:1px solid rgba(202,82,82,.4); }}
      .ws-foot{{ margin-top:6px; font-size:13px; color:#cbd5e1; }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def inject_filters_css(brand_color: str = BLUE, hover_fill: str = BLUE_FILL) -> None:
    st.markdown(
        f"""
    <style>
    :root {{ --brand:{brand_color}; --blue-fill:{hover_fill}; }}
    .filters-trigger button{{
      background: transparent !important;
      border: 1px solid #233045 !important;
      color: #d5deed !important;
      padding: 6px 12px !important;
      border-radius: 10px !important;
      font-weight: 600;
    }}
    .filters-trigger button:hover{{ background: var(--blue-fill) !important; }}
    .filters-trigger button:focus{{ box-shadow:none !important; outline:none !important; }}
    .filters-trigger button::before{{
      content:"";
      width:16px; height:16px; margin-right:8px;
      display:inline-block; background-color: var(--brand);
      -webkit-mask: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='black' d='M3 4h18l-6.5 7.5V21l-5-2v-7.5L3 4z'/>\
      </svg>") no-repeat center / contain;
              mask: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='black' d='M3 4h18l-6.5 7.5V21l-5-2v-7.5L3 4z'/>\
      </svg>") no-repeat center / contain;
    }}
    .filters-pop {{ min-width: 360px; }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def inject_upload_css(brand_color: str = BLUE, hover_fill: str = BLUE_FILL) -> None:
    st.markdown(
        f"""
    <style>
    :root {{ --brand:{brand_color}; --blue-fill:{hover_fill}; }}
    .upload-trigger button{{
      background: transparent !important;
      border: 1px solid #233045 !important;
      color: #d5deed !important;
      padding: 6px 12px !important;
      border-radius: 10px !important;
      font-weight: 600;
    }}
    .upload-trigger button:hover{{ background: var(--blue-fill) !important; }}
    .upload-trigger button:focus{{ box-shadow:none !important; outline:none !important; }}
    .upload-trigger button::before{{
      content:"";
      width:16px; height:16px; margin-right:8px;
      display:inline-block; background-color: var(--brand);
      -webkit-mask: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='black' d='M5 20h14a1 1 0 0 0 1-1v-4h-2v3H6v-3H4v4a1 1 0 0 0 1 1z'/>\
        <path fill='black' d='M12 3l5 5h-3v6h-4V8H7l5-5z'/>\
      </svg>") no-repeat center / contain;
              mask: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='black' d='M5 20h14a1 1 0 0 0 1-1v-4h-2v3H6v-3H4v4a1 1 0 0 0 1 1z'/>\
        <path fill='black' d='M12 3l5 5h-3v6h-4V8H7l5-5z'/>\
      </svg>") no-repeat center / contain;
    }}
    .upload-pop {{ min-width: 640px; }}
    .upload-pop [data-testid="stFileUploaderDropzone"]{{
      width: 100% !important; min-width: 600px; padding-right: 200px;
    }}

    </style>
    """,
        unsafe_allow_html=True,
    )


def inject_topbar_css() -> None:
    """Topbar (tb) = blue/large/borderless. Controls (cb) = outlined/neutral.
    Strictly scoped to columns that CONTAIN the marker; no global styles."""
    st.markdown(
        f"""
    <style>
      :root {{ --blue-fill: {BLUE_FILL}; }}

      /* ========== TOPBAR ONLY (columns that CONTAIN .tb marker) ========== */
      div[data-testid="column"]:has(.tb) .stButton > button,
      div[data-testid="column"]:has(.tb) .stPopover > div > button {{
        border: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        outline: none !important;
        height: 48px;
        min-width: 48px;
        padding: 8px 12px !important;
        border-radius: 12px !important;
        margin: 0 6px !important;
        color: {BLUE} !important;
        font-size: 20px;  /* emoji fallback size */
      }}
      /* Material icon SVGs in TOPBAR */
      div[data-testid="column"]:has(.tb) [data-testid="stIcon"] svg,
      div[data-testid="column"]:has(.tb) svg {{
        width: 24px; height: 24px;
        color: {BLUE} !important;
        fill:  {BLUE} !important;
      }}
      div[data-testid="column"]:has(.tb) .stButton > button:hover,
      div[data-testid="column"]:has(.tb) .stPopover > div > button:hover {{
        background: var(--blue-fill) !important;
      }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def inject_botbar_css() -> None:
    """CONTROLS ROW ONLY (columns we mark with .cb): outlined, neutral color."""
    st.markdown(
        """
    <style>
      /* Popover triggers ONLY in columns that contain our .cb marker (controls row) */
      div[data-testid="column"]:has(> .cb) .stPopover > div > button {
        border: 1px solid #233045 !important;   /* default outline */
        background: transparent !important;
        color: #d5deed !important;              /* neutral text/icon */
        height: 40px !important;
        min-width: 0 !important;
        padding: 6px 12px !important;
        border-radius: 10px !important;
        margin: 0 8px !important;
      }
      /* Icons inside Calendar/Filters popovers in controls row */
      div[data-testid="column"]:has(> .cb) [data-testid="stIcon"] svg,
      div[data-testid="column"]:has(> .cb) svg {
        width: 18px !important;
        height: 18px !important;
        color: #d5deed !important;
        fill:  #d5deed !important;
      }
    </style>
    """,
        unsafe_allow_html=True,
    )


def inject_header_layout_css() -> None:
    """(Optional) small padding tweak for header rows."""
    st.markdown(
        """
    <style>
      .topbar [data-testid="column"] > div,
      .controls [data-testid="column"] > div {
        padding-left: 2px !important;
        padding-right: 2px !important;
      }
    </style>
    """,
        unsafe_allow_html=True,
    )
