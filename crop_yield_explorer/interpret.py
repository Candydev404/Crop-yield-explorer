"""Plain-language interpretation text generated from the filtered data.

All wording describes statistical association only. No sentence claims that one
variable causes another.
"""
from __future__ import annotations

import pandas as pd

from . import config, stats

CAUSATION_POINTS = [
    "**Correlation** describes the strength and direction of a statistical relationship between two variables.",
    "A **positive** correlation does not establish that one variable causes the other to rise.",
    "A **negative** correlation does not establish that one variable causes the other to fall.",
    "Other agricultural, environmental and management factors (for example crop type, soil, "
    "pests, variety, planting date, irrigation and labour) may influence crop yield and may also be "
    "related to the variable being examined.",
]


def yield_by_crop(df: pd.DataFrame) -> str:
    g = df.groupby("crop")["yield_t_ha"].mean().sort_values()
    if len(g) < 2:
        return f"Only one crop ({g.index[0]}) is selected; its mean yield is {g.iloc[0]:.2f} t/ha."
    return (f"Among the selected records, **{g.index[-1]}** has the highest mean yield ({g.iloc[-1]:.2f} t/ha) "
            f"and **{g.index[0]}** the lowest ({g.iloc[0]:.2f} t/ha). Root and tuber crops are normally "
            "reported on a much larger tonnes-per-hectare scale than cereals and legumes, so compare crops "
            "of the same type where possible.")


def production(df: pd.DataFrame) -> str:
    g = df.groupby("crop")["production_tonnes"].sum().sort_values(ascending=False)
    total = g.sum()
    if total <= 0 or g.empty:
        return "No production values are available for the selected records."
    top = g.index[0]
    return (f"**{top}** accounts for {g.iloc[0] / total * 100:.1f}% of the {total:,.1f} tonnes recorded in the "
            "selection. Production depends on both yield and the area planted, so a crop can rank high "
            "because it is grown on many or large plots, not only because its yield is high.")


def scatter(df: pd.DataFrame, x: str) -> str:
    r, n = stats.pair_correlation(df, x)
    name = config.COLUMNS[x]["label"].lower()
    if n < 3 or pd.isna(r):
        return "There are too few valid pairs of values to describe a relationship."
    strength = stats.strength_label(r)
    if strength == "negligible":
        kind = "a **negligible** association (close to no linear relationship)"
    else:
        kind = f"a **{strength} {stats.direction_label(r)}** association"
    text = f"Across {n:,} records the Pearson correlation between {name} and yield is **r = {r:+.2f}**, {kind}."
    if df["crop"].nunique() > 1:
        text += (" Several crop types are included, and crops differ greatly in typical yield, so this "
                 "overall figure partly reflects differences between crops. Filter to a single crop to "
                 "see the relationship within that crop.")
    text += " This describes how the values move together; it does not show that a change in "
    text += f"{name} causes a change in yield."
    return text


def region(df: pd.DataFrame) -> str:
    g = df.groupby("region")["yield_t_ha"].mean().sort_values()
    if len(g) < 2:
        return f"Only one region ({g.index[0]}) is selected."
    mix = ""
    if df["crop"].nunique() > 1:
        mix = (" Regional means are influenced by which crops were recorded in each region (the crop mix); "
               "see the crop-by-region chart below.")
    return (f"The highest mean yield is in **{g.index[-1]}** ({g.iloc[-1]:.2f} t/ha) and the lowest in "
            f"**{g.index[0]}** ({g.iloc[0]:.2f} t/ha).{mix}")


def distribution(df: pd.DataFrame) -> str:
    s = df["yield_t_ha"]
    skew = s.skew() if len(s) > 2 else float("nan")
    shape = ""
    if pd.notna(skew):
        if skew > 0.5:
            shape = " The distribution is skewed to the right: most records have lower yields and a smaller number have high yields."
        elif skew < -0.5:
            shape = " The distribution is skewed to the left."
        else:
            shape = " The distribution is roughly symmetric."
    return (f"Yield ranges from {s.min():.2f} to {s.max():.2f} t/ha with a mean of {s.mean():.2f} and a "
            f"median of {s.median():.2f} t/ha.{shape} When several crops are selected, the distribution can show "
            "more than one peak because crops have different typical yields.")


def trend(df: pd.DataFrame) -> str:
    g = df.dropna(subset=["year"]).groupby("year")["yield_t_ha"].mean()
    if len(g) < 2:
        return ""
    return (f"Mean yield was {g.iloc[0]:.2f} t/ha in {int(g.index[0])} and {g.iloc[-1]:.2f} t/ha in "
            f"{int(g.index[-1])}. Year-to-year movement also reflects changes in which crops and regions are "
            "present in each year's records.")


def heatmap(corr: pd.DataFrame, df: pd.DataFrame) -> str:
    if corr.empty:
        return "A correlation matrix cannot be calculated for the current selection."
    note = ("Coefficients range from -1 (perfect negative) through 0 (no linear relationship) to +1 "
            "(perfect positive). Only the lower triangle is shown. ")
    if "production_tonnes" in corr.columns and "land_area_ha" in corr.columns:
        note += ("Production is calculated from yield and land area, so correlations involving production "
                 "partly reflect that arithmetic relationship. ")
    if df["crop"].nunique() > 1:
        note += "Several crops are selected, so some coefficients mix differences between crops with differences within crops."
    return note
