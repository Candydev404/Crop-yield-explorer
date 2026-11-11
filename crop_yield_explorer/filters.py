"""Filtering logic (no Streamlit dependency)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config

NUMERIC_FILTERS = ["year", "rainfall_mm", "temperature_c", "fertilizer_kg_ha", "land_area_ha"]
CATEGORY_FILTERS = ["crop", "region", "season"]


@dataclass
class Criteria:
    """Selected filter values.

    ``categories`` maps a column to the list of selected values.
    ``ranges`` maps a column to (low, high) selected bounds.
    """

    categories: dict[str, list]
    ranges: dict[str, tuple[float, float]]


def nice_step(span: float) -> float:
    """Pick a slider step that gives roughly 100-200 positions."""
    if span <= 0:
        return 1.0
    target = span / 150
    for step in (0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50, 100):
        if step >= target:
            return float(step)
    return 100.0


def range_bounds(series: pd.Series, is_year: bool = False) -> tuple[float, float, float] | None:
    """Return (low, high, step) slider bounds covering the series, or None if not filterable."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    if is_year:
        lo, hi = int(s.min()), int(s.max())
        return (lo, hi, 1) if lo < hi else None
    step = nice_step(float(s.max() - s.min()))
    lo = math.floor(s.min() / step) * step
    hi = math.ceil(s.max() / step) * step
    lo, hi = round(lo, 4), round(hi, 4)
    return (lo, hi, step) if lo < hi else None


def apply_filters(df: pd.DataFrame, criteria: Criteria,
                  full_ranges: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """Apply the selected criteria.

    A numeric range equal to the full slider range is treated as 'not filtering', so
    records with missing values in that column are retained until the user narrows it.
    """
    mask = pd.Series(True, index=df.index)
    for col, selected in criteria.categories.items():
        if col in df.columns:
            mask &= df[col].isin(selected)
    for col, (lo, hi) in criteria.ranges.items():
        if col not in df.columns:
            continue
        full = full_ranges.get(col)
        if full is not None and (lo, hi) == tuple(full):
            continue
        vals = pd.to_numeric(df[col], errors="coerce")
        mask &= vals.between(lo, hi)
    return df[mask].reset_index(drop=True)


def describe_active(criteria: Criteria, df_all: pd.DataFrame,
                    full_ranges: dict[str, tuple[float, float]]) -> list[str]:
    """Human-readable list of filters that differ from the defaults."""
    parts = []
    for col, selected in criteria.categories.items():
        total = df_all[col].nunique()
        if len(selected) != total:
            shown = ", ".join(map(str, selected[:3])) + (" ..." if len(selected) > 3 else "")
            parts.append(f"{config.label(col, False)}: {shown or 'none selected'}")
    for col, (lo, hi) in criteria.ranges.items():
        full = full_ranges.get(col)
        if full is not None and (lo, hi) != tuple(full):
            fmt = "{:g}"
            parts.append(f"{config.label(col)}: {fmt.format(lo)} to {fmt.format(hi)}")
    return parts
