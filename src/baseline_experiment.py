"""
MONSOONAI — Phase 2 baseline experiment (BASELINES ONLY)
==========================================================
Predicts NEXT-DAY rainfall (target = precipitation_sum on day t+1, in mm)
for Mumbai, using only data dated t or earlier.

Baselines (the bar every later model must clear):
  1. Persistence — tomorrow's rainfall = today's rainfall.
  2. Day-of-year climatology — tomorrow's rainfall = the mean rainfall
     for that calendar day-of-year, computed from the TRAINING period
     only (using test-period data here would be leakage).

Chronological split (no random shuffling — time order is the point):
  * train      2000-01-01 to 2017-12-31
  * validation 2018-01-01 to 2020-12-31
  * test       2021-01-01 to 2024-12-31

Metrics: MAE, RMSE, R^2 — overall and on rainy days only
(rainy day = precipitation_sum >= 2.5 mm, the IMD-verified threshold;
see docs/crosscheck-and-threshold.md).

What this script does NOT do: no Random Forest, no XGBoost, no LSTM,
no classification model. Those come only after the data is validated.

Run:  python3 src/baseline_experiment.py
"""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Fixed seed (no randomness is used here, but the seed is set anyway so
# any future extension of this script is reproducible).
np.random.seed(42)

DATA = "data/processed/mumbai_daily_2000-2024.csv"
RAINY_DAY_MM = 2.5  # IMD-verified rainy-day threshold (see docs/crosscheck-and-threshold.md)

df = pd.read_csv(DATA, parse_dates=["time"]).sort_values("time").reset_index(drop=True)

# Target: tomorrow's rainfall. The last row has no tomorrow, so it drops out.
df["target_next_day_rain_mm"] = df["precipitation_sum"].shift(-1)
df = df.dropna(subset=["target_next_day_rain_mm"]).reset_index(drop=True)

train = df[df["time"] < "2018-01-01"]
valid = df[(df["time"] >= "2018-01-01") & (df["time"] < "2021-01-01")]
test = df[df["time"] >= "2021-01-01"]

print(f"train rows: {len(train)}, validation rows: {len(valid)}, "
      f"test rows: {len(test)}")

# --- Baseline 1: persistence -------------------------------------------
# Predict tomorrow = today. Uses only the rainfall on day t.
test_persistence = test["precipitation_sum"].values

# --- Baseline 2: day-of-year climatology -------------------------------
# Mean rainfall for each day-of-year, computed from TRAINING data only.
climatology = train.groupby(train["time"].dt.day_of_year)["precipitation_sum"].mean()
test_climatology = test["time"].dt.day_of_year.map(climatology).values

y_true = test["target_next_day_rain_mm"].values
rainy_mask = y_true >= RAINY_DAY_MM


def report(name, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    r2 = r2_score(y_true, y_pred)
    mae_rainy = mean_absolute_error(y_true[rainy_mask], y_pred[rainy_mask])
    rmse_rainy = mean_squared_error(y_true[rainy_mask], y_pred[rainy_mask]) ** 0.5
    print(f"\n{name}")
    print(f"  overall:  MAE = {mae:.3f} mm, RMSE = {rmse:.3f} mm, R2 = {r2:.4f}")
    print(f"  rainy days only (n = {rainy_mask.sum()} of {len(y_true)}): "
          f"MAE = {mae_rainy:.3f} mm, RMSE = {rmse_rainy:.3f} mm")
    return {"MAE": mae, "RMSE": rmse, "R2": r2,
            "MAE_rainy": mae_rainy, "RMSE_rainy": rmse_rainy}


print("\n=== Next-day rainfall, test period 2021-2024 ===")
print(f"test days: {len(y_true)}, rainy days (>= {RAINY_DAY_MM} mm): "
      f"{rainy_mask.sum()} ({100 * rainy_mask.mean():.1f}%)")
print(f"mean observed rainfall on test days: {y_true.mean():.3f} mm, "
      f"max: {y_true.max():.1f} mm")
report("Persistence (tomorrow = today)", test_persistence)
report("Day-of-year climatology (train-period means)", test_climatology)
