"""Authentication: Supabase Auth backend, input validation and the session gate.

Security design
- Passwords are sent straight to Supabase Auth and are never stored by this application. Password boxes live inside
  forms that clear on submit, so the value does not stay in Streamlit's widget state.
- Only tokens are kept in st.session_state (server memory of this one browser session).
- Every Supabase client is created per call; no client or token is shared between users.
- If Supabase is not configured the application refuses all access and explains what is missing.
- The Supabase service-role key is never used. Only the public anon key is needed.
"""
from __future__ import annotations

import base64
import hashlib
import re
import secrets
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from urllib.parse import urlencode

import streamlit as st

SESSION_MAX_AGE_S = 12 * 3600      # a sign-in is valid for at most 12 hours
REVERIFY_EVERY_S = 600             # the access token is re-checked with Supabase every 10 minutes
REFRESH_MARGIN_S = 90
PENDING_TTL_S = 900


class AuthError(Exception):
    """An error whose message is safe to show to the user."""


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    name: str
    avatar_url: str | None = None
    provider: str = "email"
    created_at: str | None = None
    email_confirmed: bool = True


@dataclass(frozen=True)
class AuthSession:
    user: AuthUser
    access_token: str
    refresh_token: str
    expires_at: int
    signed_in_at: float
    verified_at: float = 0.0


# ----------------------------------------------------------------------------- validation
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")


def validate_email(email: str) -> str | None:
    e = (email or "").strip()
    if not e or len(e) > 254 or not _EMAIL.match(e):
        return "Enter a valid email address."
    return None


def password_problems(pw: str) -> list[str]:
    """Reasons a password is too weak (empty list means acceptable)."""
    p = pw or ""
    out = []
    if len(p) < 10:
        out.append("at least 10 characters")
    if not re.search(r"[a-z]", p):
        out.append("a lowercase letter")
    if not re.search(r"[A-Z]", p):
        out.append("an uppercase letter")
    if not re.search(r"\d", p):
        out.append("a number")
    if len(p) > 128:
        out.append("no more than 128 characters")
    return out


def validate_name(name: str) -> str | None:
    n = (name or "").strip()
    if len(n) < 2 or len(n) > 80:
        return "Enter your full name (2 to 80 characters)."
    return None


def first_name(user: AuthUser) -> str:
    return (user.name or user.email.split("@")[0]).split()[0].capitalize() if (user.name or user.email) else "there"


# ----------------------------------------------------------------------------- configuration
@dataclass(frozen=True)
class AuthSettings:
    url: str
    anon_key: str
    app_url: str


def load_settings() -> tuple[AuthSettings | None, list[str]]:
    """Read Supabase settings from Streamlit secrets. Returns (settings, missing_keys)."""
    try:
        sec = st.secrets["supabase"]
        url, key = str(sec.get("url", "")).strip().rstrip("/"), str(sec.get("anon_key", "")).strip()
        app = str(sec.get("app_url", "")).strip().rstrip("/")
    except Exception:
        url = key = app = ""
    missing = [n for n, v in (("supabase.url", url), ("supabase.anon_key", key), ("supabase.app_url", app)) if not v]
    if missing:
        return None, missing
    return AuthSettings(url, key, app), []


# ----------------------------------------------------------------------------- PKCE pending store (server memory)
_PENDING: dict[str, tuple[str, str, float]] = {}
_LOCK = threading.Lock()


def _new_pending(purpose: str) -> tuple[str, str, str]:
    """Create a one-time nonce with its PKCE verifier. Returns (nonce, verifier, challenge)."""
    nonce = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    now = time.time()
    with _LOCK:
        for k in [k for k, v in _PENDING.items() if v[2] < now]:
            _PENDING.pop(k, None)
        _PENDING[nonce] = (verifier, purpose, now + PENDING_TTL_S)
    return nonce, verifier, challenge


def pop_pending(nonce: str) -> tuple[str, str] | None:
    with _LOCK:
        item = _PENDING.pop(nonce, None)
    if not item or item[2] < time.time():
        return None
    return item[0], item[1]


# ----------------------------------------------------------------------------- Supabase backend
def _ts(value) -> str | None:
    if value is None:
        return None
    return value.strftime("%d %B %Y") if hasattr(value, "strftime") else str(value)[:10]


def _to_user(u) -> AuthUser:
    meta = getattr(u, "user_metadata", None) or {}
    app_meta = getattr(u, "app_metadata", None) or {}
    email = getattr(u, "email", "") or ""
    name = (meta.get("full_name") or meta.get("name") or "").strip()
    return AuthUser(
        id=str(u.id), email=email, name=name or email.split("@")[0],
        avatar_url=meta.get("avatar_url") or meta.get("picture"),
        provider=(app_meta.get("provider") or "email"), created_at=_ts(getattr(u, "created_at", None)),
        email_confirmed=bool(getattr(u, "email_confirmed_at", None)),
    )


def _to_session(resp) -> AuthSession:
    s, u = getattr(resp, "session", None), getattr(resp, "user", None)
    if s is None or u is None:
        raise AuthError("Sign-in did not complete. Please try again.")
    return AuthSession(_to_user(u), s.access_token, s.refresh_token, int(s.expires_at or time.time() + 3000), time.time(), time.time())


class SupabaseBackend:
    """Thin wrapper over Supabase Auth. Every method builds its own short-lived client."""

    def __init__(self, settings: AuthSettings):
        self.s = settings

    def _client(self):
        from supabase import ClientOptions, create_client
        return create_client(self.s.url, self.s.anon_key, options=ClientOptions(auto_refresh_token=False, persist_session=False))

    def sign_up(self, email: str, password: str, name: str) -> tuple[AuthSession | None, str]:
        try:
            r = self._client().auth.sign_up({"email": email, "password": password,
                                             "options": {"data": {"full_name": name}, "email_redirect_to": self.s.app_url}})
        except Exception as exc:
            raise AuthError(_friendly(exc, "We could not create the account. Please try again.")) from None
        if r.user is not None and getattr(r.user, "identities", None) == []:
            raise AuthError("An account with this email already exists. Sign in or reset your password.")
        if r.session is not None:
            return _to_session(r), "Account created."
        return None, "Account created. Check your inbox and follow the verification link, then sign in."

    def sign_in(self, email: str, password: str) -> AuthSession:
        try:
            return _to_session(self._client().auth.sign_in_with_password({"email": email, "password": password}))
        except AuthError:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "confirm" in msg or "verif" in msg:
                raise AuthError("Your email address has not been verified yet. Open the verification link we sent you.") from None
            raise AuthError("Incorrect email or password.") from None

    def oauth_url(self, provider: str = "google") -> str:
        nonce, _, challenge = _new_pending("oauth")
        redirect = f"{self.s.app_url}/?{urlencode({'cyx': nonce})}"
        return f"{self.s.url}/auth/v1/authorize?" + urlencode({
            "provider": provider, "redirect_to": redirect, "code_challenge": challenge, "code_challenge_method": "s256"})

    def send_reset(self, email: str) -> None:
        import httpx
        nonce, _, challenge = _new_pending("recovery")
        redirect = f"{self.s.app_url}/?{urlencode({'cyx': nonce})}"
        try:
            httpx.post(f"{self.s.url}/auth/v1/recover", params={"redirect_to": redirect},
                       headers={"apikey": self.s.anon_key, "Content-Type": "application/json"},
                       json={"email": email, "code_challenge": challenge, "code_challenge_method": "s256"}, timeout=15).raise_for_status()
        except Exception:
            pass  # the user always sees the same message so that accounts cannot be probed

    def exchange(self, code: str, verifier: str) -> AuthSession:
        try:
            return _to_session(self._client().auth.exchange_code_for_session({"auth_code": code, "code_verifier": verifier}))
        except AuthError:
            raise
        except Exception:
            raise AuthError("The sign-in link is invalid or has expired. Please try again.") from None

    def refresh(self, sess: AuthSession) -> AuthSession:
        try:
            r = self._client().auth.refresh_session(sess.refresh_token)
            return replace(_to_session(r), signed_in_at=sess.signed_in_at)
        except Exception:
            raise AuthError("Your session has expired. Please sign in again.") from None

    def verify(self, sess: AuthSession) -> AuthUser:
        try:
            r = self._client().auth.get_user(sess.access_token)
            return _to_user(r.user)
        except Exception:
            raise AuthError("Your session is no longer valid. Please sign in again.") from None

    def _authed(self, sess: AuthSession):
        c = self._client()
        r = c.auth.set_session(sess.access_token, sess.refresh_token)
        return c, (_to_session(r) if getattr(r, "session", None) else sess)

    def update_name(self, sess: AuthSession, name: str) -> AuthSession:
        try:
            c, s2 = self._authed(sess)
            u = c.auth.update_user({"data": {"full_name": name}})
            return replace(s2, user=_to_user(u.user), signed_in_at=sess.signed_in_at)
        except Exception as exc:
            raise AuthError(_friendly(exc, "The profile could not be updated.")) from None

    def update_password(self, sess: AuthSession, new_password: str) -> AuthSession:
        try:
            c, s2 = self._authed(sess)
            c.auth.update_user({"password": new_password})
            return replace(s2, signed_in_at=sess.signed_in_at)
        except Exception as exc:
            raise AuthError(_friendly(exc, "The password could not be changed.")) from None

    def sign_out(self, sess: AuthSession, everywhere: bool = False) -> None:
        try:
            c, _ = self._authed(sess)
            c.auth.sign_out({"scope": "global" if everywhere else "local"})
        except Exception:
            pass

    # persistence helpers (used by store.py)
    def postgrest(self, access_token: str):
        c = self._client()
        c.postgrest.auth(access_token)
        return c


def _friendly(exc: Exception, default: str) -> str:
    m = str(exc).lower()
    if "password" in m and ("weak" in m or "least" in m or "short" in m):
        return "The password is too weak. Use at least 10 characters with upper and lower case letters and a number."
    if "same" in m and "password" in m:
        return "The new password must be different from the current one."
    if "rate" in m or "too many" in m or "seconds" in m:
        return "Too many attempts. Please wait a minute and try again."
    return default


# ----------------------------------------------------------------------------- backend selection and session gate
_override = None


def set_backend_for_tests(backend) -> None:
    """Test harnesses only. The production app.py never calls this."""
    global _override
    _override = backend


def get_backend():
    if _override is not None:
        return _override
    settings, _ = load_settings()
    return SupabaseBackend(settings) if settings else None


def current_session() -> AuthSession | None:
    return st.session_state.get("auth_session")


def sign_out(everywhere: bool = False) -> None:
    sess, be = current_session(), get_backend()
    if sess and be:
        be.sign_out(sess, everywhere)
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def _handle_callback(be) -> None:
    """Complete an OAuth or password-recovery redirect (?code=...&cyx=...)."""
    qp = st.query_params
    code, nonce = qp.get("code"), qp.get("cyx")
    if not code or not nonce:
        return
    pend = pop_pending(nonce)
    st.query_params.clear()
    if pend is None:
        st.session_state["auth_notice"] = ("error", "That sign-in link has expired or was already used. Please sign in again.")
        return
    verifier, purpose = pend
    try:
        sess = be.exchange(code, verifier)
    except AuthError as e:
        st.session_state["auth_notice"] = ("error", str(e))
        return
    st.session_state["auth_session"] = sess
    if purpose == "recovery":
        st.session_state["recovery_pending"] = True


def _keep_session_fresh(be, sess: AuthSession):
    now = time.time()
    if now - sess.signed_in_at > SESSION_MAX_AGE_S:
        raise AuthError("Your session has expired. Please sign in again.")
    if sess.expires_at - now < REFRESH_MARGIN_S:
        sess = be.refresh(sess)
    if now - sess.verified_at > REVERIFY_EVERY_S:
        user = be.verify(sess)           # server-side check of the token
        sess = replace(sess, user=user, verified_at=now)
    return sess


def gate(render_login, render_recovery, render_unconfigured) -> AuthSession:
    """Return a verified session or render a sign-in screen and stop the script. There is no bypass."""
    be = get_backend()
    if be is None:
        _, missing = load_settings()
        render_unconfigured(missing)
        st.stop()
    _handle_callback(be)
    sess = current_session()
    if sess is not None:
        try:
            sess = _keep_session_fresh(be, sess)
            st.session_state["auth_session"] = sess
        except AuthError as e:
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state["auth_notice"] = ("info", str(e))
            sess = None
    if sess is None:
        render_login(be)
        st.stop()
    if st.session_state.get("recovery_pending"):
        render_recovery(be, sess)
        st.stop()
    return sess
