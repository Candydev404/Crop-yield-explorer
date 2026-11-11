"""Statistics page: descriptive statistics, group summaries and correlation analysis."""
from __future__ import annotations

import streamlit as st

from .. import config, interpret, stats, ui

FMT = {c: "{:,.2f}" for c in ["Mean", "Median", "Minimum", "Maximum", "Std. deviation",
                              "Mean yield", "Median yield", "Min yield", "Max yield", "Total production (t)"]}


def render(df, fdf, active, synthetic, source):
    ui.header("Statistical Analysis", "Descriptive statistics, group comparisons and correlation analysis.", synthetic)
    st.caption("Active filters: " + ("; ".join(active) if active else "none"))
    if not ui.require_records(fdf):
        return
    st.markdown("## Descriptive statistics")
    st.dataframe(stats.describe_numeric(fdf).style.format(FMT, na_rep="n/a"), hide_index=True, width="stretch")
    st.caption("Count excludes missing values. Standard deviation is the sample standard deviation (n - 1).")

    st.markdown("## Yield by group")
    opts = [c for c in config.CATEGORY_COLUMNS if c in fdf.columns and fdf[c].notna().any()]
    by = st.selectbox("Group by", opts, format_func=lambda c: config.label(c, False), key="grp_by")
    st.dataframe(stats.group_summary(fdf, by).style.format(FMT, na_rep="n/a"), hide_index=True, width="stretch")

    st.markdown("## Correlation analysis")
    ui.note("<br>".join("&bull; " + p.replace("**", "") for p in interpret.CAUSATION_POINTS), "caution")
    method = st.radio("Method", ["Pearson", "Spearman"], horizontal=True, key="st_method",
                      help="Pearson measures linear association; Spearman measures rank (monotonic) association.")
    cw = stats.correlations_with_yield(fdf, method.lower())
    if cw.empty:
        st.warning("Correlations cannot be calculated: too few records, or the variables do not vary.")
    else:
        st.markdown("**Association of each variable with crop yield**")
        st.dataframe(cw.style.format({"Coefficient (r)": "{:+.3f}"}), hide_index=True, width="stretch")
        if cw["Variable"].str.startswith("Total production").any():
            st.caption("Total production is calculated from yield and land area, so its coefficient with yield reflects "
                       "that arithmetic relationship and is not a finding about agricultural drivers.")
        cw_main = cw[~cw["Variable"].str.startswith("Total production")]
        top = cw_main.iloc[0] if len(cw_main) else cw.iloc[0]
        ui.interp(f"{top['Variable']} has the largest coefficient with yield in this selection (r = {top['Coefficient (r)']:+.3f}, "
                  f"{top['Strength']}, {top['Direction']}). This is an association between values; it is not evidence that "
                  f"{top['Variable'].lower()} causes yield to change.")
    if fdf["crop"].nunique() > 1:
        ui.note("Several crops are selected. Crops differ greatly in typical yield, which can strongly influence overall "
                "coefficients. Filter to one crop to examine relationships within it.")
    with st.expander("Full correlation matrix"):
        avail = [c for c in config.CORRELATION_COLUMNS if c in fdf.columns]
        m = stats.correlation_matrix(fdf, avail, method.lower())
        if m.empty:
            st.write("Not available.")
        else:
            m = m.rename(index=config.label, columns=config.label)
            st.dataframe(m.style.format("{:.3f}", na_rep="n/a").background_gradient(cmap="RdBu_r", vmin=-1, vmax=1),
                         width="stretch")
