"""Settings page: saved preferences and project information."""
from __future__ import annotations

import streamlit as st

from .. import store, ui
from . import about


def render(df, fdf, active):
    c = ui.ctx()
    ui.page_header("Settings", "Preferences", "Each setting changes how the application behaves for you. Settings are saved to your account.")
    cur = {k: ui.pref(k) for k in store.DEFAULT_PREFS}
    with ui.card():
        with st.form("prefs"):
            rows = st.selectbox("Rows shown in data previews", store.PREF_CHOICES["preview_rows"], index=store.PREF_CHOICES["preview_rows"].index(cur["preview_rows"]))
            dens = st.radio("Chart size", store.PREF_CHOICES["chart_density"], index=store.PREF_CHOICES["chart_density"].index(cur["chart_density"]), horizontal=True,
                            help="Compact charts show more on screen; Tall charts give more room to read.")
            interp = st.toggle("Show written interpretations under charts", value=cur["show_interpretations"])
            meth = st.radio("Default correlation method", store.PREF_CHOICES["correlation_method"], index=store.PREF_CHOICES["correlation_method"].index(cur["correlation_method"]), horizontal=True)
            save = st.form_submit_button("Save settings", type="primary")
        if save:
            new = store.clean_prefs({"preview_rows": rows, "chart_density": dens, "show_interpretations": interp, "correlation_method": meth})
            try:
                c["store"].save_prefs(new)
            except store.StoreError as e:
                st.error(str(e))
            else:
                st.session_state["prefs"] = new
                ui.notify("success", "Settings saved.")
                st.rerun()
        if c["store"].persistent:
            st.caption("Saved to your account and restored the next time you sign in.")
        else:
            st.caption("Persistent storage is not set up for this deployment, so settings last only for this session.")
    ui.section("About this project")
    about.render(df, fdf, active, embedded=True)
