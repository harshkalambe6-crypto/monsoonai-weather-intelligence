"""MONSOONAI — Page 2: Rainfall Prediction.

Next-day (t+1) prediction ONLY, generated from the saved Phase 3 model
artefacts using only data dated t or earlier. Two views:

  1. "Make a prediction" — pick a cutoff day t and a model; the app
     builds the features for t and runs the saved model. The default
     is the latest available date in the local dataset. This is a
     HISTORICAL-DATA demonstration, not a live forecast: the dataset
     ends 31 Dec 2024 and no live weather feed is connected.
  2. "Historical test predictions" — the saved test-period predictions
     (2021–2024), where the observed t+1 value is known, so the error
     can be shown. These are labelled as historical test predictions.

If the data file cannot be loaded, the page shows an error instead of
inventing a value.
"""

import pandas as pd
import requests
import streamlit as st

from charts import CYAN, line_chart
from feature_engine import feature_row_for_cutoff
from predict import imd_band, predict_next_day
from ui_common import category_pills, footer, info_box, page_header, warning_box


def render(ctx):
    page_header(
        "Rainfall Prediction — next day only (t+1)",
        "Prediction for the day after the cutoff, 23:59 Asia/Kolkata, "
        "from data dated t or earlier only")
    category_pills(["reanalysis", "prediction"])

    daily = ctx["daily"]
    latest = daily["time"].max()
    target_date = latest + pd.Timedelta(days=1)

    warning_box(
        "NOT a live forecast. This prediction is generated from the local "
        "historical dataset, which ends "
        f"{latest.date()} (reanalysis, ~5-day lag from real time). "
        "No live weather feed is connected, and no current weather data "
        "is shown anywhere in this app. The prediction below is a "
        "demonstration of the trained model on historical data.")

    info_box(
        f"**Data availability:** latest available day in this build: "
        f"**{latest.date()}**. Prediction cutoff: 23:59 Asia/Kolkata on "
        f"the cutoff day. Input window: t−7…t. Target: rainfall on "
        f"{target_date.date()}. If the dataset is refreshed (Phase 2 prep "
        "script), this page automatically uses the new latest date.")

    # --- Optional archive freshness check ---------------------------------
    if st.button("Check whether newer archive data exists (Open-Meteo)"):
        try:
            url = ("https://archive-api.open-meteo.com/v1/archive"
                   "?latitude=19.0760&longitude=72.8777"
                   "&start_date=2024-12-20&end_date=2025-12-31"
                   "&daily=precipitation_sum&timezone=Asia%2FKolkata&format=csv")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            lines = [ln for ln in resp.text.splitlines() if ln.strip()]
            if len(lines) > 1:
                last = lines[-1].split(",")[0]
                st.info(
                    f"Open-Meteo archive now reaches **{last}**; this build "
                    f"uses data through **{latest.date()}**. To refresh, "
                    "re-run the Phase 2 data pipeline "
                    "(src/prepare_mumbai_daily.py) — the dashboard does not "
                    "auto-refresh, so it never silently changes its data.")
            else:
                st.warning("The archive returned no rows for the checked range.")
        except Exception as exc:  # network failure is not a prediction
            st.warning(
                "Could not reach the Open-Meteo archive to check for newer "
                f"data ({exc}). The local dataset through "
                f"{latest.date()} is still used; nothing was invented.")

    # --- Make a prediction --------------------------------------------------
    st.markdown("### Make a prediction")
    min_date = daily["time"].min().date() + pd.Timedelta(days=7)
    col1, col2 = st.columns(2)
    with col1:
        cutoff = st.date_input(
            "Cutoff day t (prediction made at 23:59 Asia/Kolkata)",
            value=latest.date(), min_value=min_date, max_value=latest.date(),
            help="Only data dated t or earlier is used. The first 7 days "
                 "of the series cannot be a cutoff day (no t−7 history).")
    with col2:
        model_name = st.selectbox(
            "Model",
            ["Random Forest", "Linear Regression", "Persistence", "Climatology"],
            help="Random Forest has the best test MAE; Linear Regression "
                 "the best RMSE/R². Persistence and Climatology are the "
                 "baselines the models are judged against.")

    cutoff_ts = pd.Timestamp(cutoff)
    try:
        climatology = ctx["climatology_train"]
        row = feature_row_for_cutoff(daily, climatology, cutoff_ts)
        day_row = daily[daily["time"] == cutoff_ts]
        rain_today = float(day_row["precipitation_sum"].iloc[0]) if not day_row.empty else None
        clim_value = float(row["climatology_doy"].iloc[0]) if row is not None else None
        result = predict_next_day(row, model_name,
                                  climatology_value=clim_value,
                                  rain_today=rain_today)
    except Exception as exc:
        st.error(
            "Could not generate a prediction for this cutoff day. "
            f"({exc}) No value has been invented — pick another date or "
            "check that the model artefacts exist in artifacts/.")
        result = None

    if result is not None:
        target = cutoff_ts + pd.Timedelta(days=1)
        st.markdown(f"#### Prediction for **{target.date()}** "
                    f"(model: {model_name})")
        col1, col2, col3 = st.columns(3)
        col1.metric("Predicted rainfall", f"{result['amount_mm']:.1f} mm",
                    result["band"])
        col2.metric(
            "Rain probability (≥ 2.5 mm)",
            f"{result['rain_probability'] * 100:.0f}%" if result["rain_probability"] is not None else "—",
            "from the rain/no-rain classifier" if result["rain_probability"] is not None else "not available for baselines")
        col3.metric(
            "Heavy-rain probability (≥ 64.5 mm)",
            f"{result['heavy_probability'] * 100:.0f}%" if result["heavy_probability"] is not None else "—",
            "RF heavy classifier — precision 0.137" if result["heavy_probability"] is not None else "not available for baselines")
        for note in result["notes"]:
            st.caption(note)
        # Observed value, if the target day is in the dataset (historical check).
        observed_row = daily[daily["time"] == target]
        if not observed_row.empty:
            observed = float(observed_row["precipitation_sum"].iloc[0])
            error = result["amount_mm"] - observed
            st.markdown(
                f"**Historical check (reanalysis):** observed rainfall on "
                f"{target.date()} was **{observed:.1f} mm** — this "
                f"prediction was **{error:+.1f} mm** off. This is a "
                f"back-test on historical data, not a live forecast.")
        else:
            st.markdown(
                f"**Observed value for {target.date()}:** not in the "
                f"dataset (it is after the last available day). The "
                f"prediction cannot be verified against data yet.")

    # --- Historical test predictions ---------------------------------------
    st.markdown("### Historical test predictions (2021–2024)")
    st.markdown(
        "The saved test-period predictions, where the observed t+1 value "
        "is known. Use these to judge the model — not the single "
        "prediction above.")
    preds = ctx["predictions"]
    col_map = {
        "Random Forest": "pred_random_forest_mm",
        "Linear Regression": "pred_linear_regression_mm",
        "Persistence": "pred_persistence_mm",
        "Climatology": "pred_climatology_mm",
    }
    test_date = st.date_input(
        "Pick a cutoff day t in the test period",
        value=pd.Timestamp("2021-07-09").date(),
        min_value=pd.Timestamp("2021-01-01").date(),
        max_value=pd.Timestamp("2024-12-31").date(),
        help="The saved predictions are stored by cutoff day t. The "
             "observed value shown is the rainfall on t+1.")
    prow = preds[preds["time"] == pd.Timestamp(test_date)]
    if prow.empty:
        st.warning("No test prediction exists for that date.")
    else:
        prow = prow.iloc[0]
        cols = st.columns(4)
        for (label, colname), c in zip(col_map.items(), cols):
            pred_val = float(prow[colname])
            err = pred_val - float(prow["observed_next_day_rain_mm"])
            c.metric(label, f"{pred_val:.1f} mm", f"error {err:+.1f} mm")
        target_day = pd.Timestamp(test_date) + pd.Timedelta(days=1)
        st.caption(
            f"Cutoff day t: {test_date} · predicted day t+1: "
            f"{target_day.date()} · observed (reanalysis) on t+1: "
            f"{float(prow['observed_next_day_rain_mm']):.1f} mm · "
            f"Rain probability (RF classifier): "
            f"{float(prow['pred_rain_prob_rf']) * 100:.0f}% · "
            f"(Logistic Regression): "
            f"{float(prow['pred_rain_prob_logreg']) * 100:.0f}%")

    footer()
