"""Shared Streamlit interface layer: design system, components, state and sidebar controls."""
from __future__ import annotations

import html
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from . import config, data, filters

# --------------------------------------------------------------------------
# Design system
# --------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
:root {
  --forest:#163B2D; --evergreen:#102B22; --green:#287A52; --sage:#DCE9DF; --ivory:#F8F7F1; --white:#FFFFFF;
  --ink:#202923; --muted:#7C887F; --lime:#B9D977; --line:#E3E7DF; --amber:#C99A2E;
  --shadow:0 1px 2px rgba(16,43,34,.05), 0 2px 8px rgba(16,43,34,.04);
}
html, body, [class*="css"], .stApp, button, input, textarea, select { font-family:'Manrope','Inter','Segoe UI',Arial,sans-serif !important; }
.stApp { background: var(--ivory); color: var(--ink); }
header[data-testid="stHeader"] { background: transparent; }
footer, #MainMenu { visibility: hidden; }
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1320px; }
h1,h2,h3,h4 { color: var(--ink); letter-spacing:-0.015em; }
p, li { line-height:1.6; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { border-right:1px solid rgba(255,255,255,.06); }
section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }
.brand { display:flex; align-items:center; gap:.7rem; padding:.2rem .2rem 1rem .2rem; }
.brand .mark { width:38px; height:38px; border-radius:9px; background:var(--green); display:flex; align-items:center; justify-content:center; flex:0 0 auto; }
.brand .name { color:#fff; font-weight:800; letter-spacing:.06em; font-size:.92rem; line-height:1.1; }
.brand .tag { color:#9DB5A6; font-size:.68rem; letter-spacing:.05em; text-transform:uppercase; margin-top:.15rem; }
.side-label { color:#9DB5A6; font-size:.68rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; margin:1.1rem 0 .35rem 0; }
.side-chip { background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.08); border-radius:8px; padding:.6rem .7rem; font-size:.8rem; color:#E6EFE8; margin:.2rem 0 .4rem 0; line-height:1.45; }
.side-chip b { color:#fff; }
.dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--lime); margin-right:.4rem; box-shadow:0 0 0 3px rgba(185,217,119,.18); }
.dot.warn { background:var(--amber); box-shadow:0 0 0 3px rgba(201,154,46,.2); }
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap:.15rem; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"] { padding:.55rem .75rem; border-radius:8px; border-left:3px solid transparent;
  transition: background .15s ease, border-color .15s ease; cursor:pointer; width:100%; min-height:44px; align-items:center; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background:rgba(255,255,255,.07); }
section[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) { background:rgba(185,217,119,.14); border-left-color:var(--lime); }
section[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child { display:none; }
section[data-testid="stSidebar"] [data-testid="stRadioOption"] p { font-weight:600; font-size:.93rem; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.1); margin:1rem 0; }
section[data-testid="stSidebar"] .stButton button { background:transparent; border:1px solid rgba(255,255,255,.25); color:#fff; font-weight:600; min-height:42px; }
section[data-testid="stSidebar"] .stButton button:hover { border-color:var(--lime); color:var(--lime); }
section[data-testid="stSidebar"] [data-testid="stExpander"] { border:1px solid rgba(255,255,255,.1); border-radius:8px; background:rgba(255,255,255,.03); }

/* ---------- page header ---------- */
.page-head { display:flex; justify-content:space-between; align-items:flex-end; gap:1.2rem; flex-wrap:wrap; margin-bottom:1.3rem; padding-bottom:1.1rem; border-bottom:1px solid var(--line); }
.page-head .eyebrow { color:var(--green); font-size:.72rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; margin-bottom:.35rem; }
.page-head h1 { font-size:2rem !important; font-weight:800; margin:0; line-height:1.15; }
.page-head .sub { color:#56635B; font-size:1rem; margin:.4rem 0 0 0; max-width:640px; }
.status { display:flex; flex-direction:column; gap:.2rem; background:#fff; border:1px solid var(--line); border-radius:10px; padding:.65rem .9rem; box-shadow:var(--shadow); font-size:.8rem; color:#56635B; min-width:230px; }
.status .s1 { color:var(--ink); font-weight:700; font-size:.86rem; }
.pill { display:inline-block; font-size:.68rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; padding:.12rem .5rem; border-radius:4px; vertical-align:middle; }
.pill.syn { background:#FBF3DD; color:#7A5A14; border:1px solid #EBD79C; }
.pill.ok { background:#E4F0E7; color:#1E5C3E; border:1px solid #BCD8C5; }

/* ---------- KPI grid ---------- */
.kpi-grid { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:.9rem; margin:.2rem 0 1.4rem 0; }
.kpi { background:#fff; border:1px solid var(--line); border-radius:10px; padding:1rem 1.05rem; box-shadow:var(--shadow);
  transition: box-shadow .18s ease, transform .18s ease, border-color .18s ease; }
.kpi:hover { box-shadow:0 6px 18px rgba(16,43,34,.09); transform:translateY(-1px); border-color:#CFD9CF; }
.kpi .top { display:flex; justify-content:space-between; align-items:center; margin-bottom:.55rem; }
.kpi .k-label { font-size:.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; font-weight:700; }
.kpi .ic { width:32px; height:32px; border-radius:8px; background:var(--sage); display:flex; align-items:center; justify-content:center; }
.kpi .k-value { font-size:1.75rem; font-weight:800; color:var(--forest); line-height:1.1; letter-spacing:-0.02em; }
.kpi .k-unit { font-size:.85rem; font-weight:600; color:var(--muted); margin-left:.25rem; letter-spacing:0; }
.kpi .k-note { font-size:.78rem; color:#56635B; margin-top:.4rem; }
.mini-grid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:.8rem; margin:.4rem 0 1.1rem 0; }
.mini-grid .kpi .k-value { font-size:1.4rem; }

/* ---------- cards, notes, sections ---------- */
[class*="st-key-card_"] { background:#fff !important; border:1px solid var(--line) !important; border-radius:10px !important; box-shadow:var(--shadow); padding:.4rem .5rem; transition: box-shadow .18s ease; }
[class*="st-key-card_"]:hover { box-shadow:0 6px 18px rgba(16,43,34,.08); }
.stAppDeployButton { display:none !important; }
.sec { margin:1.7rem 0 .7rem 0; }
.sec h2 { font-size:1.15rem !important; font-weight:800; margin:0; border:0; padding:0; }
.sec p { color:#56635B; font-size:.9rem; margin:.2rem 0 0 0; }
.note { background:var(--sage); border-left:4px solid var(--green); border-radius:6px; padding:.7rem .9rem; font-size:.9rem; margin:.4rem 0 1rem 0; color:#1D3A2C; }
.caution { background:#FBF3DD; border-left:4px solid var(--amber); border-radius:6px; padding:.7rem .9rem; font-size:.9rem; margin:.4rem 0 1rem 0; color:#5E4710; }
.interp { font-size:.88rem; color:#3A4740; margin:.1rem 0 .3rem 0; padding:.55rem .75rem; background:#F5F7F2; border-radius:6px; }
.interp b { color:var(--forest); }
.empty { text-align:center; background:#fff; border:1px dashed #BFCBC2; border-radius:10px; padding:2.4rem 1.2rem; margin:1rem 0; }
.empty .t { font-weight:800; font-size:1.05rem; color:var(--forest); }
.empty .d { color:#56635B; font-size:.92rem; margin-top:.3rem; }
.fact { background:#fff; border:1px solid var(--line); border-radius:10px; padding:1rem 1.1rem; height:100%; box-shadow:var(--shadow); }
.fact .h { font-weight:800; color:var(--forest); font-size:.95rem; margin-bottom:.3rem; }
.fact .b { font-size:.88rem; color:#46544B; }
.chips { display:flex; flex-wrap:wrap; gap:.4rem; margin:.3rem 0 .9rem 0; }
.chip { font-size:.76rem; font-weight:600; background:#fff; border:1px solid var(--line); color:#3A4740; border-radius:999px; padding:.18rem .65rem; }

/* ---------- widgets ---------- */
section[data-testid="stSidebar"] [data-baseweb="tag"] { height:24px; font-size:.74rem; }
.stTabs [data-baseweb="tab-list"] { gap:.3rem; border-bottom:1px solid var(--line); overflow-x:auto; }
.stTabs [data-baseweb="tab"] { font-weight:700; font-size:.9rem; padding:.55rem .9rem; min-height:44px; }
.stTabs [aria-selected="true"] { color:var(--green); }
.stButton button, .stDownloadButton button { border-radius:8px; font-weight:700; min-height:44px; transition: box-shadow .15s ease, transform .15s ease; }
.stButton button:hover, .stDownloadButton button:hover { box-shadow:0 4px 12px rgba(16,43,34,.14); transform:translateY(-1px); }
[data-testid="stFileUploaderDropzone"] { border:2px dashed #9FB8A8; background:#F5F8F4; border-radius:12px; padding:1.6rem; transition: background .15s ease, border-color .15s ease; }
[data-testid="stFileUploaderDropzone"]:hover { background:#EAF2EC; border-color:var(--green); }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:8px; overflow:hidden; }
[data-testid="stPlotlyChart"] { width:100%; }

/* ---------- responsive ---------- */
@media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(3, minmax(0,1fr)); } .mini-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } }
@media (max-width: 768px) {
  .block-container { padding: 1.2rem .9rem 3rem .9rem; }
  .page-head h1 { font-size:1.55rem !important; }
  .status { width:100%; min-width:0; }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0,1fr)); gap:.6rem; }
  .kpi { padding:.8rem .8rem; } .kpi .k-value { font-size:1.35rem; }
}
@media (max-width: 420px) { .kpi-grid { grid-template-columns: 1fr 1fr; } .kpi .k-label { font-size:.66rem; } }
</style>
"""

_I = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#287A52" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{}</svg>'
ICONS = {
    "records": _I.format('<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>'),
    "production": _I.format('<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>'),
    "yield": _I.format('<path d="M11 20A7 7 0 0 1 4 13c0-5 4-9 16-9 0 12-4 16-9 16z"/><path d="M4 21c2-6 5-9 9-11"/>'),
    "peak": _I.format('<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>'),
    "crops": _I.format('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'),
    "regions": _I.format('<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>'),
    "area": _I.format('<path d="M3 3h18v18H3z"/><path d="M3 9h18M9 3v18"/>'),
}
LOGO = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 4 13c0-5 4-9 16-9 0 12-4 16-9 16z"/><path d="M4 21c2-6 5-9 9-11"/></svg>')

NAV = {
    "Overview": ":material/dashboard: Overview",
    "Explore Data": ":material/table_view: Explore Data",
    "Crop Analysis": ":material/eco: Crop Analysis",
    "Relationships": ":material/scatter_plot: Relationships",
    "Dataset Manager": ":material/upload_file: Dataset Manager",
    "About Project": ":material/info: About Project",
}


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x) -> str:
    return html.escape(str(x))


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------
def brand() -> None:
    st.sidebar.markdown(
        f'<div class="brand"><div class="mark">{LOGO}</div><div><div class="name">CROP YIELD<br>EXPLORER</div>'
        '<div class="tag">Agricultural data analytics</div></div></div>',
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, subtitle: str) -> None:
    synthetic = st.session_state.get("synthetic", False)
    res = st.session_state.get("result")
    loaded = st.session_state.get("loaded_at", "")
    n = len(res.df) if res is not None else 0
    pill = '<span class="pill syn">Synthetic sample</span>' if synthetic else '<span class="pill ok">User dataset</span>'
    st.markdown(
        f'<div class="page-head"><div><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1>'
        f'<p class="sub">{esc(subtitle)}</p></div>'
        f'<div class="status"><div class="s1"><span class="dot"></span>Dataset ready {pill}</div>'
        f'<div>{esc(st.session_state.get("source_name", ""))}</div>'
        f'<div>{n:,} records loaded{(" · loaded at " + esc(loaded)) if loaded else ""}</div></div></div>',
        unsafe_allow_html=True,
    )


def kpi_grid(items: list[tuple], css_class: str = "kpi-grid") -> None:
    """items: (icon_key, label, value, unit, note). Rendered as one responsive HTML grid."""
    cells = []
    for icon, label, value, unit, note in items:
        u = f'<span class="k-unit">{esc(unit)}</span>' if unit else ""
        cells.append(
            f'<div class="kpi"><div class="top"><div class="k-label">{esc(label)}</div><div class="ic">{ICONS[icon]}</div></div>'
            f'<div class="k-value">{esc(value)}{u}</div><div class="k-note">{esc(note) if note else "&nbsp;"}</div></div>'
        )
    st.markdown(f'<div class="{css_class}">{"".join(cells)}</div>', unsafe_allow_html=True)


def section(title: str, desc: str = "") -> None:
    d = f"<p>{esc(desc)}</p>" if desc else ""
    st.markdown(f'<div class="sec"><h2>{esc(title)}</h2>{d}</div>', unsafe_allow_html=True)


def note(text: str, kind: str = "note") -> None:
    st.markdown(f'<div class="{kind}">{text}</div>', unsafe_allow_html=True)


def interp(text: str) -> None:
    if text:
        h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        st.markdown(f'<div class="interp"><b>Reading this chart.</b> {h}</div>', unsafe_allow_html=True)


def empty_state(title: str, text: str) -> None:
    st.markdown(f'<div class="empty"><div class="t">{esc(title)}</div><div class="d">{esc(text)}</div></div>', unsafe_allow_html=True)


def fact(col, heading: str, body: str) -> None:
    col.markdown(f'<div class="fact"><div class="h">{esc(heading)}</div><div class="b">{body}</div></div>', unsafe_allow_html=True)


def chips(items: list[str]) -> None:
    if items:
        st.markdown('<div class="chips">' + "".join(f'<span class="chip">{esc(i)}</span>' for i in items) + "</div>", unsafe_allow_html=True)


def card():
    """A bordered white card. Keys are unique per run so the CSS can target every card."""
    st.session_state["_card_n"] = st.session_state.get("_card_n", 0) + 1
    return st.container(border=True, key=f"card_{st.session_state['_card_n']}")


def plot(fig, key: str) -> None:
    st.plotly_chart(fig, width="stretch", key=key,
                    config={"displaylogo": False, "displayModeBar": "hover",
                            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]})


def fmt_num(x, decimals: int = 2, unit: str = "") -> str:
    if x is None or pd.isna(x):
        return "n/a"
    s = f"{x:,.{decimals}f}"
    return f"{s} {unit}".strip()


def active_filters_chips(active: list[str]) -> None:
    chips(active if active else ["No filters applied"])


# --------------------------------------------------------------------------
# State and data source
# --------------------------------------------------------------------------
def _set_result(res: data.LoadResult, name: str, synthetic: bool) -> None:
    st.session_state["result"] = res
    st.session_state["source_name"] = name
    st.session_state["synthetic"] = synthetic
    st.session_state["loaded_at"] = datetime.now().strftime("%H:%M")
    st.session_state["ds_version"] = st.session_state.get("ds_version", 0) + 1


def init_state() -> None:
    if "result" not in st.session_state:
        _set_result(data.load_sample(), config.SAMPLE_NAME, True)


def _on_source_change() -> None:
    if st.session_state.get("source_choice", "").startswith("Sample"):
        _set_result(data.load_sample(), config.SAMPLE_NAME, True)


def dataset_source_controls() -> None:
    """Dataset Manager: choose the sample dataset or upload a CSV file (state survives page changes)."""
    if "source_choice" not in st.session_state:
        st.session_state["source_choice"] = "Sample dataset (synthetic)" if st.session_state.get("synthetic") else "Upload my own CSV"
    choice = st.radio("Data source", ["Sample dataset (synthetic)", "Upload my own CSV"], key="source_choice",
                      horizontal=True, on_change=_on_source_change)
    if choice.startswith("Sample"):
        return
    up = st.file_uploader("Drag and drop a CSV file here, or browse", type=["csv", "txt"], key="uploader",
                          help=f"Maximum {config.MAX_UPLOAD_MB} MB. Required columns: crop and yield.")
    if up is None:
        if st.session_state.get("synthetic") is True:
            st.caption("No file chosen yet. The synthetic sample stays loaded until a valid file is uploaded.")
        else:
            st.caption(f"Currently loaded: {st.session_state.get('source_name')}. Choose another file to replace it.")
        return
    sig = (up.name, up.size)
    if st.session_state.get("upload_sig") != sig:
        with st.spinner("Validating and cleaning the file..."):
            res = data.load_csv_bytes(up.getvalue())
        st.session_state["upload_sig"] = sig
        st.session_state["upload_result"] = res
        if res.ok:
            _set_result(res, up.name, False)
            st.rerun()  # refresh the header, sidebar filters and every page with the new dataset
    res = st.session_state["upload_result"]
    if not res.ok:
        st.error("The uploaded file could not be loaded.")
        for e in res.errors:
            st.markdown(f"- {e}")
        st.warning("The previously loaded dataset is still in use.")
    else:
        st.success(f"Loaded {res.rows_kept:,} of {res.rows_read:,} rows from {up.name}.")


def sidebar_dataset_chip() -> None:
    res = st.session_state["result"]
    kind = "Synthetic sample" if st.session_state.get("synthetic") else "Your upload"
    st.sidebar.markdown(
        f'<div class="side-chip"><span class="dot"></span><b>{kind}</b><br>{esc(st.session_state["source_name"])}<br>'
        f'{len(res.df):,} records</div>', unsafe_allow_html=True)


def sidebar_filters(df: pd.DataFrame):
    """Render filters and return (filtered_df, criteria, active_descriptions)."""
    st.sidebar.markdown('<div class="side-label">Filters</div>', unsafe_allow_html=True)
    cats: dict[str, list] = {}
    ranges: dict[str, tuple[float, float]] = {}
    full: dict[str, tuple[float, float]] = {}
    ver = f'{st.session_state.get("filter_version", 0)}_{st.session_state.get("ds_version", 0)}'

    for col in filters.CATEGORY_FILTERS:
        if col in df.columns and df[col].notna().any():
            opts = sorted(df[col].dropna().unique().tolist())
            cats[col] = st.sidebar.multiselect(config.label(col, False), opts, default=opts, key=f"f_{col}_{ver}")

    with st.sidebar.expander("Numeric ranges", expanded=False):
        for col in filters.NUMERIC_FILTERS:
            if col not in df.columns:
                continue
            b = filters.range_bounds(df[col], is_year=(col == "year"))
            if b is None:
                continue
            lo, hi, step = b
            full[col] = (lo, hi)
            ranges[col] = st.slider(config.label(col), min_value=lo, max_value=hi, value=(lo, hi), step=step, key=f"f_{col}_{ver}")

    if st.sidebar.button("Reset all filters", width="stretch"):
        st.session_state["filter_version"] = st.session_state.get("filter_version", 0) + 1
        st.rerun()

    crit = filters.Criteria(categories=cats, ranges=ranges)
    fdf = filters.apply_filters(df, crit, full)
    active = filters.describe_active(crit, df, full)
    st.sidebar.caption(f"Showing {len(fdf):,} of {len(df):,} records")
    return fdf, crit, active


def require_records(fdf: pd.DataFrame, minimum: int = 1) -> bool:
    """Show a friendly empty state when filters remove all (or too many) records."""
    if len(fdf) < minimum:
        if len(fdf) == 0:
            empty_state("No records match the current filters", "Widen the selection in the sidebar or press Reset all filters.")
        else:
            empty_state(f"Only {len(fdf)} record(s) match", f"At least {minimum} records are needed here. Widen the filters in the sidebar.")
        return False
    return True
