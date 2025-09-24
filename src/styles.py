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
    """Topbar: blue icons, borderless buttons — column-scoped by marker.
    Works on Streamlit DOMs that use either stColumn or column."""
    st.markdown(
        f"""
<style>
  /* === Base button (stButton + popover trigger) === */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stButton"] > button,
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stPopover"] > div > button {{
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    outline: none !important;

    height: 60px !important;
    min-width: 60px !important;
    padding: 12px !important;               /* equal padding centers the fill */
    border-radius: 12px !important;
    margin: 2px 10px !important;               /* spacing between buttons */

    color: {BLUE} !important;
    font-size: 32px !important;             /* emoji fallback size */

    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 0 !important;              /* kill baseline quirk */
    box-sizing: border-box !important;
  }}

  /* Hover fill */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stButton"] > button:hover,
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stPopover"] > div > button:hover {{
    background: {BLUE_FILL} !important;
  }}

  /* Icon size/color (Material SVGs) */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stButton"] svg,
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stPopover"] svg {{
    width: 32px; height: 32px;
    color: {BLUE} !important;
    fill:  {BLUE} !important;
  }}
  /* Non-profile buttons: nudge ONLY the icon/text left */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker)
    [data-testid="stButton"] > button :where(svg, span, p) {{
    transform: translateX(-2px);   /* adjust: -1px..-3px */
  }}

  /* Profile popover trigger: no nudge */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker)
    [data-testid="stPopover"] > div > button :where(svg, span, p) {{
    transform: none;
  }}

  /* Ensure SVGs aren’t baseline-aligned like text */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stButton"] > button svg,
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stPopover"] > div > button svg {{
    display: block !important;
    margin: 0 !important;
  }}

  /* Emoji / text label size inside the button (affects 🌐 🔔 ⛶ ☼ fallbacks) */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stButton"] > button :where(span, p),
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stPopover"] > div > button :where(span, p) {{
    font-size: 28px !important;
    line-height: 1 !important;
    margin: 0 !important;
  }}

  /* Micro-nudge: shift NON-profile buttons (stButton) left so icon is visually centered in the hover fill */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stButton"] > button {{
    transform: translateX(-2px);            /* adjust to taste: -1px..-3px */
    will-change: transform;
  }}

  /* Keep the profile popover trigger centered */
  div:is([data-testid="stColumn"], [data-testid="column"]):has(.tb, .tb-marker) [data-testid="stPopover"] > div > button {{
    transform: none;
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
      /* Popover triggers ONLY in columns that contain our .cb markdiv:is([data-testid="stColumn"], [data-testid="column"]):has(> .cb) .stPopover > div > button {
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
      div:is([data-testid="stColumn"], [data-testid="column"]):has(> .cb) [data-testid="stIcon"] svg,
      div:is([data-testid="stColumn"], [data-testid="column"]):has(> .cb) svg {
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
    """Global header/layout tweaks:
    - Left-align tabs
    - Tighten header spacing
    - Column padding fixes for topbar/controls
    - Right-align the Month + Filters pair
    """
    st.markdown(
        """
<style>
/* ===== Tabs: left align + spacing ===== */
div[data-testid="stTabs"] [role="tablist"] {
  justify-content: flex-start !important;
}
div[data-testid="stTabs"] [role="tab"] {
  margin-right: 16px !important;
  flex: 0 0 auto !important;
}
div[data-testid="stTabs"] [role="tab"]:last-child {
  margin-right: 0 !important;
}

/* ===== Column padding tighten for topbar & controls ===== */
.topbar div:is([data-testid="stColumn"], [data-testid="column"]) > div,
.controls div:is([data-testid="stColumn"], [data-testid="column"]) > div {
  padding-left: 2px !important;
  padding-right: 2px !important;
}

/* ===== Tighten vertical spacing around the title/controls row ===== */
/* Target the row that contains the Month popover (cal-marker) */
div[data-testid="stHorizontalBlock"]:has(
  > div:is([data-testid="stColumn"], [data-testid="column"]) .cal-marker
){
  margin-top: -10px !important;     /* pull the row upward; tweak -6px … -16px */
  margin-bottom: 20px !important;   /* add space under the row */
  display: flex !important;         /* ensure it's a flex row */
  align-items: center !important;
}

/* Remove extra top margin on the H1 inside that row */
div[data-testid="stHorizontalBlock"]:has(
  > div:is([data-testid="stColumn"], [data-testid="column"]) .cal-marker
) [data-testid="stMarkdownContainer"] h1 {
  margin-top: 0 !important;
  line-height: 1.1 !important;
}

/* Optional: slightly tighter dividers across the page */
hr {
  margin-top: 6px !important;
  margin-bottom: 8px !important;
}

/* ===== Right-align Month + Filters (final, safe) ===== */
/* Push the Month column (the one with .cal-marker) all the way to the right */
div[data-testid="stHorizontalBlock"]:has(
  > div:is([data-testid="stColumn"], [data-testid="column"]) .cal-marker
) > div:is([data-testid="stColumn"], [data-testid="column"]):has(.cal-marker) {
  margin-left: auto !important;     /* this shoves the Month+Filters pair right */
}

/* Keep Filters snug to the edge: remove inner right padding on its column */
div[data-testid="stHorizontalBlock"]:has(
  > div:is([data-testid="stColumn"], [data-testid="column"]) .filters-marker
) > div:is([data-testid="stColumn"], [data-testid="column"]):has(.filters-marker) > div {
  padding-right: 0 !important;
}

/* Nice gap between Month and Filters buttons */
div[data-testid="stHorizontalBlock"]:has(
  > div:is([data-testid="stColumn"], [data-testid="column"]) .cal-marker
) > div:is([data-testid="stColumn"], [data-testid="column"]):has(.cal-marker)
  [data-testid="stPopover"] > div > button {
  margin-right: 12px !important;    /* tweak to taste: 8–16px */
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_isolated_ui_css() -> None:
    """Isolate styles to exact widgets using the markdown container that has our marker, then the next widget."""
    st.markdown(
        f"""
    <style>
      :root {{ --blue-fill: {BLUE_FILL}; }}

      /* ===== TOPBAR ONLY (marker is inside a markdown container) ===== */
      div[data-testid="stMarkdownContainer"]:has(.tb-marker) ~ div[data-testid="stButton"] > button,
      div[data-testid="stMarkdownContainer"]:has(.tb-marker) ~ div[data-testid="stPopover"] > div > button {{
        border: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        outline: none !important;
        height: 48px; min-width: 48px;
        padding: 8px 12px !important;
        border-radius: 12px !important;
        margin: 0 6px !important;
      }}
      div[data-testid="stMarkdownContainer"]:has(.tb-marker) ~ div[data-testid="stButton"] > button:hover,
      div[data-testid="stMarkdownContainer"]:has(.tb-marker) ~ div[data-testid="stPopover"] > div > button:hover {{
        background: var(--blue-fill) !important;
      }}
      /* Icon color/size in TOPBAR */
      div[data-testid="stMarkdownContainer"]:has(.tb-marker) ~ div[data-testid="stButton"] svg,
      div[data-testid="stMarkdownContainer"]:has(.tb-marker) ~ div[data-testid="stPopover"] svg {{
        width: 24px; height: 24px;
        color: {BLUE} !important;
        fill:  {BLUE} !important;
      }}

      /* ===== TOPBAR CONTAINER (markerless fallback) ===== */
      .topbar .stButton > button,
      .topbar .stPopover > div > button {{
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
        font-size: 20px;
      }}
      .topbar [data-testid="stIcon"] svg,
      .topbar svg {{
        width: 24px; height: 24px;
        color: {BLUE} !important;
        fill:  {BLUE} !important;
      }}
      .topbar .stButton > button:hover,
      .topbar .stPopover > div > button:hover {{
        background: var(--blue-fill) !important;
      }}

      /* ===== CONTROLS ROW ONLY (Calendar & Filters) ===== */
      div[data-testid="stMarkdownContainer"]:has(.cal-marker) + div[data-testid="stPopover"] > div > button,
      div[data-testid="stMarkdownContainer"]:has(.filters-marker) + div[data-testid="stPopover"] > div > button {{
        border: 1px solid #233045 !important;
        background: transparent !important;
        color: #d5deed !important;
        height: 40px; min-width: 0;
        padding: 6px 12px !important;
        border-radius: 10px !important;
        margin: 0 8px !important;
      }}
      div[data-testid="stMarkdownContainer"]:has(.cal-marker) + div[data-testid="stPopover"] > div > button:hover,
      div[data-testid="stMarkdownContainer"]:has(.filters-marker) + div[data-testid="stPopover"] > div > button:hover {{
        background: var(--blue-fill) !important;
      }}

      /* Make ONLY the calendar icon blue */
      div[data-testid="stMarkdownContainer"]:has(.cal-marker) + div[data-testid="stPopover"] [data-testid="stIcon"] svg {{
        color: {BLUE} !important;
        fill:  {BLUE} !important;
      }}

      /* Remove extra right gap so Filters hugs the right edge */
      div[data-testid="stMarkdownContainer"]:has(.filters-marker) + div[data-testid="stPopover"] > div > button {{
        margin-right: 0 !important;
      }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def inject_journal_css() -> None:
    """
    Visual polish for the Journal page table + summary.
    Works whether Streamlit renders as stDataFrame or stDataEditor.
    (Value-based coloring like PnL sign / Long-Short will be added via Styler in journal.py.)
    """
    st.markdown(
        """
        <style>
        /* === Table container (rounded corners + subtle border) === */
        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"] {
            border-radius: 14px !important;
            overflow: hidden !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
        }

        /* === Header row contrast === */
        [data-testid="stDataFrame"] thead tr,
        [data-testid="stDataEditor"] thead tr {
            background: rgba(255,255,255,0.03) !important;
        }
        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stDataEditor"] [role="columnheader"] {
            font-weight: 700 !important;
            border-bottom: 1px solid rgba(255,255,255,0.10) !important;
        }

        /* === Row striping + hover (very subtle) === */
        [data-testid="stDataFrame"] [role="rowgroup"] [role="row"]:nth-child(odd),
        [data-testid="stDataEditor"] [role="rowgroup"] [role="row"]:nth-child(odd) {
            background: rgba(255,255,255,0.015) !important;
        }
        [data-testid="stDataFrame"] [role="rowgroup"] [role="row"]:hover,
        [data-testid="stDataEditor"] [role="rowgroup"] [role="row"]:hover {
            background: rgba(255,255,255,0.045) !important;
            transition: background 120ms ease;
        }

        /* === Cell comfort === */
        [data-testid="stDataFrame"] [role="gridcell"],
        [data-testid="stDataEditor"] [role="gridcell"] {
            padding-top: 6px !important;
            padding-bottom: 6px !important;
            font-weight: 500 !important;
        }

        /* === BaseWeb Tag (used by ListColumn) — keep neutral for now === */
        [data-testid="stDataFrame"] [data-baseweb="tag"],
        [data-testid="stDataEditor"] [data-baseweb="tag"] {
            border-radius: 10px !important;
            background: rgba(148,163,184,0.18) !important; /* slate tint */
            color: #e5e7eb !important;
            border: 1px solid rgba(148,163,184,0.28) !important;
        }

        /* === Summary metrics row: card-like appearance === */
        .stMetric {
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 12px !important;
            padding: 12px 14px !important;
        }
        .stMetric > div { gap: 2px !important; }

        /* === Divider helper (use via st.markdown('<div class="journal-divider"></div>')) === */
        .journal-divider {
            height: 1px;
            background: linear-gradient(
                to right,
                rgba(255,255,255,0),
                rgba(255,255,255,0.10),
                rgba(255,255,255,0)
            );
            margin: 10px 0 16px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
