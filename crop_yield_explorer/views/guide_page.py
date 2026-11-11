"""Guide page: how to use the application, correlation vs causation, limitations."""
from __future__ import annotations

import streamlit as st

from .. import interpret, ui


def render(df, fdf, active, synthetic, source):
    ui.header("Guide and Limitations", "How to use the explorer and how to read its results.", synthetic)
    st.markdown("## Using the application")
    st.markdown(
        "1. Choose **Sample dataset** or **Upload my own CSV** under *Data source* in the sidebar.\n"
        "2. Review the **Data** page for column types, missing values and validation messages.\n"
        "3. Narrow the records with the **Filters** in the sidebar. Every page updates immediately.\n"
        "4. Read the **Dashboard**, **Charts** and **Statistics** pages. Each chart has an interpretation beneath it."
    )
    st.markdown("## Correlation is not causation")
    for p in interpret.CAUSATION_POINTS:
        st.markdown(f"- {p}")
    ui.note("Example: if rainfall and yield show a positive correlation in a dataset, the data alone cannot show that more rain "
            "raised the yield. Crop choice, soil, planting date, pests, fertiliser and irrigation may all differ between records.")
    st.markdown("## About the sample dataset")
    st.markdown(
        "The bundled file `data/sample_crop_yield.csv` contains **720 synthetic records** (2015 to 2024, eight crops, six regions) "
        "produced by `scripts/generate_sample_data.py` with a fixed random seed. Yields follow simple assumed relationships plus "
        "random noise. A small number of values were deliberately removed to demonstrate missing-value handling. "
        "The data are for demonstration and teaching only."
    )
    st.markdown("## Limitations")
    st.markdown(
        "- Results describe only the records loaded; they are not forecasts or recommendations for any farm.\n"
        "- Correlations use pairwise complete observations; missing values are not imputed.\n"
        "- Filtering by narrow ranges leaves few records, which makes statistics unstable.\n"
        "- Uploaded files must use recognised column names (see the Data page, *Expected format*)."
    )
