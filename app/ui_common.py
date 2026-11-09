"""
MONSOONAI dashboard — shared UI pieces (Phase 4)
==================================================
The category legend (reanalysis / observation / prediction / external
forecast) appears on every page, and the footer carries the data
attribution. Keeping them in one place means no page can forget them.
"""

import re

import streamlit as st


def _bold(text):
    """Convert Markdown **bold** to HTML <strong>, because the boxes
    below are rendered as raw HTML (where ** is literal text)."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

# Category colours — used consistently on every page.
CATEGORY_STYLE = {
    "reanalysis": ("HISTORICAL REANALYSIS", "#38bdf8"),
    "observation": ("OBSERVATIONAL DATA", "#4ade80"),
    "prediction": ("MODEL PREDICTION", "#f59e0b"),
    "forecast": ("EXTERNAL FORECAST", "#a78bfa"),
}

FOOTER_TEXT = (
    "Weather data by Open-Meteo.com (CC BY 4.0) · IMD 0.25° gridded rainfall cross-check · "
    "All model metrics are performance against Open-Meteo / ERA5 reanalysis, "
    "not independent rain-gauge observations · MONSOONAI is an educational / research tool, "
    "not an operational forecast or warning system."
)


def category_pills(categories):
    """Render the data-category legend for the current page.

    categories: list of keys from CATEGORY_STYLE that appear on the page.
    Every number on the page belongs to one of these categories.
    """
    pills = []
    for key in categories:
        label, colour = CATEGORY_STYLE[key]
        pills.append(
            f'<span style="display:inline-block; padding:2px 10px; '
            f'margin:0 6px 6px 0; border:1px solid {colour}; '
            f'border-radius:999px; color:{colour}; font-size:11px; '
            f'letter-spacing:0.08em; font-weight:600;">{label}</span>')
    st.markdown(
        '<div style="margin:4px 0 14px 0;">'
        '<span style="color:#94a3b8; font-size:12px; margin-right:8px;">'
        'DATA ON THIS PAGE:</span>' + "".join(pills) + "</div>",
        unsafe_allow_html=True)


def page_header(title, subtitle):
    """Page title + one-line summary, in the dashboard's voice."""
    st.markdown(f"## {title}")
    st.markdown(
        f'<p style="color:#94a3b8; font-size:15px; margin-top:-8px;">'
        f"{subtitle}</p>", unsafe_allow_html=True)


def warning_box(text):
    """Amber warning box for limitations that must not be missed."""
    st.markdown(
        f'<div style="background:#1c1503; border:1px solid #f59e0b; '
        f'border-left:4px solid #f59e0b; border-radius:8px; '
        f'padding:12px 16px; margin:12px 0; color:#fde68a; font-size:14px;">'
        f"⚠️ {_bold(text)}</div>",
        unsafe_allow_html=True)


def info_box(text):
    """Blue info box for honest context (data dates, lags, definitions)."""
    st.markdown(
        f'<div style="background:#0e1a2e; border:1px solid #38bdf8; '
        f'border-left:4px solid #38bdf8; border-radius:8px; '
        f'padding:12px 16px; margin:12px 0; color:#bae6fd; font-size:14px;">'
        f"ℹ️ {_bold(text)}</div>",
        unsafe_allow_html=True)


def footer():
    """Attribution + honesty footer, shown on every page."""
    st.markdown("---")
    st.markdown(
        f'<p style="color:#64748b; font-size:12px; line-height:1.6;">'
        f"{FOOTER_TEXT}</p>", unsafe_allow_html=True)
