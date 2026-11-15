"""My Profile page: account details, permitted edits and session management."""
from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

from .. import accounts, ui


def _fmt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M")


def render(df, fdf, active):
    c = ui.ctx()
    user, sess, be = c["user"], c["sess"], c["be"]
    ui.page_header("My Profile", "Your account", "Details come from your sign-in provider. You can edit the permitted fields below.")
    a, b = st.columns([2, 3], gap="medium")
    with a, ui.card():
        st.markdown(f'<div class="acct" style="gap:1rem">{ui.avatar_html(user, 64)}<div><div style="font-weight:800;font-size:1.2rem">{ui.esc(user.name)}</div>'
                    f'<div style="color:#56635B">{ui.esc(user.email)}</div></div></div>', unsafe_allow_html=True)
        st.markdown("---")
        rows = [("Full name", user.name), ("Email address", user.email),
                ("Sign-in method", "Google" if user.provider == "google" else "Email and password"),
                ("Email verified", "Yes" if user.email_confirmed else "Not yet"),
                ("Account created", user.created_at or "Not available")]
        st.dataframe([{"Field": k, "Value": v} for k, v in rows], hide_index=True, width="stretch")
    with b:
        with ui.card():
            st.markdown("**Edit profile**")
            if user.provider == "google":
                st.caption("Your name and photo come from your Google account and are changed there.")
            else:
                with st.form("edit_name"):
                    name = st.text_input("Full name", value=user.name)
                    save = st.form_submit_button("Save changes", type="primary")
                if save:
                    err = accounts.validate_name(name)
                    if err:
                        st.error(err)
                    else:
                        try:
                            with st.spinner("Saving..."):
                                new = be.update_name(sess, name.strip())
                        except accounts.AuthError as e:
                            st.error(str(e))
                        else:
                            st.session_state["auth_session"] = new
                            ui.notify("success", "Profile updated.")
                            st.rerun()
        with ui.card():
            st.markdown("**Password**")
            if user.provider == "google":
                st.caption("You sign in with Google, so there is no password to change here.")
            else:
                with st.form("change_pw", clear_on_submit=True):
                    pw = st.text_input("New password", type="password", autocomplete="new-password")
                    pw2 = st.text_input("Confirm new password", type="password", autocomplete="new-password")
                    go = st.form_submit_button("Change password", type="primary")
                st.caption("At least 10 characters, with an uppercase letter, a lowercase letter and a number.")
                if go:
                    prob = accounts.password_problems(pw)
                    if prob:
                        st.error("Password needs " + ", ".join(prob) + ".")
                    elif pw != pw2:
                        st.error("The two passwords do not match.")
                    else:
                        try:
                            with st.spinner("Updating..."):
                                new = be.update_password(sess, pw)
                        except accounts.AuthError as e:
                            st.error(str(e))
                        else:
                            st.session_state["auth_session"] = new
                            ui.notify("success", "Password changed.")
                            st.success("Your password was changed.")
    ui.section("Session and security")
    left = max(0, int(sess.signed_in_at + accounts.SESSION_MAX_AGE_S - time.time()))
    with ui.card():
        st.dataframe([
            {"Item": "Signed in at", "Detail": _fmt(sess.signed_in_at)},
            {"Item": "Session ends automatically", "Detail": f"in about {left // 3600} h {left % 3600 // 60} min (limit {accounts.SESSION_MAX_AGE_S // 3600} hours)"},
            {"Item": "Access token refreshes", "Detail": "automatically while you are signed in"},
            {"Item": "Passwords", "Detail": "handled by Supabase Auth; this app never stores them"},
        ], hide_index=True, width="stretch")
        c1, c2 = st.columns(2)
        c1.button("Sign out", on_click=accounts.sign_out, key="pf_out", width="stretch")
        c2.button("Sign out on all devices", on_click=accounts.sign_out, kwargs={"everywhere": True}, key="pf_out_all", width="stretch")
