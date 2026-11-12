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

FONT = "Manrope, Inter, Segoe UI, Arial, sans-serif"
AXIS_COLOR = "#CBD3CC"
GRID_COLOR = "#E8ECE6"
TEXT_COLOR = config.CHARCOAL
MUTED = config.GREY
SEQ_GREEN = [[0, "#F3F6EE"], [0.35, "#CFE3D3"], [0.7, "#4F9C73"], [1, "#163B2D"]]
DIVERGING = [[0, "#B5532F"], [0.25, "#E7B79F"], [0.5, "#F8F7F1"], [0.75, "#8DBFA3"], [1, "#163B2D"]]


def color_map(values) -> dict[str, str]:
    """Stable colour per category, based on the sorted list of all values."""
    vals = sorted({str(v) for v in values if pd.notna(v)})
    return {v: config.CATEGORICAL[i % len(config.CATEGORICAL)] for i, v in enumerate(vals)}


def _style(fig: go.Figure, title: str, xtitle: str | None = None, ytitle: str | None = None,
           height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", y=0.98, yanchor="top",
                   font=dict(size=14, color=TEXT_COLOR, family=FONT)),
        template="simple_white", height=height,
        font=dict(family=FONT, size=12, color=TEXT_COLOR),
        margin=dict(l=6, r=10, t=92 if legend else 52, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="", font=dict(size=11)),
        hoverlabel=dict(font_family=FONT, font_size=12, bgcolor=config.EVERGREEN, font_color="#FFFFFF",
                        bordercolor=config.EVERGREEN),
    )
    fig.update_xaxes(title=dict(text=xtitle, font=dict(size=11, color=MUTED)), gridcolor=GRID_COLOR,
                     linecolor=AXIS_COLOR, zeroline=False, automargin=True, tickfont=dict(size=11, color=MUTED))
    fig.update_yaxes(title=dict(text=ytitle, font=dict(size=11, color=MUTED)), gridcolor=GRID_COLOR,
                     linecolor=AXIS_COLOR, zeroline=False, automargin=True, tickfont=dict(size=11, color=MUTED))
    return fig


def yield_by_crop(df: pd.DataFrame) -> go.Figure:
    g = df.groupby("crop")["yield_t_ha"].agg(["mean", "std", "count"]).reset_index()
    g = g.sort_values("mean")
    fig = go.Figure(go.Bar(
        x=g["mean"], y=g["crop"], orientation="h", marker_color=config.GREEN, marker_line_width=0,
        error_x=dict(type="data", array=g["std"].fillna(0), color="#7C877E", thickness=1.2, width=3),
        customdata=np.stack([g["std"].fillna(0), g["count"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>Mean yield: %{x:.2f} t/ha<br>Std. deviation: %{customdata[0]:.2f}"
                      "<br>Records: %{customdata[1]}<extra></extra>",
    ))
    return _style(fig, "Mean crop yield by crop type (error bars: ±1 SD)", "Mean yield (t/ha)",
                  "Crop type", height=max(320, 42 * len(g) + 120), legend=False)


def production_by_crop(df: pd.DataFrame, cmap: dict) -> go.Figure:
    g = df.groupby("crop")["production_tonnes"].sum().reset_index()
    g = g.sort_values("production_tonnes")
    total = g["production_tonnes"].sum()
    g["share"] = g["production_tonnes"] / total * 100 if total else 0
    fig = go.Figure(go.Bar(
        x=g["production_tonnes"], y=g["crop"], orientation="h",
        marker_color=config.GREEN, marker_line_width=0,
        customdata=g["share"],
        text=[f"{s:.1f}%" for s in g["share"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Total production: %{x:,.1f} tonnes<br>Share: %{customdata:.1f}%<extra></extra>",
    ))
    fig = _style(fig, "Distribution of total production by crop type",
                 "Total production (tonnes)", "Crop type",
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
            marker=dict(size=7, color=cmap.get(crop, config.GREY), opacity=0.78,
                        line=dict(width=0.5, color="white")),
            hovertemplate=f"<b>{crop}</b><br>{config.label(x)}: %{{x:,.1f}}<br>Yield: %{{y:.2f}} t/ha<extra></extra>",
        ))
    if len(d) >= 3 and d[x].nunique() > 1:
        slope, intercept = np.polyfit(d[x], d["yield_t_ha"], 1)
        xs = np.array([d[x].min(), d[x].max()])
        fig.add_trace(go.Scatter(
            x=xs, y=slope * xs + intercept, mode="lines", name="Linear fit (all plotted records)",
            line=dict(color=config.CHARCOAL, width=2, dash="dash"), hoverinfo="skip",
        ))
    return _style(fig, f"{config.COLUMNS[x]['label']} versus crop yield",
                  config.label(x), config.label("yield_t_ha"), height=430)


def region_yield(df: pd.DataFrame) -> go.Figure:
    g = df.groupby("region")["yield_t_ha"].agg(["mean", "std", "count"]).reset_index().sort_values("mean")
    fig = go.Figure(go.Bar(
        x=g["mean"], y=g["region"], orientation="h", marker_color="#1F4E5F", marker_line_width=0,
        error_x=dict(type="data", array=g["std"].fillna(0), color="#7C877E", thickness=1.2, width=3),
        customdata=np.stack([g["std"].fillna(0), g["count"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>Mean yield: %{x:.2f} t/ha<br>Std. deviation: %{customdata[0]:.2f}"
                      "<br>Records: %{customdata[1]}<extra></extra>",
    ))
    return _style(fig, "Mean crop yield by region (error bars: ±1 SD)",
                  "Mean yield (t/ha)", "Region",
                  height=max(300, 48 * len(g) + 120), legend=False)


def region_crop_heatmap(df: pd.DataFrame) -> go.Figure:
    pv = df.pivot_table(index="region", columns="crop", values="yield_t_ha", aggfunc="mean")
    cnt = df.pivot_table(index="region", columns="crop", values="yield_t_ha", aggfunc="count")
    fig = go.Figure(go.Heatmap(
        z=pv.values, x=list(pv.columns), y=list(pv.index),
        colorscale=SEQ_GREEN,
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
    fig = _style(fig, "Distribution of crop yield", config.label("yield_t_ha"),
                 "Number of records", height=400, legend=by_crop)
    fig.update_layout(xaxis2_title=None, yaxis2_title=None)
    fig.update_yaxes(showticklabels=False, row=2, col=1) if False else None
    return fig


def yield_trend(df: pd.DataFrame) -> go.Figure | None:
    if "year" not in df.columns or df["year"].dropna().nunique() < 2:
        return None
    g = df.dropna(subset=["year"]).groupby("year")["yield_t_ha"].agg(["mean", "count"]).reset_index()
    g["year"] = g["year"].astype(int)
    fig = go.Figure(go.Scatter(
        x=g["year"], y=g["mean"], mode="lines+markers", line=dict(color=config.GREEN, width=2.5), fill="tozeroy", fillcolor="rgba(40,122,82,0.10)",
        marker=dict(size=7, color=config.GREEN), customdata=g["count"],
        hovertemplate="<b>%{x}</b><br>Mean yield: %{y:.2f} t/ha<br>Records: %{customdata}<extra></extra>",
    ))
    fig = _style(fig, "Mean crop yield by year", "Year", "Mean yield (t/ha)", height=340, legend=False)
    fig.update_xaxes(dtick=1)
    return fig


def correlation_heatmap(corr: pd.DataFrame, method_name: str = "Pearson"):
    """Seaborn heatmap of a correlation matrix (returns a Matplotlib figure)."""
    labels = [config.label(c) for c in corr.columns]
    fig, ax = plt.subplots(figsize=(8.2, 6.2), dpi=110)
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr.values, mask=mask, annot=True, fmt=".2f", cmap=sns.blend_palette(["#B5532F", "#F8F7F1", "#163B2D"], as_cmap=True), vmin=-1, vmax=1, center=0,
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


def correlation_heatmap_interactive(corr: pd.DataFrame, method_name: str = "Pearson") -> go.Figure:
    """Interactive lower-triangle correlation heatmap (Plotly)."""
    labels = [config.label(c, False) for c in corr.columns]
    z = corr.values.astype(float).copy()
    z[np.triu_indices_from(z, k=1)] = np.nan
    text = np.where(np.isnan(z), "", np.char.mod("%.2f", np.nan_to_num(z)))
    fig = go.Figure(go.Heatmap(
        z=z, x=labels, y=labels, zmin=-1, zmax=1, zmid=0, colorscale=DIVERGING, xgap=2, ygap=2,
        text=text, texttemplate="%{text}", textfont=dict(size=9),
        colorbar=dict(title=dict(text=f"r ({method_name})", font=dict(size=11)), orientation="h", thickness=10, len=0.6, x=0.5, xanchor="center", y=-0.38, yanchor="top"),
        hovertemplate="<b>%{y}</b> and <b>%{x}</b><br>Correlation (r): %{z:.3f}<extra></extra>",
    ))
    fig = _style(fig, f"Correlation matrix of numeric variables ({method_name})", None, None,
                 height=max(460, 58 * len(labels) + 60), legend=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False, tickangle=-35)
    return fig


def correlation_bars(cw: pd.DataFrame, method_name: str = "Pearson") -> go.Figure:
    """Horizontal bars of each variable's correlation with yield (input: stats.correlations_with_yield)."""
    d = cw.iloc[::-1]
    colors = [config.GREEN if v >= 0 else "#B5532F" for v in d["Coefficient (r)"]]
    fig = go.Figure(go.Bar(
        x=d["Coefficient (r)"], y=d["Variable"], orientation="h", marker_color=colors, marker_line_width=0,
        text=[f"{v:+.2f}" for v in d["Coefficient (r)"]], textposition="outside", cliponaxis=False,
        customdata=np.stack([d["Strength"], d["Direction"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>r = %{x:+.3f}<br>%{customdata[0]}, %{customdata[1]}<extra></extra>",
    ))
    fig = _style(fig, "Association with crop yield",
                 f"{method_name} correlation (r)", None,
                 height=max(280, 46 * len(d) + 110), legend=False)
    fig.update_xaxes(range=[-1.1, 1.1], zeroline=True, zerolinecolor=AXIS_COLOR)
    return fig


def crop_vs_all(df_all: pd.DataFrame, crop: str) -> go.Figure:
    """Overlaid yield histograms: the selected crop against every other crop in the selection."""
    one = df_all.loc[df_all["crop"] == crop, "yield_t_ha"].dropna()
    rest = df_all.loc[df_all["crop"] != crop, "yield_t_ha"].dropna()
    fig = go.Figure()
    if len(rest):
        fig.add_trace(go.Histogram(x=rest, name="Other crops", marker_color="#C5CEC7", opacity=0.85, nbinsx=30,
                                   hovertemplate="Yield class: %{x} t/ha<br>Records: %{y}<extra>Other crops</extra>"))
    fig.add_trace(go.Histogram(x=one, name=str(crop), marker_color=config.GREEN, opacity=0.85, nbinsx=30,
                               hovertemplate="Yield class: %{x} t/ha<br>Records: %{y}<extra>" + str(crop) + "</extra>"))
    fig.update_layout(barmode="overlay", bargap=0.04)
    return _style(fig, f"Yield distribution: {crop} compared with other crops", config.label("yield_t_ha"),
                  "Number of records", height=360)


def variable_histogram(df: pd.DataFrame, col: str) -> go.Figure:
    """Histogram of one numeric variable with its mean marked."""
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    fig = go.Figure(go.Histogram(x=s, nbinsx=30, marker_color=config.GREEN, opacity=0.9,
                                 hovertemplate=config.COLUMNS[col]["label"] + ": %{x}<br>Records: %{y}<extra></extra>"))
    if len(s):
        fig.add_vline(x=float(s.mean()), line_dash="dash", line_color=config.CHARCOAL,
                      annotation_text=f"Mean {s.mean():,.2f}", annotation_position="top right")
    return _style(fig, f"Distribution of {config.COLUMNS[col]['label'].lower()}", config.label(col), "Number of records",
                  height=360, legend=False)
