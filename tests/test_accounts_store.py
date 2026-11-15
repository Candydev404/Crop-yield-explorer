import pytest

from crop_yield_explorer import accounts, store


def test_email_validation():
    assert accounts.validate_email("a@b.co") is None
    for bad in ["", "a", "a@b", "a@@b.co", "a b@c.co", "x" * 300 + "@b.co"]:
        assert accounts.validate_email(bad)


def test_password_rules():
    assert accounts.password_problems("GoodPassw0rd") == []
    assert accounts.password_problems("short")
    assert accounts.password_problems("alllowercase123")
    assert accounts.password_problems("ALLUPPERCASE123")
    assert accounts.password_problems("NoDigitsHereAtAll")
    assert accounts.password_problems("Aa1" + "x" * 200)


def test_name_validation():
    assert accounts.validate_name("Amina Bello") is None
    assert accounts.validate_name("")
    assert accounts.validate_name("x" * 200)


def test_pkce_pending_is_one_time():
    nonce, verifier, challenge = accounts._new_pending("oauth")
    assert verifier != challenge and len(challenge) >= 43
    assert accounts.pop_pending(nonce) == (verifier, "oauth")
    assert accounts.pop_pending(nonce) is None
    assert accounts.pop_pending("unknown") is None


def test_clean_prefs_rejects_unknown():
    p = store.clean_prefs({"preview_rows": 9999, "evil": 1, "chart_density": "Tall"})
    assert "evil" not in p and p["preview_rows"] == store.DEFAULT_PREFS["preview_rows"] and p["chart_density"] == "Tall"


def test_clean_name():
    assert store.clean_name("  My data \x00 ") == "My data"
    with pytest.raises(store.StoreError):
        store.clean_name("")
    with pytest.raises(store.StoreError):
        store.clean_name("x" * 61)


def test_session_store_roundtrip_and_limits():
    s = store.SessionStore(state={})
    m = s.save("a", b"crop,yield_t_ha\nMaize,3\n", 1, 2)
    assert [d.name for d in s.list()] == ["a"]
    s.rename(m.id, "b")
    assert s.list()[0].name == "b"
    assert s.load(m.id).startswith(b"crop")
    s.delete(m.id)
    assert s.list() == []
    with pytest.raises(store.StoreError):
        s.save("big", b"x" * (store.MAX_SAVE_BYTES + 1), 1, 1)
    for i in range(store.MAX_DATASETS):
        s.save(f"d{i}", b"x", 1, 1)
    with pytest.raises(store.StoreError):
        s.save("one-too-many", b"x", 1, 1)


def test_session_stores_are_isolated():
    a, b = store.SessionStore(state={}), store.SessionStore(state={})
    m = a.save("private", b"data", 1, 1)
    assert b.list() == []
    with pytest.raises(store.StoreError):
        b.load(m.id)
