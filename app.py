"""Crop Yield Explorer - Streamlit entry point (Group 65).

Run locally:  streamlit run app.py
"""
import streamlit as st

from crop_yield_explorer import config, ui
from crop_yield_explorer.views import about, crops, dataset_manager, explore, overview, relationships

st.set_page_config(page_title=config.APP_TITLE, page_icon=None, layout="wide", initial_sidebar_state="auto")
ui.inject_css()
ui.init_state()
st.session_state["_card_n"] = 0

PAGES = {
    "Overview": overview.render,
    "Explore Data": explore.render,
    "Crop Analysis": crops.render,
    "Relationships": relationships.render,
    "Dataset Manager": dataset_manager.render,
    "About Project": about.render,
}

ui.brand()
page = st.sidebar.radio("Navigation", list(PAGES), format_func=ui.NAV.get, key="page", label_visibility="collapsed")
ui.sidebar_dataset_chip()
df = st.session_state["result"].df
fdf, crit, active = ui.sidebar_filters(df)
PAGES[page](df, fdf, active)
