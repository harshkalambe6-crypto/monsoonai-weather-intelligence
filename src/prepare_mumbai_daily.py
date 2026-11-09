"""
MONSOONAI — Phase 2 data preparation
=====================================
Reads the raw Open-Meteo Archive API responses for Mumbai and builds one
clean daily dataset.

Data provenance (labels matter — see docs/data-quality-note.md):
  * The values below are HISTORICAL REANALYSIS (ERA5, via Open-Meteo),
    NOT station observations and NOT a forecast.
  * Requested point: 19.0760 N, 72.8777 E (Mumbai).
    The API returned the grid cell centred at 19.086115 N, 72.85291 E
    (a few km away) — see the alignment note in the docs.

Raw files (do not edit by hand):
  * data/raw/mumbai_openmeteo_daily_2000-2024.csv
  * data/raw/mumbai_openmeteo_hourly_2000-2024.csv

Output:
  * data/processed/mumbai_daily_2000-2024.csv  (one row per day)

Why the hourly file exists:
  The Open-Meteo Archive API only offers relative humidity and pressure
  as HOURLY variables — there is no daily `relative_humidity_2m` or
  `pressure_msl` variable (the first request with those daily names
  returned HTTP 400). So daily humidity/pressure/mean temperature are
  computed here as the simple mean of the 24 hourly values for each
  Asia/Kolkata calendar day. That is a documented derivation, not a
  value the API returned directly.

Run:  python3 src/prepare_mumbai_daily.py
"""

import pandas as pd

RAW_DIR = "data/raw"
OUT_PATH = "data/processed/mumbai_daily_2000-2024.csv"

# The Open-Meteo CSV starts with 3 metadata lines (a header row, one data
# row with the grid-cell coordinates, one blank line) before the real
# column header. skiprows=3 skips them.
daily = pd.read_csv(
    f"{RAW_DIR}/mumbai_openmeteo_daily_2000-2024.csv",
    skiprows=3,
)
hourly = pd.read_csv(
    f"{RAW_DIR}/mumbai_openmeteo_hourly_2000-2024.csv",
    skiprows=3,
)

# Clean the column names: "temperature_2m_max (°C)" -> "temperature_2m_max".
# The unit in brackets is recorded in the data dictionary instead.
daily.columns = [c.split(" (")[0] for c in daily.columns]
hourly.columns = [c.split(" (")[0] for c in hourly.columns]

daily["time"] = pd.to_datetime(daily["time"])
hourly["time"] = pd.to_datetime(hourly["time"])

# Daily means from the hourly values, grouped by Asia/Kolkata calendar day.
# (The hourly timestamps are already in Asia/Kolkata, per the request.)
hourly["date"] = hourly["time"].dt.date
daily_means = (
    hourly.groupby("date")[["temperature_2m", "relative_humidity_2m",
                             "pressure_msl", "surface_pressure"]]
    .mean()
    .rename(columns={
        "temperature_2m": "temperature_2m_mean",
        "relative_humidity_2m": "relative_humidity_2m_mean",
        "pressure_msl": "pressure_msl_mean",
        "surface_pressure": "surface_pressure_mean",
    })
    .reset_index()
)
daily_means["date"] = pd.to_datetime(daily_means["date"])

df = daily.merge(daily_means, left_on="time", right_on="date", how="left")
df = df.drop(columns=["date"]).sort_values("time").reset_index(drop=True)

df.to_csv(OUT_PATH, index=False)
print(f"rows: {len(df)}")
print(f"date range: {df['time'].min().date()} to {df['time'].max().date()}")
print("columns:", list(df.columns))
print(df.isna().sum().to_string())
