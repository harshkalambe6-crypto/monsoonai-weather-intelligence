"""MONSOONAI — Page 3: Historical Analysis.

Annual / monthly trends, monsoon patterns and rainfall distribution,
all from the processed Mumbai daily series (HISTORICAL REANALYSIS).
Every chart is labelled with its units; no model output appears here.
"""

import numpy as np
import pandas as pd
import streamlit as st

from charts import BLUE, CYAN, TEAL, bar_chart, grouped_bar_chart, histogram, line_chart
from ui_common import category_pills, footer, info_box, page_header


def render(ctx):
    page_header(
        "Historical Analysis — 25 years of Mumbai rainfall",
        "Annual and monthly trends, monsoon patterns and rainfall "
        "distribution · historical reanalysis, 2000–2024")
    category_pills(["reanalysis"])

    daily = ctx["daily"]
    rain = daily["precipitation_sum"]

    # --- Annual totals ------------------------------------------------------
    annual = daily.groupby(daily["time"].dt.year).agg(
        total_mm=("precipitation_sum", "sum"),
        rainy_days=("precipitation_sum", lambda s: (s >= 2.5).sum()),
        max_day_mm=("precipitation_sum", "max"),
    ).reset_index().rename(columns={"time": "year"})
    st.plotly_chart(
        bar_chart(annual["year"], annual["total_mm"],
                  "Annual rainfall totals (mm) — Mumbai grid cell",
                  "Year", "Total rainfall (mm)", colour=BLUE),
        width="stretch")
    st.caption(
        "Historical reanalysis (Open-Meteo / ERA5). Mean annual total "
        f"{annual['total_mm'].mean():,.0f} mm. Wettest: "
        f"{int(annual.loc[annual['total_mm'].idxmax(), 'year'])} "
        f"({annual['total_mm'].max():,.0f} mm). Driest: "
        f"{int(annual.loc[annual['total_mm'].idxmin(), 'year'])} "
        f"({annual['total_mm'].min():,.0f} mm).")

    # --- Monthly means + monsoon share --------------------------------------
    monthly = daily.groupby(daily["time"].dt.month).agg(
        mean_daily_mm=("precipitation_sum", "mean"),
        total_mm=("precipitation_sum", "sum"),
    )
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monsoon_total = daily[daily["time"].dt.month.isin([6, 7, 8, 9])][
        "precipitation_sum"].sum()
    monsoon_share = 100 * monsoon_total / rain.sum()
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            bar_chart(months, monthly["mean_daily_mm"].values,
                      "Mean daily rainfall by month (mm/day)",
                      "Month", "Mean rainfall (mm/day)", colour=CYAN),
            width="stretch")
    with col2:
        st.plotly_chart(
            bar_chart(months, monthly["total_mm"].values,
                      "Total rainfall by month, 2000–2024 (mm)",
                      "Month", "Total rainfall (mm)", colour=TEAL),
            width="stretch")
    st.markdown(
        f"**Monsoon (June–September) contributes {monsoon_share:.1f}% of "
        "all rainfall in this dataset.** July alone averages "
        f"{monthly.loc[7, 'mean_daily_mm']:.1f} mm/day. From November to "
        "April Mumbai is almost dry — the median day in those months "
        "records 0.0 mm.")

    # --- Three-way classification -------------------------------------------
    dry = int((rain == 0).sum())
    light = int(((rain > 0) & (rain < 2.5)).sum())
    rainy = int((rain >= 2.5).sum())
    heavy = int((rain >= 64.5).sum())
    very_heavy = int((rain >= 115.6).sum())
    extreme = int((rain > 204.4).sum())
    st.markdown("### How the 9,132 days classify")
    st.markdown(
        "Rainy day: ≥ 2.5 mm (IMD Met Glossary, verified). Heavy: "
        "≥ 64.5 mm, very heavy: ≥ 115.6 mm, extremely heavy: > 204.4 mm "
        "(IMD bands). The three categories below are exhaustive — they "
        "sum to 9,132 days.")
    class_df = pd.DataFrame([
        {"Category": "Dry (exactly 0.00 mm)", "Days": dry,
         "Share": f"{100 * dry / len(daily):.1f}%"},
        {"Category": "Light rain (0 – 2.5 mm)", "Days": light,
         "Share": f"{100 * light / len(daily):.1f}%"},
        {"Category": "Rainy (≥ 2.5 mm)", "Days": rainy,
         "Share": f"{100 * rainy / len(daily):.1f}%"},
    ])
    st.dataframe(class_df, width="stretch", hide_index=True)
    st.caption(
        f"The 893 light-rain days contribute only 885.9 mm in total "
        f"(1.7% of all rain) — numerous, but hydrologically small. "
        f"Heavy days: {heavy} · very heavy: {very_heavy} · "
        f"extremely heavy: {extreme} in 25 years.")

    # --- Distribution --------------------------------------------------------
    st.plotly_chart(
        histogram(rain, "Distribution of daily rainfall (mm) — 2000–2024",
                  "Daily rainfall (mm)"),
        width="stretch")
    st.caption(
        "Daily rainfall is strongly zero-inflated: 59.9% of days record "
        "exactly 0.0 mm, and the distribution has a long right tail "
        "(maximum 251.1 mm, 22 Sep 2016). This is why R² is a weak "
        "summary for this target and why rainy-day-only errors are "
        "reported separately on the Model Performance page.")

    # --- Annual detail table ---------------------------------------------------
    st.markdown("### Annual detail")
    annual_display = annual.copy()
    annual_display.columns = ["Year", "Total (mm)", "Rainy days",
                              "Wettest day (mm)"]
    annual_display["Total (mm)"] = annual_display["Total (mm)"].round(1)
    annual_display["Wettest day (mm)"] = annual_display[
        "Wettest day (mm)"].round(1)
    st.dataframe(annual_display, width="stretch", hide_index=True)

    info_box(
        "About the data: these are reanalysis values for the grid cell "
        "centred at 19.086115° N, 72.85291° E — the ~25 km cell containing "
        "Mumbai, not a rain gauge. The 2020 IMD cross-check found "
        "reanalysis totals ~22% below IMD's gauge-based gridded totals, "
        "so treat the absolute totals as reanalysis-scale, not gauge truth.")

    footer()
