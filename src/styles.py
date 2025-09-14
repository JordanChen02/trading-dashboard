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


def inject_topbar_css(brand_color: str = BLUE, hover_fill: str = BLUE_FILL) -> None:
    brand_enc = brand_color.replace("#", "%23")  # URL-encode for inline SVG

    st.markdown(
        f"""
    <style>
    :root {{ --brand:{brand_color}; --blue-fill:{hover_fill}; }}

    /* Generic icon button (no border/outline) */
    .icon-btn button {{
      background: transparent !important;
      border: 0 !important;
      color: #d5deed !important;
      padding: 6px 10px !important;
      border-radius: 10px !important;
      font-weight: 600;
      min-width: 40px;
      height: 40px;
    }}
    .icon-btn button:hover {{ background: var(--blue-fill) !important; }}
    .icon-btn button:focus {{ box-shadow:none !important; outline:none !important; }}

    /* Render the icon via a background-image on the button itself */
    .icon-btn button::before {{
      content: "";
      width: 18px; height: 18px; display: inline-block;
      margin: 0; vertical-align: middle;
      background-repeat: no-repeat; background-position: center; background-size: contain;
    }}

    /* Globe */
    .icon-btn.globe button::before {{
      background-image: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='{brand_enc}' d='M12 2a10 10 0 1 0 0 20a10 10 0 0 0 0-20m-1 2.05v3.1a7.98 7.98 0 0 0-5.46 3.83H4.06A8.03 8.03 0 0 1 11 4.05M4.06 11h1.48A7.98 7.98 0 0 0 11 14.85v3.1A8.03 8.03 0 0 1 4.06 11m9.94 6.95v-3.1A7.98 7.98 0 0 0 18.46 11h1.48A8.03 8.03 0 0 1 14 17.95M18.46 10A7.98 7.98 0 0 0 14 6.15V4.05A8.03 8.03 0 0 1 19.94 10Z'/>\
      </svg>");
    }}

    /* Bell */
    .icon-btn.bell button::before {{
      background-image: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='{brand_enc}' d='M12 22a2 2 0 0 0 2-2H10a2 2 0 0 0 2 2m6-6v-5a6 6 0 0 0-5-5.91V4a1 1 0 1 0-2 0v1.09A6 6 0 0 0 6 11v5l-2 2v1h16v-1z'/>\
      </svg>");
    }}

    /* Fullscreen */
    .icon-btn.fullscreen button::before {{
      background-image: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='{brand_enc}' d='M7 14H5v5h5v-2H7v-3m0-4h3V5H5v5h2m10 7h-3v2h5v-5h-2v3m0-7h2V5h-5v2h3v3Z'/>\
      </svg>");
    }}

    /* Theme (sun icon) */
    .icon-btn.theme button::before {{
      background-image: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='{brand_enc}' d='M12 3a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1m7 8a7 7 0 1 1-7-7a7 7 0 0 1 7 7m1 0a8 8 0 1 0-8 8a8 8 0 0 0 8-8Z'/>\
      </svg>");
    }}

    /* Profile trigger (avatar circle, also borderless) */
    .profile-trigger button {{
      background: transparent !important;
      border: 0 !important;
      color: #d5deed !important;
      padding: 6px 10px !important;
      border-radius: 999px !important;
      width: 40px; height: 40px;
    }}
    .profile-trigger button:hover {{ background: var(--blue-fill) !important; }}
    .profile-trigger button:focus {{ box-shadow:none !important; outline:none !important; }}
    .profile-trigger button::before {{
      content: "";
      width: 18px; height: 18px; display: inline-block;
      background-repeat: no-repeat; background-position: center; background-size: contain;
      background-image: url("data:image/svg+xml;utf8,\
      <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>\
        <path fill='{brand_enc}' d='M12 2a5 5 0 1 1 0 10a5 5 0 0 1 0-10m0 12c-4.42 0-8 2.24-8 5v1h16v-1c0-2.76-3.58-5-8-5Z'/>\
      </svg>");
    }}

    .profile-pop {{ min-width: 360px; }}
    </style>
    """,
        unsafe_allow_html=True,
    )
