"""Chart builders. Plotly figures for interactive charts; Seaborn for the heatmap."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import seaborn as sns

from . import config

FONT = "Source Sans Pro, Segoe UI, Arial, sans-serif"
AXIS_COLOR = "#C9CFC8"
TEXT_COLOR = "#1F2A24"


def color_map(values) -> dict[str, str]:
    """Stable colour per category, based on the sorted list of all values."""
    vals = sorted({str(v) for v in values if pd.notna(v)})
    return {v: config.CATEGORICAL[i % len(config.CATEGORICAL)] for i, v in enumerate(vals)}


def _style(fig: go.Figure, title: str, xtitle: str | None = None, ytitle: str | None = None,
           height: int = 400, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", y=0.98, yanchor="top", font=dict(size=15, color=TEXT_COLOR)),
        template="simple_white", height=height,
        font=dict(family=FONT, size=12, color=TEXT_COLOR),
        margin=dict(l=10, r=10, t=95 if legend else 55, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        hoverlabel=dict(font_family=FONT),
    )
    fig.update_xaxes(title=xtitle, gridcolor="#E7EBE5", linecolor=AXIS_COLOR, automargin=True)
    fig.update_yaxes(title=ytitle, gridcolor="#E7EBE5", linecolor=AXIS_COLOR, automargin=True)
    return fig


def yield_by_crop(df: pd.DataFrame) -> go.Figure:
    g = df.groupby("crop")["yield_t_ha"].agg(["mean", "std", "count"]).reset_index()
    g = g.sort_values("mean")
    fig = go.Figure(go.Bar(
        x=g["mean"], y=g["crop"], orientation="h", marker_color=config.GREEN,
        error_x=dict(type="data", array=g["std"].fillna(0), color="#7C877E", thickness=1.2, width=3),
        customdata=np.stack([g["std"].fillna(0), g["count"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>Mean yield: %{x:.2f} t/ha<br>Std. deviation: %{customdata[0]:.2f}"
                      "<br>Records: %{customdata[1]}<extra></extra>",
    ))
    return _style(fig, "Mean crop yield by crop type", "Mean yield (t/ha); bars show ±1 std. deviation",
                  "Crop type", height=max(320, 42 * len(g) + 120), legend=False)


def production_by_crop(df: pd.DataFrame, cmap: dict) -> go.Figure:
    g = df.groupby("crop")["production_tonnes"].sum().reset_index()
    g = g.sort_values("production_tonnes")
    total = g["production_tonnes"].sum()
    g["share"] = g["production_tonnes"] / total * 100 if total else 0
    fig = go.Figure(go.Bar(
        x=g["production_tonnes"], y=g["crop"], orientation="h",
        marker_color=[cmap.get(c, config.GREEN) for c in g["crop"]],
        customdata=g["share"],
        text=[f"{s:.1f}%" for s in g["share"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Total production: %{x:,.1f} tonnes<br>Share: %{customdata:.1f}%<extra></extra>",
    ))
    fig = _style(fig, "Distribution of total production by crop type",
                 "Total production (tonnes); labels show share of total", "Crop type",
                 height=max(320, 42 * len(g) + 120), legend=False)
    fig.update_xaxes(range=[0, float(g["production_tonnes"].max()) * 1.15])
    return fig


def scatter_vs_yield(df: pd.DataFrame, x: str, cmap: dict) -> go.Figure:
    d = df[["crop", x, "yield_t_ha"]].copy()
    d[x] = pd.to_numeric(d[x], errors="coerce")
    d = d.dropna()
    fig = go.Figure()
    for crop, sub in d.groupby("crop"):
        fig.add_trace(go.Scatter(
            x=sub[x], y=sub["yield_t_ha"], mode="markers", name=str(crop),
            marker=dict(size=7, color=cmap.get(crop, config.GREY), opacity=0.75,
                        line=dict(width=0.5, color="white")),
            hovertemplate=f"<b>{crop}</b><br>{config.label(x)}: %{{x:,.1f}}<br>Yield: %{{y:.2f}} t/ha<extra></extra>",
        ))
    if len(d) >= 3 and d[x].nunique() > 1:
        slope, intercept = np.polyfit(d[x], d["yield_t_ha"], 1)
        xs = np.array([d[x].min(), d[x].max()])
        fig.add_trace(go.Scatter(
            x=xs, y=slope * xs + intercept, mode="lines", name="Linear fit (all plotted records)",
            line=dict(color="#222222", width=2, dash="dash"), hoverinfo="skip",
        ))
    return _style(fig, f"{config.COLUMNS[x]['label']} versus crop yield",
                  config.label(x), config.label("yield_t_ha"), height=430)


def region_yield(df: pd.DataFrame) -> go.Figure:
    g = df.groupby("region")["yield_t_ha"].agg(["mean", "std", "count"]).reset_index().sort_values("mean")
    fig = go.Figure(go.Bar(
        x=g["mean"], y=g["region"], orientation="h", marker_color=config.WHEAT,
        error_x=dict(type="data", array=g["std"].fillna(0), color="#7C877E", thickness=1.2, width=3),
        customdata=np.stack([g["std"].fillna(0), g["count"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>Mean yield: %{x:.2f} t/ha<br>Std. deviation: %{customdata[0]:.2f}"
                      "<br>Records: %{customdata[1]}<extra></extra>",
    ))
    return _style(fig, "Mean crop yield by region (all selected crops)",
                  "Mean yield (t/ha); bars show ±1 std. deviation", "Region",
                  height=max(300, 48 * len(g) + 120), legend=False)


def region_crop_heatmap(df: pd.DataFrame) -> go.Figure:
    pv = df.pivot_table(index="region", columns="crop", values="yield_t_ha", aggfunc="mean")
    cnt = df.pivot_table(index="region", columns="crop", values="yield_t_ha", aggfunc="count")
    fig = go.Figure(go.Heatmap(
        z=pv.values, x=list(pv.columns), y=list(pv.index),
        colorscale=[[0, "#F4F1E6"], [0.5, "#9CC5A1"], [1, "#1F4A28"]],
        colorbar=dict(title="t/ha"), customdata=cnt.reindex(index=pv.index, columns=pv.columns).values,
        hovertemplate="<b>%{y} – %{x}</b><br>Mean yield: %{z:.2f} t/ha<br>Records: %{customdata}<extra></extra>",
        xgap=2, ygap=2,
    ))
    return _style(fig, "Mean yield by region and crop type", "Crop type", "Region",
                  height=max(320, 50 * len(pv) + 140), legend=False)


def yield_distribution(df: pd.DataFrame, cmap: dict, by_crop: bool = False) -> go.Figure:
    if by_crop:
        fig = px.histogram(df, x="yield_t_ha", color="crop", color_discrete_map=cmap, nbins=30,
                           marginal="box", opacity=0.75)
        fig.update_layout(barmode="overlay")
    else:
        fig = px.histogram(df, x="yield_t_ha", nbins=30, marginal="box",
                           color_discrete_sequence=[config.GREEN])
    fig.update_traces(selector=dict(type="histogram"),
                      hovertemplate="Yield class: %{x} t/ha<br>Records: %{y}<extra></extra>")
    return _style(fig, "Distribution of crop yield", config.label("yield_t_ha"),
                  "Number of records", height=420, legend=by_crop)


def yield_trend(df: pd.DataFrame) -> go.Figure | None:
    if "year" not in df.columns or df["year"].dropna().nunique() < 2:
        return None
    g = df.dropna(subset=["year"]).groupby("year")["yield_t_ha"].agg(["mean", "count"]).reset_index()
    g["year"] = g["year"].astype(int)
    fig = go.Figure(go.Scatter(
        x=g["year"], y=g["mean"], mode="lines+markers", line=dict(color=config.GREEN, width=2.5),
        marker=dict(size=7), customdata=g["count"],
        hovertemplate="<b>%{x}</b><br>Mean yield: %{y:.2f} t/ha<br>Records: %{customdata}<extra></extra>",
    ))
    fig = _style(fig, "Mean crop yield by year", "Year", "Mean yield (t/ha)", height=360, legend=False)
    fig.update_xaxes(dtick=1)
    return fig


def correlation_heatmap(corr: pd.DataFrame, method_name: str = "Pearson"):
    """Seaborn heatmap of a correlation matrix (returns a Matplotlib figure)."""
    labels = [config.label(c) for c in corr.columns]
    fig, ax = plt.subplots(figsize=(8.2, 6.2), dpi=110)
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr.values, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, center=0,
        square=True, linewidths=0.6, linecolor="white", cbar_kws={"label": f"{method_name} correlation coefficient (r)", "shrink": 0.8},
        xticklabels=labels, yticklabels=labels, annot_kws={"size": 9}, ax=ax,
    )
    ax.set_title(f"Correlation matrix of numeric variables ({method_name})", loc="left", fontsize=12, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right", fontsize=9)
    plt.setp(ax.get_yticklabels(), rotation=0, fontsize=9)
    fig.tight_layout()
    return fig
