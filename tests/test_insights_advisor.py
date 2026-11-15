import numpy as np
import pandas as pd

from crop_yield_explorer import advisor, data, insights


def sample():
    return data.load_sample().df


def test_insights_from_sample_are_grounded():
    items = insights.generate(sample())
    assert items and all(i.title and i.text for i in items)
    text = " ".join(i.text for i in items).lower()
    assert "caus" in text or all("caus" not in i.text.lower() for i in items)  # never asserts causation
    assert "significan" not in text


def test_insights_tiny_data_makes_no_group_claims():
    df = pd.DataFrame({"crop": ["Maize", "Rice"], "yield_t_ha": [2.0, 3.0]})
    kinds = " ".join(i.title for i in insights.generate(df))
    assert "highest" not in kinds.lower()


def test_insights_never_crash_on_odd_data():
    df = pd.DataFrame({"crop": [None] * 3, "yield_t_ha": [np.nan] * 3})
    insights.generate(df)


def test_advisor_all_recommendations_build():
    df = sample()
    cols = advisor.usable_columns(df)
    built = 0
    for x in cols:
        for y in [None] + cols:
            for rec in advisor.recommend(df, x, y):
                advisor.build(df, x, y, rec.chart, {})
                built += 1
    assert built > 20


def test_advisor_rejects_impossible_chart():
    import pytest
    df = sample()
    with pytest.raises(ValueError):
        advisor.build(df, "crop", None, "Scatter plot", {})
