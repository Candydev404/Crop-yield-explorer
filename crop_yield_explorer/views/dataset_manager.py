"""Dataset Manager: load or upload data, review quality, and keep a private library of saved datasets."""
from __future__ import annotations

import streamlit as st

from .. import config, data, store, ui


def _use_saved(ds_id: str, name: str) -> None:
    c = ui.ctx()
    try:
        res = data.load_csv_bytes(c["store"].load(ds_id))
    except store.StoreError as e:
        st.session_state["dm_msg"] = ("error", str(e))
        return
    if not res.ok:
        st.session_state["dm_msg"] = ("error", "The saved file no longer passes validation.")
        return
    ui.activate(res, name, False)
    st.session_state["source_choice"] = "Upload my own CSV"
    ui.notify("success", f"Loaded saved dataset: {name}.")


def _quality(df, res) -> None:
    kinds = {"numeric": 0, "category": 0}
    for c in df.columns:
        k = config.COLUMNS.get(c, {}).get("kind")
        if k in kinds and df[c].notna().any():
            kinds[k] += 1
    m = data.missing_table(df)
    st.dataframe([
        {"Check": "Records read from the file", "Result": f"{res.rows_read:,}"},
        {"Check": "Records kept after cleaning", "Result": f"{res.rows_kept:,}"},
        {"Check": "Records removed (unusable rows and exact duplicates)", "Result": f"{max(res.rows_read - res.rows_kept, 0):,}"},
        {"Check": "Dimensions", "Result": f"{df.shape[0]:,} rows by {df.shape[1]} columns"},
        {"Check": "Numeric columns / category columns", "Result": f"{kinds['numeric']} / {kinds['category']}"},
        {"Check": "Missing values (left empty, not imputed)", "Result": f"{int(m['Missing values'].sum()):,}"},
        {"Check": "Warnings raised", "Result": f"{len(res.warnings)}"},
    ], hide_index=True, width="stretch")


def render(df, fdf, active):
    c = ui.ctx()
    ui.page_header("Dataset Manager", "Load, check and keep your datasets",
                   "Use the bundled synthetic sample, upload a CSV file, or reopen a dataset saved in your private workspace.")
    res = st.session_state["result"]
    msg = st.session_state.pop("dm_msg", None)
    if msg:
        (st.error if msg[0] == "error" else st.success)(msg[1])
    if c["store"].persistent:
        ui.note("Saved datasets are stored in your account database. Only you can read them: access is enforced by Row Level Security.")
    else:
        ui.note("Persistent storage is not set up for this deployment, so saved datasets last only for this browser session.", "caution")

    ui.section("Active dataset")
    m = data.missing_table(df)
    ui.kpi_grid([
        ("records", "Records", f"{len(df):,}", "", f"{res.rows_read:,} rows read, {res.rows_kept:,} kept"),
        ("production", "Columns", f"{df.shape[1]:,}", "", "after standardising names"),
        ("peak", "Missing values", f"{int(m['Missing values'].sum()):,}", "", "left empty, not imputed"),
        ("regions", "Source", "Sample" if st.session_state.get("synthetic") else "Upload", "", st.session_state.get("source_name", "")),
    ], "mini-grid")

    ui.section("Load data", "An invalid file never replaces the dataset that is already loaded.")
    with ui.card():
        ui.dataset_source_controls()
        ui.chips(["CSV or TXT", f"Up to {config.MAX_UPLOAD_MB} MB", "UTF-8 or Windows encodings", "Comma or semicolon separated", "Required: crop and yield"])

    if not st.session_state.get("synthetic"):
        with ui.card():
            st.markdown("**Save this dataset to your workspace**")
            with st.form("save_ds"):
                default = st.session_state.get("source_name", "dataset").rsplit(".", 1)[0][:60]
                name = st.text_input("Name", value=default, max_chars=60)
                go = st.form_submit_button("Save dataset", type="primary")
            if go:
                try:
                    payload = df.to_csv(index=False).encode("utf-8")
                    meta = c["store"].save(name, payload, len(df), df.shape[1])
                except store.StoreError as e:
                    st.error(str(e))
                else:
                    ui.notify("success", f"Saved \"{meta.name}\" to your workspace.")
                    st.success(f"Saved \"{meta.name}\".")

    ui.section("My datasets", f"Up to {store.MAX_DATASETS} datasets, 5 MB each. Only your own datasets are listed.")
    try:
        lib = c["store"].list()
    except store.StoreError as e:
        lib = []
        st.error(str(e))
    if not lib:
        ui.empty_state("No saved datasets yet", "Upload a CSV file above, then choose Save dataset to keep it in your workspace.")
    for d in lib:
        with ui.card():
            a, b, cc, dd = st.columns([4, 1.1, 1.3, 1.2], gap="small", vertical_alignment="center")
            a.markdown(f"**{ui.esc(d.name)}**  \n<small>{d.rows:,} rows, {d.cols} columns, {d.size_bytes / 1024:,.0f} KB, saved {ui.esc(d.created_at)}</small>", unsafe_allow_html=True)
            b.button("Use", key=f"use_{d.id}", on_click=_use_saved, args=(d.id, d.name), width="stretch")
            with cc.popover("Rename", width="stretch"):
                with st.form(f"rn_{d.id}"):
                    nn = st.text_input("New name", value=d.name, max_chars=60)
                    ok = st.form_submit_button("Rename")
                if ok:
                    try:
                        c["store"].rename(d.id, nn)
                    except store.StoreError as e:
                        st.error(str(e))
                    else:
                        ui.notify("info", f"Renamed to \"{nn.strip()}\".")
                        st.rerun()
            with dd.popover("Remove", width="stretch"):
                st.caption("This permanently removes the saved copy.")
                if st.button("Confirm remove", key=f"rm_{d.id}", type="primary"):
                    try:
                        c["store"].delete(d.id)
                    except store.StoreError as e:
                        st.error(str(e))
                    else:
                        ui.notify("info", f"Removed \"{d.name}\".")
                        st.rerun()

    ui.section("Data quality summary", "What was found and changed when the active dataset was loaded.")
    _quality(df, res)
    for w in res.warnings:
        st.warning(w)
    for n in res.notes:
        st.info(n)
    if not res.warnings:
        ui.note("No values were removed or corrected during validation.")

    ui.section("Preview", "The first records of the active dataset.")
    st.dataframe(df.head(10), hide_index=True, width="stretch")

    ui.section("Expected format", "Only crop and yield are required. Other columns unlock more analysis.")
    st.markdown("**Required columns:** `crop` and `yield_t_ha`. Yield can also be calculated if `production_tonnes` and `land_area_ha` are supplied.")
    rows = [{"Column": k, "Meaning": config.COLUMNS[k]["label"], "Unit": config.COLUMNS[k]["unit"] or "-",
             "Type": config.COLUMNS[k]["kind"], "Required": "Yes" if k in config.REQUIRED_COLUMNS else "No"} for k in config.COLUMNS]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Common alternative names such as Crop Type, Location, Rainfall, Temperature and Yield are recognised automatically.")
    st.download_button("Download the sample dataset (CSV)", config.SAMPLE_PATH.read_bytes(), file_name="sample_crop_yield.csv", mime="text/csv",
                       on_click=ui.notify_cb("Export completed: sample_crop_yield.csv"), key="dl_sample")
