"""Charts page: the eight required visualisations, each with interpretation."""
from __future__ import annotations

import streamlit as st

from .. import charts, config, interpret, stats, ui


def render(df, fdf, active, synthetic, source):
    ui.header("Charts", "Interactive visualisations that update with the sidebar filters.", synthetic)
    st.caption("Active filters: " + ("; ".join(active) if active else "none"))
    if not ui.require_records(fdf):
        return
    cmap = charts.color_map(df["crop"])
    tabs = st.tabs(["Yield by crop", "Production", "Weather and inputs", "Regions", "Distribution", "Correlation heatmap"])

    with tabs[0]:
        st.plotly_chart(charts.yield_by_crop(fdf), width="stretch", key="c_yc")
        ui.interp(interpret.yield_by_crop(fdf))
        fig = charts.yield_trend(fdf)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="c_tr")
            ui.interp(interpret.trend(fdf))
    with tabs[1]:
        if "production_tonnes" in fdf.columns and fdf["production_tonnes"].notna().any():
            st.plotly_chart(charts.production_by_crop(fdf, cmap), width="stretch", key="c_pc")
            ui.interp(interpret.production(fdf))
        else:
            st.info("The loaded data has no production column.")
    with tabs[2]:
        ui.note("Each scatter plot shows the relationship as a <b>correlation</b>. A trend line summarises how the values move "
                "together; it does not show that changing the variable would change yield.")
        for col, key in (("rainfall_mm", "c_rain"), ("temperature_c", "c_temp"), ("fertilizer_kg_ha", "c_fert")):
            if col in fdf.columns and fdf[col].notna().sum() >= 3:
                st.plotly_chart(charts.scatter_vs_yield(fdf, col, cmap), width="stretch", key=key)
                ui.interp(interpret.scatter(fdf, col))
            else:
                st.info(f"{config.COLUMNS[col]['label']} is not available or has too few values for a scatter plot.")
    with tabs[3]:
        if "region" in fdf.columns and fdf["region"].notna().any():
            st.plotly_chart(charts.region_yield(fdf), width="stretch", key="c_reg")
            ui.interp(interpret.region(fdf))
            if fdf["crop"].nunique() > 1 and fdf["region"].nunique() > 1:
                st.plotly_chart(charts.region_crop_heatmap(fdf), width="stretch", key="c_rch")
                ui.interp("Darker cells indicate higher mean yield. Empty cells mean no records for that crop in that region.")
        else:
            st.info("The loaded data has no region column.")
    with tabs[4]:
        by = st.checkbox("Colour by crop type", value=False, key="dist_by")
        st.plotly_chart(charts.yield_distribution(fdf, cmap, by), width="stretch", key="c_dist")
        ui.interp(interpret.distribution(fdf))
    with tabs[5]:
        method = st.radio("Correlation method", ["Pearson", "Spearman"], horizontal=True, key="hm_method")
        avail = [c for c in config.CORRELATION_COLUMNS if c in fdf.columns]
        corr = stats.correlation_matrix(fdf, avail, method.lower())
        if corr.empty or len(fdf) < 3:
            st.warning("A correlation matrix needs at least three records and two numeric variables that vary.")
        else:
            fig = charts.correlation_heatmap(corr, method)
            st.pyplot(fig, width="content")
            ui.interp(interpret.heatmap(corr, fdf))
