"""
MONSOONAI dashboard — chart helpers (Phase 4)
===============================================
One consistent visual style for every chart: deep navy panels,
atmospheric blue, a single restrained cyan accent, readable axes and
units on every chart. No gradients, no decoration for its own sake.
"""

import plotly.graph_objects as go

# Palette — deep navy / charcoal, atmospheric blue, restrained cyan.
NAVY_BG = "#0b1220"
PANEL_BG = "#111a2e"
GRID = "#24344d"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
CYAN = "#38bdf8"
BLUE = "#60a5fa"
TEAL = "#2dd4bf"
AMBER = "#f59e0b"
RED = "#f87171"
GREEN = "#4ade80"


def base_layout(title, x_title, y_title, height=380):
    """Shared Plotly layout: dark panels, labelled axes, no clutter."""
    return dict(
        title=dict(text=title, font=dict(size=15, color=TEXT), x=0.01),
        xaxis=dict(title=x_title, gridcolor=GRID, zerolinecolor=GRID,
                   tickfont=dict(color=MUTED), title_font=dict(color=MUTED)),
        yaxis=dict(title=y_title, gridcolor=GRID, zerolinecolor=GRID,
                   tickfont=dict(color=MUTED), title_font=dict(color=MUTED)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter, system-ui, sans-serif"),
        legend=dict(font=dict(color=MUTED), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=50, r=20, t=50, b=50),
        height=height,
    )


def line_chart(df, x, series, title, x_title, y_title, height=380):
    """Multi-series line chart. series: list of (column, label, colour)."""
    fig = go.Figure()
    for col, label, colour in series:
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], mode="lines", name=label,
            line=dict(color=colour, width=1.6)))
    fig.update_layout(**base_layout(title, x_title, y_title, height))
    return fig


def bar_chart(x, values, title, x_title, y_title, colour=CYAN, height=380):
    """Single-series bar chart."""
    fig = go.Figure(go.Bar(x=x, y=values, marker_color=colour))
    fig.update_layout(**base_layout(title, x_title, y_title, height))
    return fig


def grouped_bar_chart(categories, series, title, x_title, y_title, height=380):
    """Grouped bars. series: list of (label, values, colour)."""
    fig = go.Figure()
    for label, values, colour in series:
        fig.add_trace(go.Bar(x=categories, y=values, name=label,
                             marker_color=colour))
    fig.update_layout(barmode="group",
                      **base_layout(title, x_title, y_title, height))
    return fig


def histogram(values, title, x_title, height=360, nbins=40):
    """Distribution histogram (rainfall amounts)."""
    fig = go.Figure(go.Histogram(x=values, nbinsx=nbins,
                                 marker_color=BLUE, opacity=0.85))
    fig.update_layout(**base_layout(title, x_title, "Number of days", height))
    return fig


def scatter_chart(x, y, title, x_title, y_title, height=420):
    """Scatter with a perfect-prediction diagonal (actual vs predicted)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name="Test days",
                             marker=dict(color=CYAN, size=5, opacity=0.45)))
    limit = max(float(x.max()), float(y.max())) * 1.05
    fig.add_trace(go.Scatter(x=[0, limit], y=[0, limit], mode="lines",
                             name="Perfect prediction",
                             line=dict(color=RED, dash="dash", width=1)))
    fig.update_layout(**base_layout(title, x_title, y_title, height))
    return fig
