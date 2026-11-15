"""Smart Insights page: automatic observations and a chart advisor."""
from __future__ import annotations

import streamlit as st

from .. import advisor, charts, config, insights, ui


def render(df, fdf, active):
    ui.page_header("Smart Insights", "What the data says",
                   "Observations generated from calculations on the current selection, and charts recommended for the variables you choose.")
    ui.active_filters_chips(active)
    if not ui.require_records(fdf, 5):
        return
    items = insights.generate(fdf)
    ui.section("Automatic insights", "Every statement below comes from a calculation on the selected records. Correlation is not causation, "
                                      "and no statistical significance tests are run.")
    for kind, label in (("finding", "Findings"), ("caution", "Cautions"), ("info", "Context")):
        sub = [i for i in items if i.kind == kind]
        if not sub:
            continue
        st.markdown(f"**{label}**")
        for i in sub:
            ev = f'<div class="ev">Basis: {ui.esc(i.evidence)}</div>' if i.evidence else ""
            st.markdown(f'<div class="insight {i.kind}"><div class="it">{ui.esc(i.title)}</div><div class="tx">{ui.esc(i.text)}</div>{ev}</div>', unsafe_allow_html=True)
    st.download_button("Download insights (Markdown)", insights.as_markdown(items).encode("utf-8"), "insights.md", "text/markdown",
                       on_click=ui.notify_cb("Export completed: insights.md"), key="sm_dl")

    ui.section("Visualization advisor", "Choose one or two variables. Only charts that can meaningfully show them are offered.")
    cols = advisor.usable_columns(fdf)
    a, b = st.columns(2)
    x = a.selectbox("Variable", cols, index=cols.index("yield_t_ha") if "yield_t_ha" in cols else 0, format_func=config.label, key="adv_x")
    ychoices = [None] + [c for c in cols if c != x]
    y = b.selectbox("Compare with (optional)", ychoices, format_func=lambda c: "None (single variable)" if c is None else config.label(c), key="adv_y")
    recs = advisor.recommend(fdf, x, y)
    if not recs:
        ui.empty_state("No suitable chart", "These variables cannot be shown together in a meaningful chart. Try a different pair.")
        return
    pick = st.radio("Recommended charts", [r.chart for r in recs], horizontal=True, key="adv_pick")
    why = next(r.reason for r in recs if r.chart == pick)
    cmap = charts.color_map(df["crop"])
    try:
        fig = advisor.build(fdf, x, y, pick, cmap)
    except ValueError as e:
        ui.empty_state("This chart cannot be drawn", f"The selected records do not support it ({e}).")
        return
    with ui.card():
        ui.plot(fig, "adv_chart")
        ui.interp(why)
    st.download_button("Download this chart (interactive HTML)", fig.to_html(include_plotlyjs="cdn").encode("utf-8"), "chart.html", "text/html",
                       on_click=ui.notify_cb("Export completed: chart.html"), key="adv_dl")
