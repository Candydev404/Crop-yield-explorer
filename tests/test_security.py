import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = [p for p in list(ROOT.glob("*.py")) + list((ROOT / "crop_yield_explorer").rglob("*.py"))]


def test_no_service_role_or_jwt_in_code():
    for p in SRC:
        t = p.read_text()
        assert "service_role" not in t, p
        assert not re.search(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}", t), p


def test_real_secrets_file_not_in_repo_and_ignored():
    assert not (ROOT / ".streamlit" / "secrets.toml").exists()
    assert "secrets.toml" in (ROOT / ".gitignore").read_text()
    ex = (ROOT / ".streamlit" / "secrets.toml.example").read_text()
    assert "service_role" in ex.lower() and "never" in ex.lower()  # warning only
    assert "YOUR-" in ex


def test_no_password_stored_in_session_state_code():
    t = (ROOT / "crop_yield_explorer" / "views" / "login.py").read_text()
    assert not re.search(r'session_state\[[^\]]*(pw|password)', t)


def test_rls_enabled_and_anon_revoked():
    sql = re.sub(r"\s+", " ", (ROOT / "supabase_schema.sql").read_text().lower())
    for table in ("datasets", "user_settings"):
        assert f"alter table public.{table} enable row level security" in sql
        assert f"alter table public.{table} force row level security" in sql
    assert "auth.uid() = user_id" in sql and "revoke all" in sql


def test_no_guest_or_demo_login_text():
    for p in (ROOT / "crop_yield_explorer" / "views").glob("*.py"):
        t = p.read_text().lower()
        assert "continue as guest" not in t and "demo account" not in t, p
