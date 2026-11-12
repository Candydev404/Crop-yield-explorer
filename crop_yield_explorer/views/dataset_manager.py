"""Dataset Manager page: choose or upload a dataset, review validation feedback and the expected format."""
from __future__ import annotations

import streamlit as st

from .. import config, data, ui


def render(df, fdf, active):
    ui.page_header("Dataset Manager", "Load and validate your data",
                   "Use the bundled synthetic sample or upload a CSV file. Every file is checked before it is used.")
    res = st.session_state["result"]
    m = data.missing_table(df)
    ui.section("Active dataset")
    ui.kpi_grid([
        ("records", "Records", f"{len(df):,}", "", f"{res.rows_read:,} rows read, {res.rows_kept:,} kept"),
        ("crops", "Columns", f"{df.shape[1]:,}", "", "after standardising names"),
        ("area", "Missing values", f"{int(m['Missing values'].sum()):,}", "", "left empty, not imputed"),
        ("regions", "Source", "Sample" if st.session_state.get("synthetic") else "Upload", "", st.session_state.get("source_name", "")),
    ], "mini-grid")

    ui.section("Load data", "Choose the data source. An invalid file never replaces the dataset that is already loaded.")
    with ui.card():
        ui.dataset_source_controls()
        ui.chips(["CSV or TXT", f"Up to {config.MAX_UPLOAD_MB} MB", "UTF-8 or Windows encodings", "Comma or semicolon separated",
                  "Required: crop and yield"])

    ui.section("Validation report", "What was found and changed when the active dataset was loaded.")
    for w in res.warnings:
        st.warning(w)
    for n in res.notes:
        st.info(n)
    if not res.warnings and not res.errors:
        ui.note(f"Validation passed for {ui.esc(st.session_state.get('source_name'))}: required columns are present and no values "
                "were removed or corrected.")

    ui.section("Preview", "The first records of the active dataset.")
    st.dataframe(df.head(10), hide_index=True, width="stretch")

    ui.section("Expected format", "Only crop and yield are required. Other columns unlock more analysis.")
    st.markdown("**Required columns:** `crop` and `yield_t_ha`. Yield can also be calculated if `production_tonnes` and `land_area_ha` are supplied.")
    rows = [{"Column": c, "Meaning": config.COLUMNS[c]["label"], "Unit": config.COLUMNS[c]["unit"] or "-",
             "Type": config.COLUMNS[c]["kind"], "Required": "Yes" if c in config.REQUIRED_COLUMNS else "No"} for c in config.COLUMNS]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Common alternative names such as Crop Type, Location, Rainfall, Temperature and Yield are recognised automatically.")
    st.download_button("Download the sample dataset (CSV)", config.SAMPLE_PATH.read_bytes(),
                       file_name="sample_crop_yield.csv", mime="text/csv")
