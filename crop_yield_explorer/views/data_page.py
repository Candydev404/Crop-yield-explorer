"""Data page: preview, structure, missing values, validation messages, download."""
from __future__ import annotations

import streamlit as st

from .. import config, data, ui


def render(df, fdf, active, synthetic, source):
    ui.header("Data and Validation", "Preview records, inspect columns and data types, and review data quality.", synthetic)
    res = st.session_state["result"]
    st.caption(f"Data source: {source}  |  {len(df):,} records loaded, {len(fdf):,} after filters")

    up_res = st.session_state.get("upload_result")
    if up_res is not None and not up_res.ok and st.session_state.get("source_choice", "").startswith("Upload"):
        st.error("The uploaded file could not be loaded:")
        for e in up_res.errors:
            st.markdown(f"- {e}")
        st.caption("The previously loaded dataset is still in use below.")

    for w in res.warnings:
        st.warning(w)
    for n in res.notes:
        st.info(n)
    if not res.warnings and not res.errors:
        ui.note(f"Validation passed for the loaded dataset ({source}): required columns are present and no values were removed or corrected.")

    t1, t2, t3, t4 = st.tabs(["Record preview", "Columns and data types", "Missing values", "Expected format"])
    with t1:
        n = st.slider("Rows to preview", 5, min(200, max(len(fdf), 6)), min(20, max(len(fdf), 5)), key="prev_n") if len(fdf) > 5 else len(fdf)
        if len(fdf):
            st.dataframe(fdf.head(n), hide_index=True, width="stretch")
            st.download_button("Download filtered records (CSV)", fdf.to_csv(index=False).encode("utf-8"),
                               file_name="filtered_crop_records.csv", mime="text/csv")
        else:
            st.warning("No records match the current filters.")
    with t2:
        st.dataframe(data.schema_table(df), hide_index=True, width="stretch")
        st.caption("Column names are standardised on upload (for example 'Rainfall' becomes rainfall_mm).")
    with t3:
        m = data.missing_table(df)
        total = int(m["Missing values"].sum())
        if total == 0:
            st.success("No missing values were found in the loaded data.")
        else:
            st.write(f"{total:,} missing value(s) across {int((m['Missing values'] > 0).sum())} column(s). "
                     "Missing numeric values are left empty and are excluded from calculations that need them (pairwise deletion).")
        st.dataframe(m, hide_index=True, width="stretch")
    with t4:
        st.markdown("**Required columns:** `crop` and `yield_t_ha` (yield can also be calculated if `production_tonnes` and `land_area_ha` are supplied).")
        rows = [{"Column": c, "Meaning": config.COLUMNS[c]["label"], "Unit": config.COLUMNS[c]["unit"] or "-",
                 "Type": config.COLUMNS[c]["kind"], "Required": "Yes" if c in config.REQUIRED_COLUMNS else "No"}
                for c in config.COLUMNS]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.caption("Common alternative names such as Crop Type, Location, Rainfall, Temperature and Yield are recognised automatically.")
        st.download_button("Download the sample dataset (CSV)", config.SAMPLE_PATH.read_bytes(),
                           file_name="sample_crop_yield.csv", mime="text/csv")
