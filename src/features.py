"""
MONSOONAI — Feature engineering (Phase 3)
===========================================
Builds the feature table for next-day rainfall prediction from
data/processed/mumbai_daily_2000-2024.csv (Open-Meteo / ERA5 reanalysis).

Prediction setup (binding — see docs/prediction-definition.md):
  * Cutoff: end of day t, 23:59 Asia/Kolkata.
  * Target: precipitation_sum on day t+1, in mm.
  * Input window: days t-7 .. t (widened from t-6..t in Phase 3 — see
    the note on the t-7 lag below; the t-7 lag is leakage-free because
    it is in the past, and widening the window definition is cleaner
    than dropping a useful weekly-lag feature).

Leakage rule (see docs/leakage-audit.md): every feature uses data
dated t or earlier ONLY. Nothing in this file touches t+1, except the
target column itself, which is built with a shift and is never used
as an input.

The three Phase 2 leakage-audit fixes, applied here:
  1. Input window widened to t-7..t so the t-7 lag is inside it.
  2. Day-of-year climatology is computed from TRAINING data only —
     the caller passes the train-only climatology in; this module
     never computes it from the full series.
  3. "Days since last rain" is capped at 30 days.

Run:  python3 src/train_models.py   (this module is imported, not run)
"""

import numpy as np
import pandas as pd

RAINY_DAY_MM = 2.5   # IMD-verified rainy-day threshold
HEAVY_MM = 64.5      # IMD "heavy" band starts at 64.5 mm / 24 h
DAYS_SINCE_RAIN_CAP = 30

# Columns in the processed daily file that are inputs at day t.
# (temperature_2m_mean, relative_humidity_2m_mean, pressure_msl_mean
# and surface_pressure_mean are daily means computed from that day's
# own 24 hourly values — see docs/leakage-audit.md.)


def build_features(df, climatology_train):
    """Build the feature table.

    Parameters
    ----------
    df : DataFrame with a 'time' column (datetime) and the 14 processed
        columns, sorted by date, one row per day.
    climatology_train : Series indexed by day-of-year giving the mean
        rainfall for that day-of-year, computed from TRAINING data only.

    Returns
    -------
    DataFrame with one row per day t (the first 7 rows are dropped:
    the t-7 lag does not exist for them), a 'target_next_day_rain_mm'
    column, and one column per feature. The target is the ONLY column
    that uses t+1 data.
    """
    df = df.sort_values("time").reset_index(drop=True)
    rain = df["precipitation_sum"]
    temp_mean = df["temperature_2m_mean"]
    humidity = df["relative_humidity_2m_mean"]
    pressure = df["pressure_msl_mean"]

    out = pd.DataFrame({"time": df["time"]})

    # --- Lagged rainfall (all dated t or earlier) ----------------------
    out["rain_t"] = rain
    out["rain_t1"] = rain.shift(1)
    out["rain_t2"] = rain.shift(2)
    out["rain_t3"] = rain.shift(3)
    out["rain_t7"] = rain.shift(7)  # inside the widened t-7..t window

    # --- Rolling rainfall (windows end at t) ---------------------------
    out["rain_roll3_sum"] = rain.rolling(3).sum()
    out["rain_roll3_mean"] = rain.rolling(3).mean()
    out["rain_roll7_sum"] = rain.rolling(7).sum()
    out["rain_roll7_mean"] = rain.rolling(7).mean()

    # --- Days since last rain, capped at 30 (fix 3) --------------------
    # Count back from day t (inclusive) to the most recent rainy day.
    # 0 means it rained on day t itself.
    is_rainy = (rain >= RAINY_DAY_MM).values
    days_since = np.zeros(len(df), dtype=int)
    last_rain = -1  # index of the most recent rainy day seen so far
    for i in range(len(df)):
        if is_rainy[i]:
            last_rain = i
        if last_rain == -1:
            # No rainy day yet in the series: count back to the start.
            days_since[i] = i
        else:
            days_since[i] = i - last_rain
    out["days_since_rain"] = np.minimum(days_since, DAYS_SINCE_RAIN_CAP)

    # --- Rainy-day count in the last 7 days (t-6..t) -------------------
    out["rainy_days_last7"] = is_rainy.astype(int)
    out["rainy_days_last7"] = (
        pd.Series(out["rainy_days_last7"]).rolling(7).sum().values
    )

    # --- Temperature ----------------------------------------------------
    out["temp_max_t"] = df["temperature_2m_max"]
    out["temp_min_t"] = df["temperature_2m_min"]
    out["temp_mean_t"] = temp_mean
    out["temp_mean_3d"] = temp_mean.rolling(3).mean()

    # --- Humidity -------------------------------------------------------
    out["humidity_t"] = humidity
    out["humidity_3d"] = humidity.rolling(3).mean()

    # --- Pressure -------------------------------------------------------
    out["pressure_t"] = pressure
    out["pressure_change_3d"] = pressure - pressure.shift(3)

    # --- Wind -----------------------------------------------------------
    out["wind_max_t"] = df["wind_speed_10m_max"]
    direction_rad = np.deg2rad(df["wind_direction_10m_dominant"])
    out["wind_dir_sin"] = np.sin(direction_rad)
    out["wind_dir_cos"] = np.cos(direction_rad)

    # --- Seasonal (calendar only — no weather data involved) -----------
    doy = df["time"].dt.day_of_year
    out["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    out["month"] = df["time"].dt.month
    out["is_monsoon"] = df["time"].dt.month.isin([6, 7, 8, 9]).astype(int)

    # --- Climatology (fix 2: TRAINING data only) -----------------------
    # The caller computed this from the training period (2000-2017).
    # It is mapped in by day-of-year, so no test/validation rainfall
    # can leak into the feature.
    out["climatology_doy"] = doy.map(climatology_train).values

    # --- Target: tomorrow's rainfall (the ONLY t+1 column) ------------
    out["target_next_day_rain_mm"] = rain.shift(-1)

    # Drop rows where any lag/rolling feature is undefined (the first
    # 7 days) and the last row, which has no tomorrow to predict.
    out = out.dropna().reset_index(drop=True)
    return out


FEATURE_COLUMNS = [
    "rain_t", "rain_t1", "rain_t2", "rain_t3", "rain_t7",
    "rain_roll3_sum", "rain_roll3_mean", "rain_roll7_sum", "rain_roll7_mean",
    "days_since_rain", "rainy_days_last7",
    "temp_max_t", "temp_min_t", "temp_mean_t", "temp_mean_3d",
    "humidity_t", "humidity_3d",
    "pressure_t", "pressure_change_3d",
    "wind_max_t", "wind_dir_sin", "wind_dir_cos",
    "doy_sin", "doy_cos", "month", "is_monsoon",
    "climatology_doy",
]
