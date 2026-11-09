"""
MONSOONAI dashboard — data loading (Phase 4)
===============================================
Every number shown in the dashboard comes from the files produced in
Phases 2–3. Nothing here is hard-coded: regression metrics are read
from artifacts/evaluation_summary.json, and classification metrics,
feature importances and year-wise results are *recomputed* from the
saved model artefacts and artifacts/predictions_test.csv using exactly
the same logic as src/evaluate_models.py. If an artefact is missing
or a number disagrees with the evaluation report, the dashboard says
so instead of showing a made-up value.

Data categories (Harsh's binding rule, Phase 1 §13): every dataset
loaded here is labelled with one of
  * "reanalysis"  — Open-Meteo / ERA5 historical reanalysis
  * "observation" — IMD gridded rainfall (interpolated gauge data)
  * "prediction"  — numbers produced by this project's own models
  * "forecast"    — external forecasts (NOT used anywhere in this app)
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# --- Paths -----------------------------------------------------------------
# app/ lives inside the project folder, so the project root is its parent.
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DOCS_DIR = PROJECT_ROOT / "docs"

PROCESSED_CSV = DATA_DIR / "processed" / "mumbai_daily_2000-2024.csv"
IMD_COMPARISON_CSV = DATA_DIR / "processed" / "mumbai_imd_vs_openmeteo_2020.csv"
PREDICTIONS_CSV = ARTIFACTS_DIR / "predictions_test.csv"
SUMMARY_JSON = ARTIFACTS_DIR / "evaluation_summary.json"
SETTINGS_JSON = ARTIFACTS_DIR / "training_settings.json"

# Artefact files the dashboard needs. If any is missing, the app must
# show a clear error, not silently fall back to invented numbers.
REQUIRED_ARTEFACTS = [
    "linear_regression.joblib",
    "random_forest_regressor.joblib",
    "logistic_regression.joblib",
    "random_forest_classifier.joblib",
    "random_forest_heavy_classifier.joblib",
    "feature_columns.joblib",
    "climatology_train.joblib",
]


class DataLoadError(Exception):
    """Raised when a required project file is missing or unreadable."""


def check_required_files():
    """Return a list of required files that are missing (empty = all OK)."""
    missing = []
    for name in [PROCESSED_CSV, IMD_COMPARISON_CSV, PREDICTIONS_CSV,
                 SUMMARY_JSON, SETTINGS_JSON]:
        if not name.exists():
            missing.append(str(name))
    for artefact in REQUIRED_ARTEFACTS:
        if not (ARTIFACTS_DIR / artefact).exists():
            missing.append(str(ARTIFACTS_DIR / artefact))
    return missing


def load_daily():
    """Mumbai daily series (HISTORICAL REANALYSIS, Open-Meteo / ERA5).

    Columns: time, temperature_2m_max/min/mean, precipitation_sum,
    rain_sum, precipitation_hours, wind_speed_10m_max,
    wind_direction_10m_dominant, wind_gusts_10m_max,
    shortwave_radiation_sum, relative_humidity_2m_mean,
    pressure_msl_mean, surface_pressure_mean.
    """
    try:
        df = pd.read_csv(PROCESSED_CSV, parse_dates=["time"])
    except FileNotFoundError as exc:
        raise DataLoadError(
            f"Processed dataset not found: {PROCESSED_CSV}. "
            "Run the Phase 2 data pipeline first (src/prepare_mumbai_daily.py)."
        ) from exc
    return df.sort_values("time").reset_index(drop=True)


def load_imd_comparison():
    """2020 day-by-day IMD vs Open-Meteo comparison (OBSERVATIONAL cross-check)."""
    try:
        # The comparison CSV's first column header is empty (the file
        # starts with a comma), so pandas names it "Unnamed: 0" — rename
        # it to "time" explicitly instead of assuming the header.
        df = pd.read_csv(IMD_COMPARISON_CSV)
        df = df.rename(columns={df.columns[0]: "time"})
        df["time"] = pd.to_datetime(df["time"])
    except FileNotFoundError as exc:
        raise DataLoadError(
            f"IMD comparison file not found: {IMD_COMPARISON_CSV}."
        ) from exc
    return df.sort_values("time").reset_index(drop=True)


def load_test_predictions():
    """Test-period predictions (MODEL PREDICTIONS, 2021–2024, 1,460 rows).

    Columns include the observed next-day rainfall (reanalysis) and the
    prediction of every model for the same target days.
    """
    try:
        df = pd.read_csv(PREDICTIONS_CSV, parse_dates=["time"])
    except FileNotFoundError as exc:
        raise DataLoadError(
            f"Test predictions not found: {PREDICTIONS_CSV}. "
            "Run Phase 3 first (src/train_models.py, src/evaluate_models.py)."
        ) from exc
    return df.sort_values("time").reset_index(drop=True)


def load_summary():
    """Machine-readable evaluation metrics (from Phase 3, unedited)."""
    try:
        return json.loads(SUMMARY_JSON.read_text())
    except FileNotFoundError as exc:
        raise DataLoadError(
            f"Evaluation summary not found: {SUMMARY_JSON}. "
            "Run Phase 3 first (src/evaluate_models.py)."
        ) from exc


def load_settings():
    """Training settings: splits, seed, hyperparameters (from Phase 3)."""
    try:
        return json.loads(SETTINGS_JSON.read_text())
    except FileNotFoundError as exc:
        raise DataLoadError(
            f"Training settings not found: {SETTINGS_JSON}."
        ) from exc


def load_artefact(name):
    """Load one saved model artefact (joblib)."""
    path = ARTIFACTS_DIR / name
    if not path.exists():
        raise DataLoadError(
            f"Model artefact not found: {path}. "
            "Run Phase 3 first (src/train_models.py)."
        )
    return joblib.load(path)


def regression_metrics(summary):
    """Regression table, exactly as saved by Phase 3 (no re-typing)."""
    return summary["regression"]


def compute_regression_metrics(predictions):
    """Regression metrics recomputed at full precision from the saved
    test predictions (artifacts/predictions_test.csv), with exactly the
    same logic as src/evaluate_models.py.

    Why recompute instead of reading evaluation_summary.json? The JSON
    stores metrics rounded to 4 decimals, which is not enough to
    reproduce the report's 3-decimal display in every case (e.g. the
    Random Forest RMSE: full value 11.3675… displays as 11.368, but
    the stored 11.3675 formats as 11.367). Recomputing from the saved
    predictions gives the exact report numbers. The summary JSON is
    still loaded and cross-checked by the test suite.
    """
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    y = predictions["observed_next_day_rain_mm"].values
    rainy = y >= 2.5
    heavy = y >= 64.5
    cols = {
        "persistence": "pred_persistence_mm",
        "climatology": "pred_climatology_mm",
        "linear_regression": "pred_linear_regression_mm",
        "random_forest": "pred_random_forest_mm",
    }
    out = {}
    for key, col in cols.items():
        pred = predictions[col].values
        out[key] = {
            "MAE": mean_absolute_error(y, pred),
            "RMSE": mean_squared_error(y, pred) ** 0.5,
            "R2": r2_score(y, pred),
            "MAE_rainy": mean_absolute_error(y[rainy], pred[rainy]),
            "RMSE_rainy": mean_squared_error(y[rainy], pred[rainy]) ** 0.5,
            "n_rainy": int(rainy.sum()),
            "MAE_heavy": mean_absolute_error(y[heavy], pred[heavy]),
            "n_heavy": int(heavy.sum()),
        }
    return out


# --- Metrics recomputed from the artefacts (never hard-coded) --------------
# These mirror src/evaluate_models.py so the dashboard cannot drift
# from the evaluation report. They are computed once and cached by
# the caller (st.cache_resource) because they load the models.

def compute_classification_metrics(feature_table, feature_columns):
    """Rain/no-rain and heavy-rain classification metrics, test period.

    feature_table: output of feature_engine.build_feature_table(),
    restricted to the test period (2021-01-01 onwards).
    Returns a dict with per-model precision/recall/F1/ROC-AUC and
    confusion matrices, computed with the saved classifier artefacts.
    """
    from sklearn.metrics import (classification_report, confusion_matrix,
                                 roc_auc_score)

    X = feature_table[feature_columns]
    y_true = feature_table["target_next_day_rain_mm"].values
    y_rain = (y_true >= 2.5).astype(int)
    y_heavy = (y_true >= 64.5).astype(int)

    out = {}
    for key, artefact in [
        ("logistic_regression", "logistic_regression.joblib"),
        ("random_forest_classifier", "random_forest_classifier.joblib"),
    ]:
        model = load_artefact(artefact)
        pred = model.predict(X)
        proba = model.predict_proba(X)[:, 1]
        report = classification_report(
            y_rain, pred, digits=4, output_dict=True,
            target_names=["no rain", "rain"], zero_division=0,
        )
        out[key] = {
            "precision_rain": report["rain"]["precision"],
            "recall_rain": report["rain"]["recall"],
            "f1_rain": report["rain"]["f1-score"],
            "accuracy": report["accuracy"],
            "roc_auc": roc_auc_score(y_rain, proba),
            "confusion": confusion_matrix(y_rain, pred).tolist(),
        }

    heavy_model = load_artefact("random_forest_heavy_classifier.joblib")
    pred_h = heavy_model.predict(X)
    proba_h = heavy_model.predict_proba(X)[:, 1]
    report_h = classification_report(
        y_heavy, pred_h, digits=4, output_dict=True,
        target_names=["not heavy", "heavy"], zero_division=0,
    )
    out["heavy_classifier"] = {
        "precision_heavy": report_h["heavy"]["precision"],
        "recall_heavy": report_h["heavy"]["recall"],
        "f1_heavy": report_h["heavy"]["f1-score"],
        "accuracy": report_h["accuracy"],
        "confusion": confusion_matrix(y_heavy, pred_h).tolist(),
        "support_heavy": int(y_heavy.sum()),
    }

    # Regression predictions thresholded at 64.5 mm (as in Phase 3 §5.1).
    lr = load_artefact("linear_regression.joblib")
    rf = load_artefact("random_forest_regressor.joblib")
    persistence = feature_table["rain_t"].values
    thresholded = {}
    for name, pred in [
        ("linear_regression", np.clip(lr.predict(X), 0, None)),
        ("random_forest", np.clip(rf.predict(X), 0, None)),
        ("persistence", persistence),
    ]:
        heavy_pred = pred >= 64.5
        tp = int((y_heavy.astype(bool) & heavy_pred).sum())
        fp = int(((~y_heavy.astype(bool)) & heavy_pred).sum())
        fn = int((y_heavy.astype(bool) & (~heavy_pred)).sum())
        thresholded[name] = {
            "predicted_heavy": int(heavy_pred.sum()),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if (tp + fp) else 0.0,
            "recall": tp / (tp + fn) if (tp + fn) else 0.0,
        }
    out["heavy_thresholded"] = thresholded
    return out


def compute_feature_importance(feature_columns):
    """Random Forest regressor importances + Linear Regression coefficients.

    Taken from the saved artefacts, not typed in by hand.
    """
    rf = load_artefact("random_forest_regressor.joblib")
    importances = sorted(
        zip(feature_columns, rf.feature_importances_),
        key=lambda pair: pair[1], reverse=True,
    )
    lr = load_artefact("linear_regression.joblib")
    # The LR artefact is a pipeline (StandardScaler + LinearRegression);
    # coefficients are on standardised features.
    lr_model = lr.steps[-1][1]
    coefficients = sorted(
        zip(feature_columns, lr_model.coef_),
        key=lambda pair: abs(pair[1]), reverse=True,
    )
    return {"random_forest": importances, "linear_regression": coefficients}


def year_wise_metrics(predictions):
    """Regression MAE / RMSE / R² per test year, per model.

    Computed from artifacts/predictions_test.csv (observed + predicted
    columns), so the numbers always match the saved predictions.
    """
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    df = predictions.copy()
    df["year"] = df["time"].dt.year
    models = {
        "Persistence": "pred_persistence_mm",
        "Climatology": "pred_climatology_mm",
        "Linear Regression": "pred_linear_regression_mm",
        "Random Forest": "pred_random_forest_mm",
    }
    rows = []
    for year, group in df.groupby("year"):
        row = {"year": int(year), "days": len(group)}
        for label, col in models.items():
            row[f"{label} MAE"] = mean_absolute_error(
                group["observed_next_day_rain_mm"], group[col])
            row[f"{label} RMSE"] = mean_squared_error(
                group["observed_next_day_rain_mm"], group[col]) ** 0.5
            row[f"{label} R²"] = r2_score(
                group["observed_next_day_rain_mm"], group[col])
        rows.append(row)
    return pd.DataFrame(rows)


def error_by_month(predictions):
    """Mean absolute error by month of the cutoff day (t), test period.

    Note: predictions_test.csv is stored by cutoff day t, so the month
    here is the month of t (the day the prediction was made), matching
    src/evaluate_models.py.
    """
    df = predictions.copy()
    df["month"] = df["time"].dt.month
    out = pd.DataFrame({
        "month": range(1, 13),
        "Persistence": [np.nan] * 12,
        "Linear Regression": [np.nan] * 12,
        "Random Forest": [np.nan] * 12,
        "Mean observed (mm)": [np.nan] * 12,
    })
    for month, group in df.groupby("month"):
        idx = month - 1
        for label, col in [
            ("Persistence", "pred_persistence_mm"),
            ("Linear Regression", "pred_linear_regression_mm"),
            ("Random Forest", "pred_random_forest_mm"),
        ]:
            out.loc[idx, label] = np.abs(
                group["observed_next_day_rain_mm"] - group[col]).mean()
        out.loc[idx, "Mean observed (mm)"] = group[
            "observed_next_day_rain_mm"].mean()
    return out


def worst_misses(predictions, n=10):
    """Worst Random Forest misses in the test period, by |error|."""
    df = predictions.copy()
    df["error_rf_mm"] = (
        df["pred_random_forest_mm"] - df["observed_next_day_rain_mm"])
    df["abs_error_mm"] = df["error_rf_mm"].abs()
    cols = ["time", "observed_next_day_rain_mm",
            "pred_random_forest_mm", "pred_linear_regression_mm",
            "error_rf_mm", "abs_error_mm"]
    return df.sort_values("abs_error_mm", ascending=False).head(n)[cols]
