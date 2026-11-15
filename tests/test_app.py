"""Interface tests. Authentication is replaced by tests/fake_backend.py, so these check the app's own
behaviour (gate, pages, storage rules) but NOT the real Supabase service."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
HARNESS = str(ROOT / "tests" / "harness_app.py")
REAL_APP = str(ROOT / "app.py")
PAGES = ["Overview", "Explore Data", "Crop Analysis", "Correlation Insights", "Dataset Manager",
         "Smart Insights", "My Profile", "Settings"]


def fresh():
    from crop_yield_explorer import accounts
    if hasattr(accounts, "_test_be"):
        del accounts._test_be
    return AppTest.from_file(HARNESS, default_timeout=60).run()


def signed_in():
    at = fresh()
    at.text_input[0].set_value("amina@example.com")
    at.text_input[1].set_value("GoodPassw0rd!")
    at.button[0].click().run()
    return at


def test_unconfigured_app_denies_access():
    from crop_yield_explorer import accounts
    accounts.set_backend_for_tests(None)
    at = AppTest.from_file(REAL_APP, default_timeout=60).run()
    assert not at.exception
    assert "auth_session" not in at.session_state
    text = " ".join(m.value for m in at.markdown)
    assert "not configured" in text.lower() or "configuration" in text.lower()
    assert not at.sidebar.radio  # no workspace navigation


def test_login_screen_shows_no_workspace():
    at = fresh()
    assert not at.exception
    assert "auth_session" not in at.session_state
    assert not at.sidebar.radio


def test_wrong_password_rejected():
    at = fresh()
    at.text_input[0].set_value("amina@example.com")
    at.text_input[1].set_value("WrongPassw0rd")
    at.button[0].click().run()
    assert "auth_session" not in at.session_state
    assert any("Incorrect email or password" in e.value for e in at.error)


def test_empty_password_rejected():
    at = fresh()
    at.text_input[0].set_value("amina@example.com")
    at.button[0].click().run()
    assert "auth_session" not in at.session_state


def test_signin_and_welcome():
    at = signed_in()
    assert not at.exception
    assert at.session_state["auth_session"].user.email == "amina@example.com"
    assert any("Welcome back, Amina." in m.value for m in at.markdown)


def test_password_not_kept_in_state():
    at = signed_in()
    blob = repr({k: at.session_state[k] for k in list(at.session_state.keys())})
    assert "GoodPassw0rd" not in blob


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = signed_in()
    at.sidebar.radio(key="page").set_value(page).run()
    assert not at.exception, [e.value for e in at.exception]


def test_signup_duplicate_rejected():
    at = fresh()
    at.text_input[2].set_value("Amina Bello")
    at.text_input[3].set_value("amina@example.com")
    at.text_input[4].set_value("GoodPassw0rd!")
    at.text_input[5].set_value("GoodPassw0rd!")
    next(b for b in at.button if b.label == "Create account").click().run()
    assert any("already exists" in e.value for e in at.error)


def test_signup_weak_password_and_mismatch():
    at = fresh()
    at.text_input[2].set_value("New Person")
    at.text_input[3].set_value("new@example.com")
    at.text_input[4].set_value("short")
    at.text_input[5].set_value("other")
    next(b for b in at.button if b.label == "Create account").click().run()
    msgs = " ".join(e.value for e in at.error)
    assert "Password needs" in msgs and "do not match" in msgs


def test_signup_success_requires_verification():
    at = fresh()
    at.text_input[2].set_value("New Person")
    at.text_input[3].set_value("new@example.com")
    at.text_input[4].set_value("StrongPassw0rd")
    at.text_input[5].set_value("StrongPassw0rd")
    next(b for b in at.button if b.label == "Create account").click().run()
    assert "auth_session" not in at.session_state
    assert any("verification" in s.value for s in at.success)


def test_sample_data_kpis_computed():
    at = signed_in()
    html = " ".join(m.value for m in at.markdown)
    assert "720" in html
