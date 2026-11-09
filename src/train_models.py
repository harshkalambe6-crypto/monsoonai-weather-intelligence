"""
MONSOONAI — Phase 3 model training (Linear Regression + Random Forest)
========================================================================
Trains, for next-day (t+1) Mumbai rainfall:
  * Regression: Linear Regression (scaled pipeline) and Random Forest
    Regressor — target is rainfall in mm.
  * Classification: rain / no-rain (target >= 2.5 mm, IMD-verified)
    with Logistic Regression and Random Forest Classifier.
  * Heavy-rain classification: target >= 64.5 mm (IMD "heavy" band)
    with Random Forest Classifier — reported honestly; if the class
    is too rare to learn, the metrics will say so.

What this script does NOT do: no XGBoost, no LSTM, no dashboard,
no deployment. Those are out of scope for Phase 3.

Splits (chronological, never shuffled — identical to Phase 2):
  * train      2000-01-01 to 2017-12-31  (fit models; climatology too)
  * validation 2018-01-01 to 2020-12-31  (tune / choose hyperparameters)
  * test       2021-01-01 to 2024-12-31  (final evaluation, in
    src/evaluate_models.py — this script only SAVES the models and
    their validation scores; test evaluation happens once, separately)

Hyperparameter search: a SMALL grid, scored on the validation years
only — never on the test set.
  * Random Forest Regressor: max_depth {None, 10, 20} x
    n_estimators {200, 400}  (6 combinations, scored by validation MAE)
  * Random Forest Classifier: same grid, scored by validation F1

Artefacts saved to artifacts/ (joblib): the fitted models, the
feature-column list, and the train-only climatology series, so the
evaluation script (and later the dashboard) can load exactly the
models that were trained here.

Run:  python3 src/train_models.py
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import f1_score, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import FEATURE_COLUMNS, HEAVY_MM, RAINY_DAY_MM, build_features

RANDOM_STATE = 42
DATA = "data/processed/mumbai_daily_2000-2024.csv"
ARTIFACTS = Path("artifacts")
ARTIFACTS.mkdir(exist_ok=True)

# --- Load data and build features --------------------------------------
df = pd.read_csv(DATA, parse_dates=["time"]).sort_values("time").reset_index(drop=True)

# Climatology (fix 2): day-of-year mean rainfall from TRAINING data only.
train_raw = df[df["time"] < "2018-01-01"]
climatology_train = train_raw.groupby(
    train_raw["time"].dt.day_of_year)["precipitation_sum"].mean()

feat = build_features(df, climatology_train)
print(f"feature rows: {len(feat)} "
      f"({feat['time'].min().date()} to {feat['time'].max().date()})")
print(f"features: {len(FEATURE_COLUMNS)}")

train = feat[feat["time"] < "2018-01-01"]
valid = feat[(feat["time"] >= "2018-01-01") & (feat["time"] < "2021-01-01")]
test = feat[feat["time"] >= "2021-01-01"]
print(f"train rows: {len(train)}, validation rows: {len(valid)}, "
      f"test rows: {len(test)}")

X_train = train[FEATURE_COLUMNS]
X_valid = valid[FEATURE_COLUMNS]
y_train = train["target_next_day_rain_mm"].values
y_valid = valid["target_next_day_rain_mm"].values

# --- Regression: Linear Regression --------------------------------------
lr = Pipeline([("scaler", StandardScaler()),
               ("model", LinearRegression())])
lr.fit(X_train, y_train)
lr_val_mae = mean_absolute_error(y_valid, lr.predict(X_valid))
print(f"\nLinear Regression — validation MAE: {lr_val_mae:.3f} mm")

# --- Regression: Random Forest (small grid, validation only) -----------
rf_grid = [
    {"max_depth": d, "n_estimators": n}
    for d in (None, 10, 20) for n in (200, 400)
]
rf_results = []
for params in rf_grid:
    rf = RandomForestRegressor(random_state=RANDOM_STATE,
                               n_jobs=-1, **params)
    rf.fit(X_train, y_train)
    mae = mean_absolute_error(y_valid, rf.predict(X_valid))
    rf_results.append((mae, params))
    print(f"RF regressor {params} — validation MAE: {mae:.3f} mm")
rf_results.sort(key=lambda r: r[0])
best_rf_params = rf_results[0][1]
print(f"Best RF regressor (validation): {best_rf_params} "
      f"MAE {rf_results[0][0]:.3f} mm")

rf = RandomForestRegressor(random_state=RANDOM_STATE,
                           n_jobs=-1, **best_rf_params)
rf.fit(X_train, y_train)

# --- Classification: rain / no-rain (>= 2.5 mm) ------------------------
y_train_cls = (y_train >= RAINY_DAY_MM).astype(int)
y_valid_cls = (y_valid >= RAINY_DAY_MM).astype(int)
print(f"\nRain/no-rain: train positives {y_train_cls.sum()} of "
      f"{len(y_train_cls)}, validation positives {y_valid_cls.sum()} "
      f"of {len(y_valid_cls)}")

logreg = Pipeline([("scaler", StandardScaler()),
                   ("model", LogisticRegression(max_iter=1000,
                                                random_state=RANDOM_STATE))])
logreg.fit(X_train, y_train_cls)
print(f"Logistic Regression — validation F1: "
      f"{f1_score(y_valid_cls, logreg.predict(X_valid)):.4f}")

rfc_grid_results = []
for params in rf_grid:
    rfc = RandomForestClassifier(random_state=RANDOM_STATE,
                                 n_jobs=-1, class_weight="balanced",
                                 **params)
    rfc.fit(X_train, y_train_cls)
    f1 = f1_score(y_valid_cls, rfc.predict(X_valid))
    rfc_grid_results.append((f1, params))
    print(f"RF classifier {params} — validation F1: {f1:.4f}")
rfc_grid_results.sort(key=lambda r: -r[0])
best_rfc_params = rfc_grid_results[0][1]
print(f"Best RF classifier (validation): {best_rfc_params} "
      f"F1 {rfc_grid_results[0][0]:.4f}")

rfc = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1,
                             class_weight="balanced", **best_rfc_params)
rfc.fit(X_train, y_train_cls)

# --- Heavy-rain classification (>= 64.5 mm) ---------------------------
# Heavy days are rare: count them first, so the result is read honestly.
y_train_heavy = (y_train >= HEAVY_MM).astype(int)
y_valid_heavy = (y_valid >= HEAVY_MM).astype(int)
print(f"\nHeavy rain (>= {HEAVY_MM} mm): train positives "
      f"{y_train_heavy.sum()} of {len(y_train_heavy)}, validation "
      f"positives {y_valid_heavy.sum()} of {len(y_valid_heavy)}")
rfc_heavy = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1,
                                   class_weight="balanced",
                                   **best_rfc_params)
rfc_heavy.fit(X_train, y_train_heavy)
print(f"RF heavy classifier — validation F1: "
      f"{f1_score(y_valid_heavy, rfc_heavy.predict(X_valid)):.4f} "
      f"(on only {y_valid_heavy.sum()} positive validation days)")

# --- Save artefacts ------------------------------------------------------
joblib.dump(lr, ARTIFACTS / "linear_regression.joblib")
joblib.dump(rf, ARTIFACTS / "random_forest_regressor.joblib")
joblib.dump(logreg, ARTIFACTS / "logistic_regression.joblib")
joblib.dump(rfc, ARTIFACTS / "random_forest_classifier.joblib")
joblib.dump(rfc_heavy, ARTIFACTS / "random_forest_heavy_classifier.joblib")
joblib.dump(FEATURE_COLUMNS, ARTIFACTS / "feature_columns.joblib")
joblib.dump(climatology_train, ARTIFACTS / "climatology_train.joblib")

settings = {
    "random_state": RANDOM_STATE,
    "splits": {"train": "2000-01-01 to 2017-12-31",
               "validation": "2018-01-01 to 2020-12-31",
               "test": "2021-01-01 to 2024-12-31"},
    "input_window": "t-7..t (widened in Phase 3; see src/features.py)",
    "rainy_day_mm": RAINY_DAY_MM,
    "heavy_mm": HEAVY_MM,
    "days_since_rain_cap": 30,
    "climatology": "day-of-year mean rainfall from TRAINING data only",
    "rf_regressor_grid": [str(p) for _, p in rf_results],
    "rf_regressor_best": best_rf_params,
    "rf_regressor_validation_mae_mm": round(rf_results[0][0], 3),
    "linear_regression_validation_mae_mm": round(lr_val_mae, 3),
    "rf_classifier_grid_f1": [(round(f, 4), p) for f, p in rfc_grid_results],
    "rf_classifier_best": best_rfc_params,
    "feature_columns": FEATURE_COLUMNS,
}
(ARTIFACTS / "training_settings.json").write_text(json.dumps(settings, indent=2))
print("\nArtefacts saved to artifacts/ (models, feature list, "
      "climatology, training_settings.json)")
