"""Visualization advisor: recommends chart types for a chosen pair of variables and builds them."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from . import charts, config


@dataclass(frozen=True)
class Recommendation:
    chart: str
    reason: str


def kind_of(df: pd.DataFrame, col: str) -> str:
    """'time', 'category' or 'number' for a column; unusable columns return 'none'."""
    if col not in df.columns or df[col].dropna().empty:
        return "none"
    k = config.COLUMNS.get(col, {}).get("kind")
    if k == "year":
        return "time"
    if k == "category":
        return "category"
    if k == "numeric":
        return "number"
    return "none"


def usable_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in config.COLUMNS if kind_of(df, c) != "none"]


def recommend(df: pd.DataFrame, x: str, y: str | None) -> list[Recommendation]:
    """Charts that can meaningfully show the chosen variables. An empty list means none are suitable."""
    kx = kind_of(df, x)
    ky = kind_of(df, y) if y else None
    if kx == "none" or (y and ky == "none"):
        return []
    if y is None or y == x:
        if kx == "number":
            return [Recommendation("Histogram", "Shows how the values of one numeric variable are distributed."),
                    Recommendation("Box plot", "Shows the median, quartiles and unusual values.")]
        if kx == "category":
            return [Recommendation("Bar chart of counts", "Shows how many records fall in each category.")]
        return [Recommendation("Bar chart of counts", "Shows how many records exist for each year.")]
    pair = {kx, ky}
    if pair == {"number"}:
        return [Recommendation("Scatter plot", "Shows whether two numeric variables move together, one point per record.")]
    if pair == {"category", "number"}:
        return [Recommendation("Bar chart of means", "Compares the average of the numeric variable across categories."),
                Recommendation("Box plot", "Compares the spread and unusual values across categories.")]
    if pair == {"time", "number"} or pair == {"time", "number", "category"}:
        return [Recommendation("Line chart over time", "Shows how the average of the numeric variable changes by year."),
                Recommendation("Scatter plot", "Shows every record against the year.")]
    if pair == {"category"} or pair == {"category", "time"}:
        return [Recommendation("Count heatmap", "Shows how many records fall in each combination of the two variables.")]
    return []


def _num(df, c):
    return pd.to_numeric(df[c], errors="coerce")


def build(df: pd.DataFrame, x: str, y: str | None, chart: str, cmap: dict) -> go.Figure:
    """Build the recommended chart. Raises ValueError when the data cannot support it."""
    lx = config.label(x)
    ly = config.label(y) if y else ""
    if chart in ("Histogram", "Box plot") and (y is None or y == x):
        s = _num(df, x).dropna()
        if s.empty:
            raise ValueError("no numeric values")
        if chart == "Histogram":
            fig = go.Figure(go.Histogram(x=s, nbinsx=30, marker_color=config.GREEN,
                                         hovertemplate=f"{lx}: %{{x}}<br>Records: %{{y}}<extra></extra>"))
            return charts._style(fig, f"Distribution of {config.COLUMNS[x]['label'].lower()}", lx, "Number of records", legend=False)
        fig = go.Figure(go.Box(x=s, marker_color=config.GREEN, boxmean=True, name=""))
        return charts._style(fig, f"Spread of {config.COLUMNS[x]['label'].lower()}", lx, None, height=260, legend=False)
    if chart == "Bar chart of counts":
        vc = df[x].dropna().value_counts().sort_index() if kind_of(df, x) == "time" else df[x].dropna().value_counts().sort_values()
        fig = go.Figure(go.Bar(x=vc.index.astype(str) if kind_of(df, x) == "time" else vc.values,
                               y=vc.values if kind_of(df, x) == "time" else vc.index.astype(str),
                               orientation="v" if kind_of(df, x) == "time" else "h", marker_color=config.GREEN))
        horiz = kind_of(df, x) != "time"
        return charts._style(fig, f"Number of records by {config.COLUMNS[x]['label'].lower()}",
                             "Number of records" if horiz else lx, lx if horiz else "Number of records", legend=False)
    if y is None:
        raise ValueError("a second variable is needed")
    kx, ky = kind_of(df, x), kind_of(df, y)
    cat, num = (x, y) if kx == "category" else (y, x)
    if chart == "Scatter plot":
        if kx == "number" and ky == "number":
            return charts.scatter_xy(df, x, y, cmap)
        t, n = (x, y) if kx == "time" else (y, x)
        return charts.scatter_xy(df, t, n, cmap)
    if chart == "Bar chart of means":
        g = df.groupby(cat)[num].agg(["mean", "count"]).reset_index().sort_values("mean")
        fig = go.Figure(go.Bar(x=g["mean"], y=g[cat], orientation="h", marker_color=config.GREEN, customdata=g["count"],
                               hovertemplate=f"<b>%{{y}}</b><br>Mean: %{{x:.2f}}<br>Records: %{{customdata}}<extra></extra>"))
        return charts._style(fig, f"Mean {config.COLUMNS[num]['label'].lower()} by {config.COLUMNS[cat]['label'].lower()}",
                             f"Mean {config.label(num)}", config.COLUMNS[cat]["label"], height=max(300, 42 * len(g) + 120), legend=False)
    if chart == "Box plot":
        fig = px.box(df, x=cat, y=num, color=cat, color_discrete_map=cmap if cat == "crop" else None,
                     color_discrete_sequence=config.CATEGORICAL)
        fig.update_traces(hovertemplate="%{x}<br>%{y}<extra></extra>")
        return charts._style(fig, f"{config.COLUMNS[num]['label']} by {config.COLUMNS[cat]['label'].lower()}",
                             config.COLUMNS[cat]["label"], config.label(num), legend=False)
    if chart == "Line chart over time":
        t, n = (x, y) if kx == "time" else (y, x)
        g = df.dropna(subset=[t]).groupby(t)[n].agg(["mean", "count"]).reset_index()
        fig = go.Figure(go.Scatter(x=g[t].astype(int), y=g["mean"], mode="lines+markers", line=dict(color=config.GREEN, width=2.5),
                                   customdata=g["count"], hovertemplate="%{x}<br>Mean: %{y:.2f}<br>Records: %{customdata}<extra></extra>"))
        fig = charts._style(fig, f"Mean {config.COLUMNS[n]['label'].lower()} by year", "Year", f"Mean {config.label(n)}", height=340, legend=False)
        fig.update_xaxes(dtick=1)
        return fig
    if chart == "Count heatmap":
        ct = pd.crosstab(df[y], df[x])
        fig = go.Figure(go.Heatmap(z=ct.values, x=[str(c) for c in ct.columns], y=[str(i) for i in ct.index], colorscale=charts.SEQ_GREEN,
                                   xgap=2, ygap=2, hovertemplate="%{y} and %{x}<br>Records: %{z}<extra></extra>"))
        return charts._style(fig, f"Records by {config.COLUMNS[y]['label'].lower()} and {config.COLUMNS[x]['label'].lower()}",
                             config.COLUMNS[x]["label"], config.COLUMNS[y]["label"], legend=False)
    raise ValueError(f"unsupported chart: {chart}")
