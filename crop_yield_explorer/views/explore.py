"""Explore Data page: records, structure, quality, statistics and single-variable exploration."""
from __future__ import annotations

import streamlit as st

from .. import charts, config, data, stats, ui

FMT = {c: "{:,.2f}" for c in ["Mean", "Median", "Minimum", "Maximum", "Std. deviation",
                              "Mean yield", "Median yield", "Min yield", "Max yield", "Total production (t)"]}


def render(df, fdf, active):
    ui.page_header("Explore Data", "Inspect, filter and summarise the records",
                   "Preview the data, check its structure and quality, and read statistics for the current selection.")
    ui.active_filters_chips(active)
    t1, t2, t3, t4, t5 = st.tabs(["Records", "Columns and types", "Missing values", "Summary statistics", "Variable explorer"])
    with t1:
        if not ui.require_records(fdf):
            pass
        else:
            n = st.slider("Rows to preview", 5, min(200, max(len(fdf), 6)), min(20, max(len(fdf), 5)), key="prev_n") if len(fdf) > 5 else len(fdf)
            st.dataframe(fdf.head(n), hide_index=True, width="stretch")
            st.caption(f"Showing {min(n, len(fdf)):,} of {len(fdf):,} filtered records ({len(df):,} loaded).")
            st.download_button("Download filtered records (CSV)", fdf.to_csv(index=False).encode("utf-8"),
                               file_name="filtered_crop_records.csv", mime="text/csv")
    with t2:
        st.dataframe(data.schema_table(df), hide_index=True, width="stretch")
        st.caption("Column names are standardised on upload (for example 'Rainfall' becomes rainfall_mm).")
    with t3:
        m = data.missing_table(df)
        total = int(m["Missing values"].sum())
        if total == 0:
            ui.note("No missing values were found in the loaded data.")
        else:
            ui.note(f"{total:,} missing value(s) across {int((m['Missing values'] > 0).sum())} column(s). Missing numeric values are left "
                    "empty and are excluded from calculations that need them (pairwise deletion).", "caution")
        st.dataframe(m, hide_index=True, width="stretch")
    with t4:
        if ui.require_records(fdf):
            ui.section("Descriptive statistics", "Count excludes missing values. Standard deviation is the sample standard deviation (n - 1).")
            st.dataframe(stats.describe_numeric(fdf).style.format(FMT, na_rep="n/a"), hide_index=True, width="stretch")
            ui.section("Yield by group")
            opts = [c for c in config.CATEGORY_COLUMNS if c in fdf.columns and fdf[c].notna().any()]
            by = st.selectbox("Group by", opts, format_func=lambda c: config.label(c, False), key="grp_by")
            st.dataframe(stats.group_summary(fdf, by).style.format(FMT, na_rep="n/a"), hide_index=True, width="stretch")
    with t5:
        if ui.require_records(fdf):
            cols = [c for c in config.NUMERIC_COLUMNS if c in fdf.columns and fdf[c].notna().sum() > 0 and c != "year"]
            col = st.selectbox("Variable", cols, index=cols.index("yield_t_ha") if "yield_t_ha" in cols else 0,
                               format_func=config.label, key="var_pick")
            s = fdf[col].dropna()
            ui.kpi_grid([
                ("records", "Valid values", f"{len(s):,}", "", f"{len(fdf) - len(s):,} missing"),
                ("yield", "Mean", ui.fmt_num(s.mean(), 2), config.COLUMNS[col]["unit"], "average"),
                ("crops", "Median", ui.fmt_num(s.median(), 2), config.COLUMNS[col]["unit"], "middle value"),
                ("peak", "Range", f"{ui.fmt_num(s.min(), 1)} to {ui.fmt_num(s.max(), 1)}", config.COLUMNS[col]["unit"], "minimum to maximum"),
            ], "mini-grid")
            with ui.card():
                ui.plot(charts.variable_histogram(fdf, col), "x_hist")
