"""MONSOONAI — Page 5: Model Performance.

Baselines, regression metrics, classification metrics, residuals,
year-wise results and feature importance — all loaded from the Phase 3
artefacts or recomputed from them. The honest reading is stated first:
Random Forest beats persistence on MAE by only 0.9%.
"""

import numpy as np
import pandas as pd
import streamlit as st
from pathlib import Path

from charts import AMBER, BLUE, CYAN, RED, bar_chart, grouped_bar_chart
from ui_common import category_pills, footer, info_box, page_header, warning_box


def render(ctx):
    page_header(
        "Model Performance — the full evaluation",
        "Test period 2021–2024 (1,460 days) · every metric against "
        "Open-Meteo / ERA5 reanalysis, not rain gauges")
    category_pills(["reanalysis", "prediction"])

    summary = ctx["summary"]
    reg = ctx["regression"]
    cls = ctx["classification"]
    project_root = ctx["project_root"]

    info_box(
        "**The honest reading, first:** Random Forest beats persistence "
        "on MAE by only **0.9%** (4.191 vs 4.228 mm). Linear Regression "
        "does not beat persistence on MAE at all (4.356 mm — 3.0% worse), "
        "but has the best RMSE and R². The models explain far more "
        "day-to-day variation (R² ~0.46–0.49 vs 0.30) and cut the largest "
        "errors, but the average absolute error barely moves. That is a "
        "working model, not a strong one.")

    # --- Regression table (from evaluation_summary.json) -----------------------
    st.markdown("### Regression — next-day rainfall amount (mm)")
    order = ["persistence", "climatology", "linear_regression", "random_forest"]
    labels = {"persistence": "Persistence (tomorrow = today)",
              "climatology": "Day-of-year climatology",
              "linear_regression": "Linear Regression",
              "random_forest": "Random Forest"}
    rows = []
    for key in order:
        m = reg[key]
        rows.append({
            "Model": labels[key],
            "MAE (mm)": round(m["MAE"], 3),
            "RMSE (mm)": round(m["RMSE"], 3),
            "R²": round(m["R2"], 4),
            "MAE rainy only (mm)": round(m["MAE_rainy"], 3),
            "RMSE rainy only (mm)": round(m["RMSE_rainy"], 3),
            "MAE heavy only (mm)": round(m["MAE_heavy"], 3),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(
        "Rainy only: 452 days (observed t+1 ≥ 2.5 mm). Heavy only: 21 days "
        "(observed t+1 ≥ 64.5 mm). Best MAE: Random Forest. Best RMSE and "
        "R²: Linear Regression. Both models beat climatology on every metric.")

    # --- Classification ---------------------------------------------------------
    st.markdown("### Classification — rain / no-rain (≥ 2.5 mm)")
    st.markdown(
        "Predicting *whether* it will rain is far easier than *how much* — "
        "rain in Mumbai is strongly persistent day-to-day and the monsoon "
        "season is easy to recognise.")
    rows = []
    for key, label in [("logistic_regression", "Logistic Regression"),
                       ("random_forest_classifier", "Random Forest Classifier")]:
        m = cls[key]
        rows.append({
            "Model": label,
            "Precision (rain)": round(m["precision_rain"], 3),
            "Recall (rain)": round(m["recall_rain"], 3),
            "F1 (rain)": round(m["f1_rain"], 3),
            "Accuracy": round(m["accuracy"], 3),
            "ROC-AUC": round(m["roc_auc"], 3),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.markdown(
        "Confusion matrices [[true negatives, false positives], "
        "[false negatives, true positives]]: Logistic Regression "
        f"{cls['logistic_regression']['confusion']} (62 false alarms, "
        "50 missed rainy days); Random Forest "
        f"{cls['random_forest_classifier']['confusion']} (76 false alarms, "
        "37 missed rainy days).")

    # --- Year-wise results -------------------------------------------------------
    st.markdown("### Year-wise results (test years)")
    st.markdown(
        "Computed from the saved test predictions, so these numbers always "
        "match the artefacts. MAE in mm; R² is weak for zero-inflated "
        "rainfall and is shown for completeness, not as the headline.")
    yw = ctx["year_wise"].copy()
    yw = yw[["year", "days",
             "Persistence MAE", "Climatology MAE",
             "Linear Regression MAE", "Random Forest MAE",
             "Persistence R²", "Linear Regression R²", "Random Forest R²"]]
    for col in yw.columns:
        if col not in ("year", "days"):
            yw[col] = yw[col].round(3)
    st.dataframe(yw, width="stretch", hide_index=True)

    # --- Error by month ------------------------------------------------------------
    st.markdown("### Error by month")
    ebm = ctx["error_by_month"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    st.plotly_chart(
        grouped_bar_chart(
            months,
            [("Persistence", ebm["Persistence"].values, "#64748b"),
             ("Linear Regression", ebm["Linear Regression"].values, BLUE),
             ("Random Forest", ebm["Random Forest"].values, CYAN)],
            "Mean absolute error by month (mm) — test period",
            "Month", "Mean absolute error (mm)"),
        width="stretch")
    st.caption(
        "Error concentrates in the monsoon, above all July (MAE ~14 mm), "
        "where rain is heaviest and most variable. Outside the monsoon the "
        "models are nearly perfect — because it almost never rains, and "
        "predicting near-zero is usually right. Linear Regression is worse "
        "than persistence in the dry months: it predicts small amounts of "
        "rain on dry days that persistence gets exactly right.")

    # --- Residual plots (Phase 3 figures) --------------------------------------------
    st.markdown("### Residuals — actual vs predicted")
    figs = project_root / "docs" / "figures"
    col1, col2 = st.columns(2)
    with col1:
        st.image(str(figs / "actual_vs_predicted_scatter.png"),
                 caption="Actual vs predicted, test period. The scatter fans "
                         "out above ~50 mm — the under-prediction of extremes.",
                 width="stretch")
    with col2:
        st.image(str(figs / "residuals_vs_observed.png"),
                 caption="Random Forest residuals vs observed rainfall. The "
                         "downward slope at high observed values is the "
                         "extreme under-prediction.",
                 width="stretch")
    st.image(str(figs / "test_timeseries.png"),
             caption="Daily observed vs predicted, test period 2021–2024. The "
                     "models track the monsoon seasons but flatten the peaks.",
             width="stretch")

    # --- Feature importance -------------------------------------------------------------
    st.markdown("### What the models actually learned — feature importance")
    fi = ctx["feature_importance"]["random_forest"][:10]
    st.plotly_chart(
        bar_chart([name for name, _ in reversed(fi)],
                  [round(val, 3) for _, val in reversed(fi)],
                  "Random Forest — top 10 feature importances",
                  "Feature", "Importance", colour=CYAN),
        width="stretch")
    st.markdown(
        f"**Today's rainfall alone carries "
        f"{ctx['feature_importance']['random_forest'][0][1]:.0%} of the "
        "Random Forest's signal** (top 5 features together: 74.7%). The "
        "models are, in effect, smart persistence with small adjustments "
        "from pressure, humidity and earlier rain. Linear Regression "
        "agrees: its largest standardised coefficient is today's rainfall "
        "(5.35), followed by mean temperature (−2.38) and pressure "
        "(−2.15). This is explainable in an interview and is not a flaw — "
        "but it must be stated, not hidden behind the R² figure.")
    lr_coef = ctx["feature_importance"]["linear_regression"][:8]
    coef_df = pd.DataFrame(
        [{"Feature": name, "Standardised coefficient": round(val, 2)}
         for name, val in lr_coef])
    st.dataframe(coef_df, width="stretch", hide_index=True)

    warning_box(
        "Reminder: every metric on this page is performance against "
        "Open-Meteo / ERA5 **reanalysis**. Against a real rain gauge the "
        "error would be larger — the reanalysis target is already a "
        "smoothed version of reality, and the model inherits that "
        "smoothing. See Data & Methodology.")

    footer()
