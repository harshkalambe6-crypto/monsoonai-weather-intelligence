"""MONSOONAI — Page 1: Overview.

Mumbai historical rainfall intelligence and the project summary.
Everything on this page is HISTORICAL REANALYSIS or MODEL PREDICTION
metrics measured on that reanalysis — nothing here is a live forecast
or a rain-gauge observation.
"""

import numpy as np
import streamlit as st

from charts import bar_chart, line_chart, BLUE, CYAN, TEAL
from ui_common import category_pills, footer, info_box, page_header, warning_box


def render(ctx):
    page_header(
        "Overview — Mumbai rainfall intelligence",
        "MONSOONAI · Turning weather data into predictive intelligence · "
        "Mumbai, India — one reanalysis grid cell, 2000–2024")
    category_pills(["reanalysis", "prediction"])

    daily = ctx["daily"]
    summary = ctx["summary"]
    reg = ctx["regression"]

    st.markdown(
        "MONSOONAI predicts **tomorrow's rainfall in Mumbai** from the "
        "last 8 days of weather. It is a student research project, built "
        "on real historical data and evaluated honestly: the models work "
        "modestly, rain/no-rain classification is strong, and heavy-rain "
        "prediction does not work yet. This page summarises the project; "
        "the evidence is on the Model Performance and Extreme Rainfall pages.")

    warning_box(
        "This is an educational / research tool, not an operational "
        "forecast or warning system. All rainfall figures are "
        "Open-Meteo / ERA5 **reanalysis** values for the ~25 km grid cell "
        "containing Mumbai — not rain-gauge measurements, and not live data. "
        "The dataset ends 31 December 2024.")

    # --- Headline numbers (computed from the loaded dataset) ------------
    annual = daily.groupby(daily["time"].dt.year)["precipitation_sum"].sum()
    rainy = (daily["precipitation_sum"] >= 2.5).sum()
    heavy = (daily["precipitation_sum"] >= 64.5).sum()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Days in dataset", f"{len(daily):,}",
                "1 Jan 2000 – 31 Dec 2024")
    col2.metric("Mean annual rainfall", f"{annual.mean():,.0f} mm",
                "reanalysis")
    col3.metric("Rainy days (≥ 2.5 mm)", f"{rainy:,} ({100 * rainy / len(daily):.1f}%)",
                "IMD threshold, verified")
    col4.metric("Heavy days (≥ 64.5 mm)", f"{heavy:,}",
                "25 years")

    # --- Headline model results (loaded from the evaluation artefacts) ---
    st.markdown("### Headline results — test period 2021–2024 (1,460 days)")
    st.markdown(
        "Metrics are against Open-Meteo / ERA5 reanalysis, not gauges. "
        "Full tables: **Model Performance** page.")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Best MAE — Random Forest",
                f"{reg['random_forest']['MAE']:.3f} mm",
                "only 0.9% better than persistence")
    col2.metric("Best RMSE / R² (Linear Reg.)",
                f"{reg['linear_regression']['RMSE']:.3f} mm",
                f"R² {reg['linear_regression']['R2']:.3f}")
    col3.metric("Rain / no-rain — Random Forest",
                f"F1 {ctx['classification']['random_forest_classifier']['f1_rain']:.3f}",
                f"ROC-AUC {ctx['classification']['random_forest_classifier']['roc_auc']:.3f}")
    col4.metric("Heavy rain — dedicated classifier",
                f"recall {ctx['classification']['heavy_classifier']['recall_heavy']:.3f}",
                "precision 0.137 · 88 false alarms")

    # --- Annual rainfall trend -------------------------------------------
    annual_df = annual.reset_index()
    annual_df.columns = ["year", "total_mm"]
    st.plotly_chart(
        bar_chart(annual_df["year"], annual_df["total_mm"],
                  "Annual rainfall — Mumbai grid cell (historical reanalysis)",
                  "Year", "Total rainfall (mm)", colour=BLUE),
        width="stretch")
    st.caption(
        "Historical reanalysis, Open-Meteo / ERA5. Wettest year: "
        f"{annual.idxmax()} ({annual.max():,.0f} mm). Driest year: "
        f"{annual.idxmin()} ({annual.min():,.0f} mm). "
        "Reanalysis underestimates IMD gauge-based totals by ~22% (2020 "
        "cross-check) — see Data & Methodology.")

    # --- Monthly pattern ---------------------------------------------------
    monthly = daily.groupby(daily["time"].dt.month)["precipitation_sum"].mean()
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    st.plotly_chart(
        bar_chart(months, monthly.values,
                  "Mean daily rainfall by month — the monsoon dominates",
                  "Month", "Mean rainfall (mm/day)", colour=CYAN),
        width="stretch")
    st.caption(
        "June–September (monsoon) contributes 94.2% of all rainfall in "
        "this dataset. Outside the monsoon, Mumbai is almost dry — which "
        "is why predicting near-zero is usually right, and why the models' "
        "errors concentrate in July.")

    # --- What this project is / is not ------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### What MONSOONAI does")
        st.markdown(
            "- Predicts **next-day** rainfall (t+1) for one Mumbai grid cell\n"
            "- Gives a **rain / no-rain probability** (F1 0.880)\n"
            "- Reports its own errors honestly, including heavy-rain misses\n"
            "- Is fully reproducible from the saved data and code")
    with col2:
        st.markdown("### What it does NOT do")
        st.markdown(
            "- No 7-day forecast — only t+1 is supported by the data\n"
            "- No operational warnings — heavy-rain prediction is unreliable\n"
            "- No live weather — the dataset ends 31 Dec 2024\n"
            "- No India-wide model — Mumbai only, one grid cell")

    info_box(
        "How to use this dashboard: **Rainfall Prediction** for a "
        "next-day prediction from the latest available data; "
        "**Historical Analysis** for trends; **Extreme Rainfall** for the "
        "honest heavy-rain story; **Model Performance** for every metric; "
        "**Data & Methodology** for sources, alignment and reproducibility.")

    footer()
