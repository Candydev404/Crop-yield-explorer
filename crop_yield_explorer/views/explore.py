"""Explore Data page: records, structure, quality, statistics and single-variable exploration."""
from __future__ import annotations

import streamlit as st

from .. import charts, config, data, insights, stats, ui

FMT = {c: "{:,.2f}" for c in ["Mean", "Median", "Minimum", "Maximum", "Std. deviation",
                              "Mean yield", "Median yield", "Min yield", "Max yield", "Total production (t)"]}


def render(df, fdf, active):
    ui.page_header("Explore Data", "Inspect, filter and summarise the records",
                   "Preview the data, check its structure and quality, and read statistics for the current selection.")
    ui.active_filters_chips(active)
    t1, t2, t3, t4, t5, t6 = st.tabs(["Records", "Columns and types", "Missing values", "Summary statistics", "Variable explorer", "Exports"])
    with t1:
        if not ui.require_records(fdf):
            pass
        else:
            n = st.slider("Rows to preview", 5, min(200, max(len(fdf), 6)), min(ui.pref("preview_rows"), max(len(fdf), 5)), key="prev_n") if len(fdf) > 5 else len(fdf)
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
            ui.section("Quartiles, variance, mode and skewness", "Q1 and Q3 are the 25th and 75th percentiles; IQR is their difference. Mode appears only when a value repeats.")
            st.dataframe(stats.extended_stats(fdf).style.format(precision=2, na_rep="n/a"), hide_index=True, width="stretch")
            ui.section("Frequency distribution", "How many records fall in each category or value class.")
            fcols = [c for c in config.COLUMNS if c in fdf.columns and fdf[c].notna().any() and config.COLUMNS[c]["kind"] in ("category", "numeric") and c != "record_id"]
            fc = st.selectbox("Variable", fcols, format_func=config.label, key="freq_pick")
            st.dataframe(stats.frequency_table(fdf, fc).style.format({"Share (%)": "{:.1f}"}), hide_index=True, width="stretch")
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

    with t6:
        ui.section("Export", "Downloads reflect the data and filters in use right now.")
        if not ui.require_records(fdf):
            return
        a, b = st.columns(2, gap="medium")
        with a, ui.card():
            st.markdown("**Datasets**")
            st.download_button("Filtered records (CSV)", fdf.to_csv(index=False).encode("utf-8"), "filtered_crop_records.csv", "text/csv",
                               on_click=ui.notify_cb("Export completed: filtered_crop_records.csv"), key="dl_f", width="stretch")
            st.download_button("Cleaned dataset, all records (CSV)", df.to_csv(index=False).encode("utf-8"), "cleaned_crop_dataset.csv", "text/csv",
                               on_click=ui.notify_cb("Export completed: cleaned_crop_dataset.csv"), key="dl_c", width="stretch")
        with b, ui.card():
            st.markdown("**Statistical results**")
            summ = stats.describe_numeric(fdf)
            st.download_button("Descriptive statistics (CSV)", summ.to_csv(index=False).encode("utf-8"), "descriptive_statistics.csv", "text/csv",
                               on_click=ui.notify_cb("Export completed: descriptive_statistics.csv"), key="dl_s", width="stretch")
            cw = stats.correlations_with_yield(fdf)
            st.download_button("Correlations with yield (CSV)", cw.to_csv(index=False).encode("utf-8"), "correlations_with_yield.csv", "text/csv",
                               on_click=ui.notify_cb("Export completed: correlations_with_yield.csv"), key="dl_k", width="stretch", disabled=cw.empty)
            st.download_button("Analytical insights (Markdown)", insights.as_markdown(insights.generate(fdf)).encode("utf-8"), "insights.md", "text/markdown",
                               on_click=ui.notify_cb("Export completed: insights.md"), key="dl_i", width="stretch")
        st.caption("Chart images: hover over any chart and use the camera icon in its toolbar to download a PNG.")
