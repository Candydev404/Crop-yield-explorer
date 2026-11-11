"""Descriptive statistics and correlation analysis (no Streamlit dependency)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def kpis(df: pd.DataFrame) -> dict:
    """Headline figures for the dashboard."""
    out = {
        "records": int(len(df)),
        "crops": int(df["crop"].nunique()),
        "mean_yield": float(df["yield_t_ha"].mean()) if len(df) else float("nan"),
        "total_production": float(df["production_tonnes"].sum()) if "production_tonnes" in df.columns and df["production_tonnes"].notna().any() else None,
        "max_yield": float(df["yield_t_ha"].max()) if len(df) else float("nan"),
        "max_yield_crop": None,
        "max_yield_region": None,
    }
    if len(df):
        row = df.loc[df["yield_t_ha"].idxmax()]
        out["max_yield_crop"] = row["crop"]
        if "region" in df.columns:
            out["max_yield_region"] = row["region"]
    return out


def describe_numeric(df: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    """Count, missing, mean, median, min, max, standard deviation for numeric columns."""
    cols = cols or [c for c in config.NUMERIC_COLUMNS if c in df.columns and c != "year"]
    rows = []
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce").astype(float)
        rows.append({
            "Variable": config.label(c),
            "Count": int(s.count()),
            "Missing": int(s.isna().sum()),
            "Mean": s.mean(),
            "Median": s.median(),
            "Minimum": s.min(),
            "Maximum": s.max(),
            "Std. deviation": s.std(ddof=1),
        })
    return pd.DataFrame(rows)


def group_summary(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Yield statistics (and production total) per group."""
    g = df.groupby(by, dropna=True, observed=True)
    out = g["yield_t_ha"].agg(["count", "mean", "median", "min", "max", "std"])
    out.columns = ["Records", "Mean yield", "Median yield", "Min yield", "Max yield", "Std. deviation"]
    if "production_tonnes" in df.columns:
        out["Total production (t)"] = g["production_tonnes"].sum(min_count=1)
    out = out.reset_index().rename(columns={by: config.label(by, False)})
    return out.sort_values("Mean yield", ascending=False).reset_index(drop=True)


def correlation_matrix(df: pd.DataFrame, cols: list[str], method: str = "pearson") -> pd.DataFrame:
    """Pairwise correlation matrix using complete pairs; constant columns are dropped."""
    use = [c for c in cols if c in df.columns]
    data = df[use].apply(pd.to_numeric, errors="coerce").astype(float)
    data = data.loc[:, data.nunique(dropna=True) > 1]
    if data.shape[1] < 2:
        return pd.DataFrame()
    return data.corr(method=method, min_periods=3)


def strength_label(r: float) -> str:
    """Conventional wording for the magnitude of a correlation coefficient."""
    if r is None or np.isnan(r):
        return "not available"
    a = abs(r)
    if a < 0.1:
        return "negligible"
    if a < 0.3:
        return "weak"
    if a < 0.5:
        return "moderate"
    if a < 0.7:
        return "strong"
    return "very strong"


def direction_label(r: float) -> str:
    if r is None or np.isnan(r):
        return "-"
    if abs(r) < 0.1:
        return "none apparent"
    return "positive" if r > 0 else "negative"


def correlations_with_yield(df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """Rank the association of each numeric variable with yield."""
    rows = []
    for c in config.CORRELATION_COLUMNS:
        if c == "yield_t_ha" or c not in df.columns:
            continue
        pair = df[["yield_t_ha", c]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(pair) < 3 or pair[c].nunique() < 2 or pair["yield_t_ha"].nunique() < 2:
            continue
        r = pair["yield_t_ha"].corr(pair[c], method=method)
        rows.append({
            "Variable": config.label(c), "Coefficient (r)": round(float(r), 3),
            "Direction": direction_label(r), "Strength": strength_label(r), "Pairs (n)": len(pair),
            "_abs": abs(r),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("_abs", ascending=False).drop(columns="_abs").reset_index(drop=True)


def pair_correlation(df: pd.DataFrame, x: str, y: str = "yield_t_ha", method: str = "pearson"):
    """Return (r, n) for two columns, or (nan, n) when it cannot be computed."""
    if x not in df.columns or y not in df.columns:
        return float("nan"), 0
    pair = df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(pair) < 3 or pair[x].nunique() < 2 or pair[y].nunique() < 2:
        return float("nan"), len(pair)
    return float(pair[x].corr(pair[y], method=method)), len(pair)
