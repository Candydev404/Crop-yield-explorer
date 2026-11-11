"""Shared Streamlit interface helpers: styling, state, sidebar and formatting."""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from . import config, data, filters

CSS = """
<style>
:root { --green:#2F6B3A; --green-dark:#1F4A28; --wheat:#B7862B; --ink:#1F2A24; --muted:#5B6670; --line:#D9DED3; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1280px; }
h1, h2, h3, h4 { color: var(--ink); letter-spacing: -0.01em; }
h1 { font-size: 1.9rem !important; font-weight: 700; margin-bottom: .1rem; }
h2 { font-size: 1.3rem !important; font-weight: 650; border-bottom: 1px solid var(--line); padding-bottom: .35rem; margin-top: 1.6rem; }
h3 { font-size: 1.05rem !important; font-weight: 650; }
.app-header { border-left: 5px solid var(--green); padding: .1rem 0 .1rem .9rem; margin-bottom: 1rem; }
.app-header .sub { color: var(--muted); font-size: 1rem; margin: 0; }
.badge { display:inline-block; font-size:.75rem; padding:.12rem .55rem; border:1px solid var(--wheat); color:#7A5A14;
         background:#FBF5E6; border-radius:3px; margin-left:.4rem; vertical-align:middle; font-weight:600; }
.kpi { background:#fff; border:1px solid var(--line); border-top:3px solid var(--green); border-radius:4px; padding:.75rem .9rem; height:100%; }
.kpi .k-label { font-size:.78rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; font-weight:600; }
.kpi .k-value { font-size:1.55rem; font-weight:700; color:var(--ink); line-height:1.25; }
.kpi .k-note { font-size:.78rem; color:var(--muted); }
.note { background:#F3F6EE; border:1px solid var(--line); border-left:4px solid var(--green); border-radius:3px; padding:.65rem .85rem; font-size:.93rem; margin:.4rem 0 1rem 0; }
.caution { background:#FBF5E6; border:1px solid #E6D3A3; border-left:4px solid var(--wheat); border-radius:3px; padding:.65rem .85rem; font-size:.93rem; margin:.4rem 0 1rem 0; }
.interp { font-size:.92rem; color:#2E3A33; margin:-.2rem 0 1.2rem 0; }
.interp b { color: var(--green-dark); }
section[data-testid="stSidebar"] { border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
div[data-testid="stSidebar"] h2 { font-size: .85rem !important; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); border: 0; margin-top: 1rem; padding: 0; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
@media (max-width: 768px) { h1 { font-size: 1.5rem !important; } .kpi .k-value { font-size: 1.3rem; } }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header(title: str, subtitle: str, synthetic: bool = False) -> None:
    badge = '<span class="badge">SYNTHETIC SAMPLE DATA</span>' if synthetic else ""
    st.markdown(
        f'<div class="app-header"><h1>{title}{badge}</h1><p class="sub">{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def kpi(col, label: str, value: str, note: str = "") -> None:
    col.markdown(
        f'<div class="kpi"><div class="k-label">{label}</div><div class="k-value">{value}</div>'
        f'<div class="k-note">{note or "&nbsp;"}</div></div>',
        unsafe_allow_html=True,
    )


def note(text: str, kind: str = "note") -> None:
    st.markdown(f'<div class="{kind}">{text}</div>', unsafe_allow_html=True)


def interp(text: str) -> None:
    if text:
        html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        st.markdown(f'<div class="interp"><b>Interpretation.</b> {html}</div>', unsafe_allow_html=True)


def fmt_num(x, decimals: int = 2, unit: str = "") -> str:
    if x is None or pd.isna(x):
        return "n/a"
    s = f"{x:,.{decimals}f}"
    return f"{s} {unit}".strip()


# --------------------------------------------------------------------------
# State and data source
# --------------------------------------------------------------------------
def _set_result(res: data.LoadResult, name: str, synthetic: bool) -> None:
    st.session_state["result"] = res
    st.session_state["source_name"] = name
    st.session_state["synthetic"] = synthetic


def init_state() -> None:
    if "result" not in st.session_state:
        _set_result(data.load_sample(), config.SAMPLE_NAME, True)


def data_source_controls() -> None:
    """Sidebar: choose the sample dataset or upload a CSV file."""
    st.sidebar.markdown("## Data source")
    choice = st.sidebar.radio(
        "Dataset", ["Sample dataset (synthetic)", "Upload my own CSV"],
        key="source_choice", label_visibility="collapsed",
    )
    if choice.startswith("Sample"):
        if st.session_state.get("synthetic") is not True:
            _set_result(data.load_sample(), config.SAMPLE_NAME, True)
        return
    up = st.sidebar.file_uploader("CSV file", type=["csv", "txt"], key="uploader",
                                  help=f"Maximum {config.MAX_UPLOAD_MB} MB. Required columns: crop and yield.")
    if up is None:
        # No file yet: keep the previous valid upload if any, otherwise keep the sample loaded.
        if st.session_state.get("synthetic") is True:
            st.sidebar.info("Choose a CSV file to analyse. The sample data remains loaded until then.")
        return
    sig = (up.name, up.size)
    if st.session_state.get("upload_sig") != sig:
        res = data.load_csv_bytes(up.getvalue())
        st.session_state["upload_sig"] = sig
        st.session_state["upload_result"] = res
        if res.ok:
            _set_result(res, up.name, False)
    res = st.session_state["upload_result"]
    if not res.ok:
        for e in res.errors:
            st.sidebar.error(e)
        st.sidebar.warning("The file was not loaded. The previously loaded dataset is still in use.")
    else:
        st.sidebar.success(f"Loaded {res.rows_kept:,} records from {up.name}.")


def sidebar_filters(df: pd.DataFrame):
    """Render filters and return (filtered_df, criteria, active_descriptions)."""
    st.sidebar.markdown("## Filters")
    cats: dict[str, list] = {}
    ranges: dict[str, tuple[float, float]] = {}
    full: dict[str, tuple[float, float]] = {}
    ver = st.session_state.get("filter_version", 0)

    for col in filters.CATEGORY_FILTERS:
        if col in df.columns and df[col].notna().any():
            opts = sorted(df[col].dropna().unique().tolist())
            cats[col] = st.sidebar.multiselect(config.label(col, False), opts, default=opts, key=f"f_{col}_{ver}")

    for col in filters.NUMERIC_FILTERS:
        if col not in df.columns:
            continue
        b = filters.range_bounds(df[col], is_year=(col == "year"))
        if b is None:
            continue
        lo, hi, step = b
        full[col] = (lo, hi)
        ranges[col] = st.sidebar.slider(config.label(col), min_value=lo, max_value=hi, value=(lo, hi),
                                        step=step, key=f"f_{col}_{ver}")

    if st.sidebar.button("Reset all filters", width="stretch"):
        st.session_state["filter_version"] = ver + 1
        st.rerun()

    crit = filters.Criteria(categories=cats, ranges=ranges)
    fdf = filters.apply_filters(df, crit, full)
    active = filters.describe_active(crit, df, full)
    st.sidebar.caption(f"Showing {len(fdf):,} of {len(df):,} records.")
    return fdf, crit, active


def require_records(fdf: pd.DataFrame, minimum: int = 1) -> bool:
    """Show a friendly message when filters remove all (or too many) records."""
    if len(fdf) < minimum:
        st.warning(
            "No records match the current filters." if len(fdf) == 0
            else f"Only {len(fdf)} record(s) match the current filters; at least {minimum} are needed here."
        )
        st.caption("Widen the filters in the sidebar or press 'Reset all filters'.")
        return False
    return True
