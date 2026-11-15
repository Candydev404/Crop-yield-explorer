"""Smart insights: plain-language observations computed from the loaded records.

Every sentence is generated from a real calculation. No significance tests are run, so no finding is described as
"significant"; correlations are always described as associations, never as causes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config, stats

MIN_GROUP = 5          # smallest group (records) that may be named best or worst
MIN_PAIRS = 10         # fewest valid pairs for a correlation to be reported


@dataclass(frozen=True)
class Insight:
    kind: str       # "finding", "caution" or "info"
    title: str
    text: str
    evidence: str   # the numbers behind the sentence, so it can be checked


def _group_means(df: pd.DataFrame, by: str) -> pd.DataFrame | None:
    if by not in df.columns or "yield_t_ha" not in df.columns:
        return None
    g = df.groupby(by)["yield_t_ha"].agg(["mean", "count"]).reset_index()
    g = g[g["count"] >= MIN_GROUP]
    return g if len(g) >= 2 else None


def _crop_yield(df):
    out = []
    g = _group_means(df, "crop")
    if g is None:
        return [Insight("info", "Crop comparison", f"Crop yields cannot be ranked reliably: at least two crops with {MIN_GROUP}+ records each are needed.", "")]
    hi, lo = g.loc[g["mean"].idxmax()], g.loc[g["mean"].idxmin()]
    out.append(Insight("finding", "Highest average yield",
                       f"{hi['crop']} recorded the highest average yield among the selected crops ({hi['mean']:.2f} t/ha).",
                       f"{int(hi['count'])} records; {len(g)} crops compared"))
    out.append(Insight("finding", "Lowest average yield",
                       f"{lo['crop']} recorded the lowest average yield ({lo['mean']:.2f} t/ha).", f"{int(lo['count'])} records"))
    if lo["mean"] > 0:
        out.append(Insight("info", "Spread between crops",
                           f"The highest crop average is {hi['mean'] / lo['mean']:.1f} times the lowest. Crops are naturally measured on "
                           "different scales, so compare like with like.", f"{hi['mean']:.2f} vs {lo['mean']:.2f} t/ha"))
    return out


def _region(df):
    out = []
    if "region" in df.columns and "production_tonnes" in df.columns and df["production_tonnes"].notna().any():
        p = df.groupby("region")["production_tonnes"].sum().sort_values(ascending=False)
        if len(p) >= 2:
            share = p.iloc[0] / p.sum() * 100
            out.append(Insight("finding", "Highest regional production",
                               f"{p.index[0]} had the highest total production ({p.iloc[0]:,.0f} t, {share:.1f}% of the selected total).",
                               f"{len(p)} regions"))
    g = _group_means(df, "region")
    if g is not None:
        r = g.loc[g["mean"].idxmax()]
        out.append(Insight("finding", "Highest regional yield", f"{r['region']} had the highest average yield across the selected records "
                           f"({r['mean']:.2f} t/ha). Region averages mix different crops.", f"{int(r['count'])} records"))
    return out


def _relationships(df):
    out = []
    rows = []
    for col in ("rainfall_mm", "temperature_c", "fertilizer_kg_ha", "land_area_ha"):
        if col in df.columns:
            r, n = stats.pair_correlation(df, col)
            if n >= MIN_PAIRS and r == r:
                rows.append((col, r, n))
    if not rows:
        return [Insight("info", "Relationships", f"No variable has at least {MIN_PAIRS} valid pairs with yield, so relationships are not reported.", "")]
    for col, r, n in rows:
        lab = config.COLUMNS[col]["label"].lower()
        strength = stats.strength_label(r)
        if strength == "negligible":
            txt = f"{lab.capitalize()} and crop yield show almost no linear relationship in the selected data (r = {r:+.2f})."
        else:
            d = "positive" if r > 0 else "negative"
            txt = f"{lab.capitalize()} and crop yield show a {strength} {d} correlation in the selected data (r = {r:+.2f})."
        out.append(Insight("finding", f"{config.COLUMNS[col]['label']} and yield", txt + " This is an association between values, not evidence that one causes the other.",
                           f"Pearson r, {n} valid pairs"))
    top = max(rows, key=lambda t: abs(t[1]))
    out.append(Insight("info", "Strongest observed relationship",
                       f"Among the driver variables, {config.COLUMNS[top[0]]['label'].lower()} has the largest coefficient with yield (r = {top[1]:+.2f}).",
                       f"{top[2]} valid pairs"))
    if "crop" in df.columns and df["crop"].nunique() > 1:
        out.append(Insight("caution", "Mixed crops",
                           "Several crops are selected. Crops differ in typical yield, which can strengthen or weaken overall coefficients. "
                           "Filter to one crop to check each relationship within that crop.", ""))
    return out


def _outliers(df):
    s = df["yield_t_ha"].dropna() if "yield_t_ha" in df.columns else pd.Series(dtype=float)
    if len(s) < 20:
        return [Insight("info", "Outliers", "Fewer than 20 yield values are selected, so unusual values are not assessed.", "")]
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (df["yield_t_ha"] < lo) | (df["yield_t_ha"] > hi)
    n = int(mask.sum())
    if n == 0:
        return [Insight("finding", "Unusual values", "No yield value lies outside the usual range (1.5 x IQR rule).", f"range {lo:.2f} to {hi:.2f} t/ha")]
    by = df.loc[mask, "crop"].value_counts() if "crop" in df.columns else pd.Series(dtype=int)
    extra = f" Most belong to {by.index[0]} ({int(by.iloc[0])})." if len(by) else ""
    txt = (f"{n} of {len(s)} yield values ({n / len(s) * 100:.1f}%) lie outside the usual range by the 1.5 x IQR rule.{extra} "
           "Outliers are flagged for review, not removed: they may be genuine, for example a high-yielding crop in a mixed selection.")
    return [Insight("finding", "Unusual values", txt, f"range {lo:.2f} to {hi:.2f} t/ha")]


def _distribution(df):
    s = df["yield_t_ha"].dropna() if "yield_t_ha" in df.columns else pd.Series(dtype=float)
    if len(s) < 20:
        return []
    sk = float(s.skew())
    shape = "roughly symmetric" if abs(sk) < 0.5 else ("skewed to the right (a tail of high yields)" if sk > 0 else "skewed to the left (a tail of low yields)")
    return [Insight("finding", "Yield distribution",
                    f"Yield is {shape}: the mean is {s.mean():.2f} t/ha and the median {s.median():.2f} t/ha.", f"skewness {sk:+.2f}, {len(s)} values")]


def _trend(df):
    if "year" not in df.columns or df["year"].dropna().nunique() < 3:
        return []
    g = df.dropna(subset=["year"]).groupby("year")["yield_t_ha"].agg(["mean", "count"])
    first, last = g.iloc[0], g.iloc[-1]
    ch = last["mean"] - first["mean"]
    word = "higher" if ch > 0 else "lower"
    return [Insight("info", "Change over the years",
                    f"The average yield in {int(g.index[-1])} ({last['mean']:.2f} t/ha) is {abs(ch):.2f} t/ha {word} than in {int(g.index[0])} ({first['mean']:.2f} t/ha). "
                    "The mix of crops and regions differs between years, so this is not a measure of improvement.",
                    f"{int(first['count'])} and {int(last['count'])} records")]


def _quality(df):
    miss = df.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    if miss.empty:
        return [Insight("info", "Missing data", "No missing values in the selected records.", "")]
    top = ", ".join(f"{config.COLUMNS.get(c, {'label': c})['label']} ({int(v)})" for c, v in miss.head(3).items())
    return [Insight("caution", "Missing data", f"{int(miss.sum())} values are missing in {len(miss)} column(s), mainly {top}. "
                    "Calculations that need a missing value skip that record.", "")]


def generate(df: pd.DataFrame) -> list[Insight]:
    """All insights for the given records (already filtered by the caller)."""
    if df is None or len(df) == 0:
        return []
    out: list[Insight] = []
    for fn in (_crop_yield, _region, _relationships, _distribution, _outliers, _trend, _quality):
        try:
            out.extend(fn(df))
        except Exception as exc:  # never let one rule break the page
            out.append(Insight("info", "Insight unavailable", f"One analysis could not be completed ({type(exc).__name__}).", ""))
    return out


def as_markdown(items: list[Insight], heading: str = "Crop Yield Explorer: analytical insights") -> str:
    lines = [f"# {heading}", ""]
    for i in items:
        lines.append(f"- **{i.title}.** {i.text}" + (f" _({i.evidence})_" if i.evidence else ""))
    return "\n".join(lines) + "\n"
