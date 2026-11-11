"""Simple Crop Yield Data Explorer - Streamlit entry point (Group 65).

Run locally:  streamlit run app.py
"""
import streamlit as st

from crop_yield_explorer import config, ui
from crop_yield_explorer.views import charts_page, dashboard, data_page, guide_page, stats_page

st.set_page_config(page_title=config.APP_TITLE, page_icon=None, layout="wide", initial_sidebar_state="auto")
ui.inject_css()
ui.init_state()

PAGES = {
    "Dashboard": dashboard.render,
    "Data": data_page.render,
    "Charts": charts_page.render,
    "Statistics": stats_page.render,
    "Guide": guide_page.render,
}

st.sidebar.markdown("### Crop Yield Explorer")
page = st.sidebar.radio("Navigation", list(PAGES), key="page", label_visibility="collapsed")
ui.data_source_controls()

result = st.session_state["result"]
df = result.df
fdf, crit, active = ui.sidebar_filters(df)
PAGES[page](df, fdf, active, st.session_state["synthetic"], st.session_state["source_name"])
