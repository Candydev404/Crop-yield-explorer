"""In-memory stand-in for SupabaseBackend, used ONLY by tests. It is not a real identity provider."""
import time
from dataclasses import replace

from crop_yield_explorer.accounts import AuthError, AuthSession, AuthUser


class FakeBackend:
    def __init__(self):
        self.users = {}          # email -> (password, AuthUser)
        self.calls = []

    def add_user(self, email, password, name="Test User"):
        u = AuthUser(id=f"u-{len(self.users)+1}", email=email, name=name, created_at="2026-01-01T00:00:00Z")
        self.users[email] = (password, u)
        return u

    def _sess(self, u):
        now = time.time()
        return AuthSession(user=u, access_token="tok-" + u.id, refresh_token="ref-" + u.id,
                           expires_at=int(now + 3600), signed_in_at=now, verified_at=now)

    def sign_up(self, email, password, name):
        if email in self.users:
            raise AuthError("An account with this email already exists. Sign in or reset your password.")
        self.add_user(email, password, name)
        return None, "Account created. Check your inbox and follow the verification link, then sign in."

    def sign_in(self, email, password):
        rec = self.users.get(email)
        if not rec or rec[0] != password:
            raise AuthError("Incorrect email or password.")
        return self._sess(rec[1])

    def oauth_url(self, provider="google"):
        return "https://example.invalid/authorize"

    def send_reset(self, email):
        self.calls.append(("reset", email))

    def exchange(self, code, verifier):
        raise AuthError("invalid")

    def refresh(self, sess):
        return sess

    def verify(self, sess):
        return sess.user

    def update_name(self, sess, name):
        return replace(sess, user=replace(sess.user, name=name))

    def update_password(self, sess, pw):
        self.users[sess.user.email] = (pw, sess.user)
        return sess

    def sign_out(self, sess, everywhere=False):
        self.calls.append(("signout", everywhere))
