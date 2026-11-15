"""Crop Yield Explorer - Streamlit entry point (Group 65).

Every visitor must sign in first. The gate in accounts.gate() stops the script until a verified session exists;
nothing below it runs for unauthenticated visitors.

Run locally:  streamlit run app.py   (requires .streamlit/secrets.toml, see README)
"""
import streamlit as st

from crop_yield_explorer import accounts, config, store, ui
from crop_yield_explorer.views import (about, correlation, crops, dataset_manager, explore, login, overview,
                                       profile, settings, smart)

st.set_page_config(page_title=config.APP_TITLE, page_icon=None, layout="wide", initial_sidebar_state="auto")
ui.inject_css()

sess = accounts.gate(login.render_login, login.render_recovery, login.render_unconfigured)   # stops here unless signed in
be = accounts.get_backend()
user = sess.user
st.session_state["_card_n"] = 0
user_store = store.get_store(be, sess)
st.session_state["_ctx"] = {"user": user, "sess": sess, "be": be, "store": user_store}
if "prefs" not in st.session_state:
    st.session_state["prefs"] = user_store.get_prefs()
    ui.notify("info", f"Signed in as {user.email}.")
ui.init_state()
notice = st.session_state.pop("auth_notice", None)
if notice:
    (st.success if notice[0] == "success" else st.info)(notice[1])

PAGES = {
    "Overview": overview.render,
    "Explore Data": explore.render,
    "Crop Analysis": crops.render,
    "Correlation Insights": correlation.render,
    "Dataset Manager": dataset_manager.render,
    "Smart Insights": smart.render,
    "My Profile": profile.render,
    "Settings": settings.render,
}

ui.brand()
page = st.sidebar.radio("Navigation", list(PAGES), format_func=ui.NAV.get, key="page", label_visibility="collapsed")
ui.sidebar_dataset_chip()
df = st.session_state["result"].df
fdf, crit, active = ui.sidebar_filters(df)
ui.sidebar_user(user, accounts.sign_out)
ui.topbar(user, accounts.sign_out)
PAGES[page](df, fdf, active)
