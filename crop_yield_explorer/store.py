"""Per-user storage for saved datasets and preferences.

SupabaseStore keeps data in Postgres tables protected by Row Level Security (see supabase_schema.sql), so a user's
rows can only be read or changed with that user's own access token. SessionStore is the fallback when Supabase
storage is not set up: it keeps data in this browser session only and is lost when the session ends.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import streamlit as st

MAX_DATASETS = 10
MAX_SAVE_BYTES = 5 * 1024 * 1024

DEFAULT_PREFS = {"preview_rows": 20, "chart_density": "Standard", "show_interpretations": True, "correlation_method": "Pearson"}
PREF_CHOICES = {"preview_rows": [10, 20, 50, 100], "chart_density": ["Compact", "Standard", "Tall"],
                "show_interpretations": [True, False], "correlation_method": ["Pearson", "Spearman"]}


class StoreError(Exception):
    """Message safe to show to the user."""


@dataclass(frozen=True)
class DatasetMeta:
    id: str
    name: str
    rows: int
    cols: int
    size_bytes: int
    created_at: str


def clean_name(name: str) -> str:
    n = re.sub(r"[\x00-\x1f\x7f]", "", (name or "")).strip()
    if not 1 <= len(n) <= 60:
        raise StoreError("Dataset names must be 1 to 60 characters.")
    return n


def clean_prefs(raw: dict | None) -> dict:
    """Keep only known preferences with allowed values."""
    out = dict(DEFAULT_PREFS)
    for k, v in (raw or {}).items():
        if k in PREF_CHOICES and v in PREF_CHOICES[k]:
            out[k] = v
    return out


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%d %b %Y %H:%M")


class SessionStore:
    """In-memory store scoped to one browser session."""
    persistent = False

    def __init__(self, state=None):
        self.state = st.session_state if state is None else state
        self.state.setdefault("_lib", {})
        self.state.setdefault("_prefs", dict(DEFAULT_PREFS))

    def list(self) -> list[DatasetMeta]:
        return sorted((m for m, _ in self.state["_lib"].values()), key=lambda m: m.created_at, reverse=True)

    def save(self, name: str, content: bytes, rows: int, cols: int) -> DatasetMeta:
        name = clean_name(name)
        if len(content) > MAX_SAVE_BYTES:
            raise StoreError("This dataset is larger than the 5 MB limit for saved datasets.")
        if len(self.state["_lib"]) >= MAX_DATASETS:
            raise StoreError(f"You can keep up to {MAX_DATASETS} saved datasets. Remove one first.")
        meta = DatasetMeta(uuid.uuid4().hex, name, rows, cols, len(content), _now())
        self.state["_lib"][meta.id] = (meta, content)
        return meta

    def rename(self, ds_id: str, name: str) -> None:
        name = clean_name(name)
        if ds_id not in self.state["_lib"]:
            raise StoreError("Dataset not found.")
        m, c = self.state["_lib"][ds_id]
        self.state["_lib"][ds_id] = (DatasetMeta(m.id, name, m.rows, m.cols, m.size_bytes, m.created_at), c)

    def delete(self, ds_id: str) -> None:
        self.state["_lib"].pop(ds_id, None)

    def load(self, ds_id: str) -> bytes:
        if ds_id not in self.state["_lib"]:
            raise StoreError("Dataset not found.")
        return self.state["_lib"][ds_id][1]

    def get_prefs(self) -> dict:
        return clean_prefs(self.state["_prefs"])

    def save_prefs(self, prefs: dict) -> None:
        self.state["_prefs"] = clean_prefs(prefs)


class SupabaseStore:
    """Postgres storage through PostgREST with the signed-in user's own token (Row Level Security applies)."""
    persistent = True

    def __init__(self, backend, access_token: str, user_id: str):
        self.client = backend.postgrest(access_token)
        self.uid = user_id

    def _t(self, name):
        return self.client.table(name)

    def list(self) -> list[DatasetMeta]:
        try:
            r = self._t("datasets").select("id,name,rows,cols,size_bytes,created_at").eq("user_id", self.uid).order("created_at", desc=True).execute()
        except Exception:
            raise StoreError("Saved datasets could not be loaded.") from None
        return [DatasetMeta(d["id"], d["name"], d["rows"], d["cols"], d["size_bytes"], str(d["created_at"])[:16].replace("T", " ")) for d in r.data]

    def save(self, name: str, content: bytes, rows: int, cols: int) -> DatasetMeta:
        name = clean_name(name)
        if len(content) > MAX_SAVE_BYTES:
            raise StoreError("This dataset is larger than the 5 MB limit for saved datasets.")
        if len(self.list()) >= MAX_DATASETS:
            raise StoreError(f"You can keep up to {MAX_DATASETS} saved datasets. Remove one first.")
        try:
            r = self._t("datasets").insert({"user_id": self.uid, "name": name, "rows": rows, "cols": cols,
                                            "size_bytes": len(content), "content": content.decode("utf-8")}).execute()
        except Exception:
            raise StoreError("The dataset could not be saved.") from None
        d = r.data[0]
        return DatasetMeta(d["id"], d["name"], d["rows"], d["cols"], d["size_bytes"], str(d["created_at"])[:16].replace("T", " "))

    def rename(self, ds_id: str, name: str) -> None:
        name = clean_name(name)
        try:
            self._t("datasets").update({"name": name}).eq("id", ds_id).eq("user_id", self.uid).execute()
        except Exception:
            raise StoreError("The dataset could not be renamed.") from None

    def delete(self, ds_id: str) -> None:
        try:
            self._t("datasets").delete().eq("id", ds_id).eq("user_id", self.uid).execute()
        except Exception:
            raise StoreError("The dataset could not be removed.") from None

    def load(self, ds_id: str) -> bytes:
        try:
            r = self._t("datasets").select("content").eq("id", ds_id).eq("user_id", self.uid).execute()
        except Exception:
            raise StoreError("The dataset could not be loaded.") from None
        if not r.data:
            raise StoreError("Dataset not found.")
        return r.data[0]["content"].encode("utf-8")

    def get_prefs(self) -> dict:
        try:
            r = self._t("user_settings").select("prefs").eq("user_id", self.uid).execute()
            return clean_prefs(r.data[0]["prefs"] if r.data else None)
        except Exception:
            return dict(DEFAULT_PREFS)

    def save_prefs(self, prefs: dict) -> None:
        try:
            self._t("user_settings").upsert({"user_id": self.uid, "prefs": clean_prefs(prefs)}).execute()
        except Exception:
            raise StoreError("Preferences could not be saved.") from None


def get_store(backend, sess) -> SessionStore | SupabaseStore:
    """Persistent store when Supabase storage is reachable, otherwise a session-only store."""
    key = "_store_kind"
    if st.session_state.get(key) != "session" and hasattr(backend, "postgrest"):
        try:
            s = SupabaseStore(backend, sess.access_token, sess.user.id)
            if key not in st.session_state:
                s.list()                       # probe once: fails if the schema has not been created
                st.session_state[key] = "supabase"
            return s
        except Exception:
            st.session_state[key] = "session"
    return SessionStore()
