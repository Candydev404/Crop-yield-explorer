"""Authentication screens: split-screen sign in, registration, password reset, recovery and 'not configured'."""
from __future__ import annotations

import time

import streamlit as st

from .. import accounts, config, ui

HERO = """
<svg viewBox="0 0 560 330" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Illustration of crop rows under a low sun">
  <rect width="560" height="330" fill="#0E2A20"/>
  <circle cx="440" cy="92" r="46" fill="#B9D977" opacity=".92"/>
  <circle cx="440" cy="92" r="70" fill="#B9D977" opacity=".10"/>
  <path d="M0 190 C120 150 240 175 340 160 C430 146 500 160 560 150 V330 H0Z" fill="#163B2D"/>
  <path d="M0 232 C110 200 230 222 330 208 C430 194 500 214 560 200 V330 H0Z" fill="#1C4B38"/>
  <path d="M0 276 C120 250 240 270 350 258 C450 248 520 262 560 254 V330 H0Z" fill="#287A52"/>
  <g stroke="#B9D977" stroke-opacity=".28" stroke-width="1.4" fill="none">
    <path d="M30 330 C60 290 100 262 150 238"/><path d="M90 330 C120 292 160 266 210 244"/>
    <path d="M150 330 C180 296 222 270 272 250"/><path d="M210 330 C242 298 284 274 334 256"/>
    <path d="M270 330 C302 300 344 278 394 262"/><path d="M330 330 C362 302 404 282 454 266"/>
    <path d="M390 330 C422 304 462 286 512 272"/>
  </g>
  <g transform="translate(36 34)">
    <rect width="168" height="96" rx="10" fill="#FFFFFF" opacity=".08" stroke="#FFFFFF" stroke-opacity=".18"/>
    <g fill="#B9D977"><rect x="18" y="52" width="14" height="30" rx="2" opacity=".55"/><rect x="40" y="38" width="14" height="44" rx="2" opacity=".7"/>
    <rect x="62" y="26" width="14" height="56" rx="2"/><rect x="84" y="44" width="14" height="38" rx="2" opacity=".7"/><rect x="106" y="32" width="14" height="50" rx="2" opacity=".85"/></g>
    <path d="M18 20 L50 28 L84 14 L120 24 L150 12" stroke="#FFFFFF" stroke-opacity=".7" stroke-width="2" fill="none" stroke-linecap="round"/>
  </g>
</svg>
"""

AUTH_CSS = """
<style>
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display:none !important; }
.block-container { max-width:none !important; padding:0 !important; }
[data-testid="stHorizontalBlock"]:has(.auth-left) { gap:0 !important; align-items:stretch; }
[data-testid="stColumn"]:has(.auth-left) { background:var(--evergreen); }
.auth-left { padding:3.2rem 3.4rem; min-height:100vh; color:#E6EFE8; display:flex; flex-direction:column; justify-content:space-between; gap:1.6rem; }
.auth-left .brand { padding:0; }
.auth-left h2 { color:#fff; font-size:2.5rem; line-height:1.12; font-weight:800; letter-spacing:-.02em; margin:0 0 .9rem 0; }
.auth-left p { color:#B8CBBE; font-size:1.02rem; max-width:480px; }
.auth-left svg { width:100%; height:auto; border-radius:12px; border:1px solid rgba(255,255,255,.08); }
.auth-left .pts { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1rem; }
.auth-left .pts span { font-size:.78rem; font-weight:600; color:#DCE9DF; border:1px solid rgba(255,255,255,.18); padding:.2rem .65rem; border-radius:999px; }
.auth-right { padding:3.4rem 0 1rem 0; }
[data-testid="stColumn"]:has(.auth-right) { padding:0 3.4rem; max-width:100%; }
[data-testid="stColumn"]:has(.auth-right) > div { max-width:520px; margin:0 auto; }
.auth-right h1 { font-size:1.85rem !important; font-weight:800; margin:.2rem 0 .3rem 0; }
.auth-right .lead { color:#56635B; margin-bottom:1.2rem; }
.rules { font-size:.8rem; color:var(--muted); margin:-.2rem 0 .8rem 0; }
.or { text-align:center; color:var(--muted); font-size:.78rem; margin:.9rem 0; letter-spacing:.1em; text-transform:uppercase; }
a.gbtn { display:flex; align-items:center; justify-content:center; gap:.6rem; min-height:46px; border:1px solid #CBD3CC; border-radius:8px; background:#fff;
  color:var(--ink) !important; font-weight:700; text-decoration:none !important; transition: box-shadow .15s ease, border-color .15s ease; }
a.gbtn:hover { border-color:var(--green); box-shadow:0 4px 12px rgba(16,43,34,.12); }
div.gbtn-off { text-align:center; font-size:.82rem; color:var(--muted); border:1px dashed #CBD3CC; border-radius:8px; padding:.7rem; }
@media (max-width: 900px) {
  .auth-left { min-height:auto; padding:1.6rem 1.2rem; } .auth-left h2 { font-size:1.6rem; } .auth-left svg, .auth-left .pts { display:none; }
  .auth-right { padding:1.6rem 0 1rem 0; }
  [data-testid="stColumn"]:has(.auth-right) { padding:0 1.2rem 2rem 1.2rem; }
}
</style>
"""

GOOGLE_G = ('<svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z"/>'
            '<path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z"/>'
            '<path fill="#FBBC05" d="M10.5 28.7a14.5 14.5 0 0 1 0-9.4l-7.9-6.1a24 24 0 0 0 0 21.6l7.9-6.1z"/>'
            '<path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z"/></svg>')


def _left(headline=True) -> None:
    st.markdown(
        f'<div class="auth-left"><div><div class="brand"><div class="mark">{ui.LOGO}</div><div><div class="name">CROP YIELD<br>EXPLORER</div>'
        '<div class="tag">Agricultural data analytics</div></div></div></div>'
        '<div><h2>Understand Your Crops. Discover Your Data.</h2>'
        '<p>Explore agricultural datasets, uncover crop performance patterns and transform raw agricultural records into meaningful insights.</p>'
        '<div class="pts"><span>Interactive charts</span><span>Automatic insights</span><span>Private workspace</span><span>CSV import and export</span></div></div>'
        f'<div>{HERO}</div></div>', unsafe_allow_html=True)


def _shell():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    left, right = st.columns([1.05, 1], gap="small")
    with left:
        _left()
    return right


def _notice() -> None:
    n = st.session_state.pop("auth_notice", None)
    if n:
        {"error": st.error, "info": st.info, "success": st.success}.get(n[0], st.info)(n[1])


def _google(be) -> None:
    sec_ok = False
    try:
        sec_ok = bool(st.secrets["supabase"].get("google_enabled", False))
    except Exception:
        pass
    if sec_ok and hasattr(be, "oauth_url"):
        url = st.session_state.get("oauth_url")
        if not url or time.time() - st.session_state.get("oauth_url_t", 0) > 600:
            url = be.oauth_url("google")
            st.session_state["oauth_url"], st.session_state["oauth_url_t"] = url, time.time()
        st.markdown(f'<a class="gbtn" target="_self" href="{ui.esc(url)}">{GOOGLE_G} Continue with Google</a>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="gbtn-off">Google sign-in is not enabled for this deployment.</div>', unsafe_allow_html=True)


def _finish(sess, message: str) -> None:
    st.session_state["auth_session"] = sess
    st.session_state["auth_notice"] = ("success", message)
    st.session_state["welcome_event"] = True
    st.rerun()


def render_login(be) -> None:
    right = _shell()
    with right:
        st.markdown('<div class="auth-right">', unsafe_allow_html=True)
        _notice()
        tab_in, tab_up, tab_rs = st.tabs(["Sign in", "Create account", "Reset password"])
        with tab_in:
            st.markdown("<h1>Welcome back</h1><div class='lead'>Sign in to open your agricultural intelligence workspace.</div>", unsafe_allow_html=True)
            with st.form("signin", clear_on_submit=True):
                email = st.text_input("Email address", value=st.session_state.get("last_email", ""), autocomplete="email")
                pw = st.text_input("Password", type="password", autocomplete="current-password")
                go = st.form_submit_button("Sign in", type="primary", width="stretch")
            if go:
                st.session_state["last_email"] = email.strip()
                err = accounts.validate_email(email)
                if err or not pw:
                    st.error(err or "Enter your password.")
                else:
                    try:
                        with st.spinner("Signing you in..."):
                            sess = be.sign_in(email.strip(), pw)
                    except accounts.AuthError as e:
                        st.error(str(e))
                    else:
                        _finish(sess, "Signed in successfully.")
            st.markdown('<div class="or">or</div>', unsafe_allow_html=True)
            _google(be)
            st.caption("Forgot your password? Use the Reset password tab. New here? Use Create account.")
        with tab_up:
            st.markdown("<h1>Create your account</h1><div class='lead'>Your datasets and preferences stay in your own private workspace.</div>", unsafe_allow_html=True)
            with st.form("signup", clear_on_submit=True):
                name = st.text_input("Full name", autocomplete="name")
                email = st.text_input("Email address", key="su_email", autocomplete="email")
                pw = st.text_input("Password", type="password", key="su_pw", autocomplete="new-password")
                pw2 = st.text_input("Confirm password", type="password", key="su_pw2", autocomplete="new-password")
                st.markdown('<div class="rules">At least 10 characters, with an uppercase letter, a lowercase letter and a number.</div>', unsafe_allow_html=True)
                go = st.form_submit_button("Create account", type="primary", width="stretch")
            if go:
                errs = [e for e in (accounts.validate_name(name), accounts.validate_email(email)) if e]
                prob = accounts.password_problems(pw)
                if prob:
                    errs.append("Password needs " + ", ".join(prob) + ".")
                if pw != pw2:
                    errs.append("The two passwords do not match.")
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    try:
                        with st.spinner("Creating your account..."):
                            sess, msg = be.sign_up(email.strip(), pw, name.strip())
                    except accounts.AuthError as e:
                        st.error(str(e))
                    else:
                        if sess:
                            _finish(sess, msg)
                        else:
                            st.session_state["last_email"] = email.strip()
                            st.success(msg)
            st.markdown('<div class="or">or</div>', unsafe_allow_html=True)
            _google(be)
        with tab_rs:
            st.markdown("<h1>Reset your password</h1><div class='lead'>Enter your email and we will send a reset link if an account exists.</div>", unsafe_allow_html=True)
            with st.form("reset", clear_on_submit=True):
                email = st.text_input("Email address", key="rs_email", autocomplete="email")
                go = st.form_submit_button("Send reset link", type="primary", width="stretch")
            if go:
                err = accounts.validate_email(email)
                if err:
                    st.error(err)
                else:
                    with st.spinner("Sending..."):
                        be.send_reset(email.strip())
                    st.success("If an account exists for that address, a reset link has been sent. The link works once and expires.")
        st.markdown('<p class="rules" style="margin-top:1.6rem">Sessions last while this browser tab stays open, for up to 12 hours. '
                    'Use a private device for your account.</p></div>', unsafe_allow_html=True)


def render_recovery(be, sess) -> None:
    right = _shell()
    with right:
        st.markdown('<div class="auth-right"><h1>Choose a new password</h1><div class="lead">You opened a password-reset link. Set a new password to continue.</div>', unsafe_allow_html=True)
        with st.form("recover", clear_on_submit=True):
            pw = st.text_input("New password", type="password", autocomplete="new-password")
            pw2 = st.text_input("Confirm new password", type="password", autocomplete="new-password")
            go = st.form_submit_button("Update password", type="primary", width="stretch")
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
                    st.session_state.pop("recovery_pending", None)
                    st.session_state["auth_notice"] = ("success", "Your password was updated.")
                    st.rerun()
        st.button("Cancel and sign out", on_click=accounts.sign_out, key="rec_cancel")
        st.markdown("</div>", unsafe_allow_html=True)


def render_unconfigured(missing: list[str]) -> None:
    right = _shell()
    with right:
        keys = "".join(f"<li><code>{ui.esc(m)}</code></li>" for m in missing)
        st.markdown(
            '<div class="auth-right"><h1>Sign-in is not configured</h1><div class="lead">For security, Crop Yield Explorer does not open without '
            'working authentication. The application owner must add the following Streamlit secrets:</div>'
            f'<ul>{keys}</ul><p class="lead">Setup steps are in the README (section "Authentication setup"). No data is shown until sign-in works.</p></div>',
            unsafe_allow_html=True)
