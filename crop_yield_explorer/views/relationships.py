"""Relationships page: correlation heatmap, ranked associations and a scatter explorer."""
from __future__ import annotations

import streamlit as st

from .. import charts, config, interpret, stats, ui


def render(df, fdf, active):
    ui.page_header("Relationships", "Which variables move together with yield",
                   "Correlation coefficients, scatter plots and plain-language interpretations. Associations only; not cause and effect.")
    ui.active_filters_chips(active)
    c1, c2, c3 = st.columns(3, gap="medium")
    ui.fact(c1, "What correlation shows", "The strength and direction of a statistical relationship between two variables, from -1 to +1.")
    ui.fact(c2, "What it does not show", "That one variable causes the other to change. A relationship in the data is not proof of cause and effect.")
    ui.fact(c3, "Why caution is needed", "Crop type, soil, pests, variety, planting date and irrigation may influence yield and may also relate to the variable examined.")
    if not ui.require_records(fdf, 3):
        return
    method = st.radio("Correlation method", ["Pearson", "Spearman"], horizontal=True, key="rel_method",
                      help="Pearson measures linear association; Spearman measures rank (monotonic) association.")
    avail = [c for c in config.CORRELATION_COLUMNS if c in fdf.columns]
    corr = stats.correlation_matrix(fdf, avail, method.lower())

    ui.section("Correlation heatmap", "Every pair of numeric variables. Hover over a cell for the exact coefficient.")
    with ui.card():
        if corr.empty:
            ui.empty_state("Heatmap not available", "A correlation matrix needs at least three records and two numeric variables that vary.")
        else:
            ui.plot(charts.correlation_heatmap_interactive(corr, method), "r_heat")
            ui.interp(interpret.heatmap(corr, fdf))
            with st.expander("Static version (Seaborn)"):
                st.pyplot(charts.correlation_heatmap(corr, method), width="content")

    ui.section("Relationship summary", "Each variable's association with crop yield, ranked by strength.")
    cw = stats.correlations_with_yield(fdf, method.lower())
    if cw.empty:
        ui.empty_state("No correlations to show", "Too few records, or the variables do not vary in this selection.")
    else:
        a, b = st.columns([5, 4], gap="medium")
        with a, ui.card():
            ui.plot(charts.correlation_bars(cw, method), "r_bars")
        with b:
            st.dataframe(cw.style.format({"Coefficient (r)": "{:+.3f}"}), hide_index=True, width="stretch")
            if cw["Variable"].str.startswith("Total production").any():
                st.caption("Total production is calculated from yield and land area, so its coefficient with yield reflects that "
                           "arithmetic and is not a finding about agricultural drivers.")
        main = cw[~cw["Variable"].str.startswith("Total production")]
        top = main.iloc[0] if len(main) else cw.iloc[0]
        ui.interp(f"{top['Variable']} has the largest coefficient with yield in this selection (r = {top['Coefficient (r)']:+.3f}, "
                  f"{top['Strength']}, {top['Direction']}). This is an association between values; it is not evidence that "
                  f"{top['Variable'].lower()} causes yield to change.")
    if fdf["crop"].nunique() > 1:
        ui.note("Several crops are selected. Crops differ greatly in typical yield, which can strongly influence overall coefficients. "
                "Use the sidebar to filter to one crop and examine relationships within it.")

    ui.section("Scatter explorer", "Plot yield against one variable. The dashed line is a straight-line fit to all plotted records.")
    xs = [c for c in ("rainfall_mm", "temperature_c", "fertilizer_kg_ha", "land_area_ha") if c in fdf.columns and fdf[c].notna().sum() >= 3]
    if not xs:
        ui.empty_state("No variables to plot", "The loaded data has no numeric driver columns with enough values.")
        return
    x = st.selectbox("Variable on the horizontal axis", xs, format_func=config.label, key="sc_x")
    cmap = charts.color_map(df["crop"])
    r, n = stats.pair_correlation(fdf, x, method=method.lower())
    ui.kpi_grid([
        ("peak", f"{method} r", "n/a" if r != r else f"{r:+.2f}", "", "coefficient with yield"),
        ("yield", "Strength", stats.strength_label(r), "", stats.direction_label(r) + " association"),
        ("records", "Valid pairs", f"{n:,}", "", "records used"),
    ], "mini-grid")
    with ui.card():
        ui.plot(charts.scatter_vs_yield(fdf, x, cmap), "r_scatter")
        ui.interp(interpret.scatter(fdf, x))
