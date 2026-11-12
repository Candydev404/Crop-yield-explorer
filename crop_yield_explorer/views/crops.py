"""Crop Analysis page: compare crops and examine one crop in depth."""
from __future__ import annotations

import streamlit as st

from .. import charts, config, interpret, stats, ui

FMT = {c: "{:,.2f}" for c in ["Mean yield", "Median yield", "Min yield", "Max yield", "Std. deviation", "Total production (t)"]}


def render(df, fdf, active):
    ui.page_header("Crop Analysis", "How each crop performs",
                   "Compare crop types, then choose one crop to see its yield, production and regional performance.")
    ui.active_filters_chips(active)
    if not ui.require_records(fdf):
        return
    cmap = charts.color_map(df["crop"])
    ui.section("Compare crop types", "Average yield and total production for every crop in the selection.")
    c1, c2 = st.columns(2, gap="medium")
    with c1, ui.card():
        ui.plot(charts.yield_by_crop(fdf), "c_yc")
        ui.interp(interpret.yield_by_crop(fdf))
    with c2, ui.card():
        if "production_tonnes" in fdf.columns and fdf["production_tonnes"].notna().any():
            ui.plot(charts.production_by_crop(fdf, cmap), "c_pc")
            ui.interp(interpret.production(fdf))
        else:
            ui.empty_state("No production data", "The loaded data has no production column.")
    with st.expander("Crop comparison table", expanded=False):
        st.dataframe(stats.group_summary(fdf, "crop").style.format(FMT, na_rep="n/a"), hide_index=True, width="stretch")

    ui.section("Crop profile", "Pick a crop to see how it compares with the others in the current selection.")
    crops_here = sorted(fdf["crop"].dropna().unique().tolist())
    crop = st.selectbox("Crop", crops_here, key="crop_pick")
    sub = fdf[fdf["crop"] == crop]
    k = stats.kpis(sub)
    best_region = None
    if "region" in sub.columns and sub["region"].notna().any():
        best_region = sub.groupby("region")["yield_t_ha"].mean().idxmax()
    ui.kpi_grid([
        ("records", "Records", f"{k['records']:,}", "", f"{crop} records in the selection"),
        ("yield", "Average yield", ui.fmt_num(k["mean_yield"], 2), "t/ha", f"overall selection: {ui.fmt_num(stats.kpis(fdf)['mean_yield'], 2)} t/ha"),
        ("production", "Total production", ui.fmt_num(k["total_production"], 1) if k["total_production"] is not None else "n/a", "t", "tonnes"),
        ("regions", "Best region by mean yield", str(best_region) if best_region else "n/a", "", "highest mean yield for this crop"),
    ], "mini-grid")
    d1, d2 = st.columns(2, gap="medium")
    with d1, ui.card():
        ui.plot(charts.crop_vs_all(fdf, crop), "c_vs")
        ui.interp(f"The green bars show how {crop} yields are spread; grey bars show the other crops in the selection. "
                  "Overlap means similar yields; separate clusters mean the crops perform very differently.")
    with d2, ui.card():
        tr = charts.yield_trend(sub)
        if tr is not None:
            tr.update_layout(title_text=f"Mean yield by year: {crop}")
            ui.plot(tr, "c_trend")
            ui.interp(interpret.trend(sub))
        else:
            ui.empty_state("Trend not available", "This crop has records for fewer than two years in the selection.")
    if "region" in sub.columns and sub["region"].notna().any():
        with ui.card():
            fig = charts.region_yield(sub)
            fig.update_layout(title_text=f"Mean yield by region: {crop}")
            ui.plot(fig, "c_reg")
            ui.interp(interpret.region(sub))
