"""
MONSOONAI dashboard — next-day prediction (Phase 4)
====================================================
Generates a next-day (t+1) rainfall prediction from the saved Phase 3
model artefacts, using only data dated t or earlier.

What this module does NOT do:
  * It never fetches live weather and never invents a current value.
    The prediction is made from the local processed dataset
    (data/processed/mumbai_daily_2000-2024.csv). If that file ends on
    31 Dec 2024, the "latest" prediction is for 1 Jan 2025 and is
    labelled a historical-data demonstration, not a live forecast.
  * It never uses information dated after the cutoff (23:59
    Asia/Kolkata on day t). Features come from feature_engine, which
    reuses the Phase 3 definitions (leakage-audited, no FAILs).
  * It never presents a historical test prediction as a live forecast.
    Callers must label the output with its data date and category.

Model selection:
  * "Random Forest"  -> random_forest_regressor + RF rain classifier
                        + RF heavy-rain classifier
  * "Linear Regression" -> linear_regression + Logistic Regression
                        rain classifier (heavy probability still comes
                        from the RF heavy classifier, labelled as such)
  * "Persistence"     -> tomorrow = today (no probability available)
  * "Climatology"     -> train-period day-of-year mean (no probability)
"""

import numpy as np
import pandas as pd

from data_loader import load_artefact

REGRESSION_MODELS = {
    "Random Forest": "random_forest_regressor.joblib",
    "Linear Regression": "linear_regression.joblib",
}
CLASSIFIERS = {
    "Random Forest": "random_forest_classifier.joblib",
    "Linear Regression": "logistic_regression.joblib",
}
HEAVY_CLASSIFIER = "random_forest_heavy_classifier.joblib"

# IMD rainfall bands (mm / 24 h), verified in Phase 1 §5.
IMD_BANDS = [
    (204.4, "Extremely heavy (> 204.4 mm)"),
    (115.6, "Very heavy (115.6–204.4 mm)"),
    (64.5, "Heavy (64.5–115.5 mm)"),
    (15.6, "Moderate (15.6–64.4 mm)"),
    (2.5, "Light rain (2.5–15.5 mm)"),
    (0.0, "Trace / light (< 2.5 mm)"),
]


def imd_band(rain_mm):
    """IMD rainfall band for a rainfall amount in mm."""
    for threshold, label in IMD_BANDS:
        if rain_mm >= threshold:
            return label
    return "No rain (0 mm)"


def predict_next_day(feature_row, model_name, climatology_value=None,
                     rain_today=None):
    """Predict t+1 rainfall for one cutoff day.

    feature_row: one-row DataFrame with the 27 feature columns.
    model_name: one of "Random Forest", "Linear Regression",
        "Persistence", "Climatology".
    climatology_value: day-of-year mean rainfall (train period only),
        required for the Climatology model.
    rain_today: rainfall on day t in mm, required for Persistence.
    Returns a dict with the predicted amount, the rain probability
    (or None), the heavy-rain probability (or None), and notes.
    """
    if feature_row is None or feature_row.empty:
        raise ValueError("No feature row available for the chosen cutoff day.")
    result = {"model": model_name, "rain_probability": None,
              "heavy_probability": None, "notes": []}

    if model_name in REGRESSION_MODELS:
        model = load_artefact(REGRESSION_MODELS[model_name])
        amount = float(model.predict(feature_row)[0])
        result["amount_mm"] = max(amount, 0.0)  # rainfall cannot be negative
        classifier = load_artefact(CLASSIFIERS[model_name])
        result["rain_probability"] = float(
            classifier.predict_proba(feature_row)[0, 1])
        heavy_model = load_artefact(HEAVY_CLASSIFIER)
        result["heavy_probability"] = float(
            heavy_model.predict_proba(feature_row)[0, 1])
        result["notes"].append(
            "Rain probability from the matching rain/no-rain classifier; "
            "heavy-rain probability from the Random Forest heavy-rain "
            "classifier (precision 0.137 on the test set — treat with "
            "caution, see the Extreme Rainfall page).")
    elif model_name == "Persistence":
        if rain_today is None:
            raise ValueError("Persistence needs today's rainfall.")
        result["amount_mm"] = float(rain_today)
        result["notes"].append(
            "Baseline: tomorrow's rainfall = today's rainfall. "
            "No probability is available for this baseline.")
    elif model_name == "Climatology":
        if climatology_value is None:
            raise ValueError("Climatology needs the train-period day-of-year mean.")
        result["amount_mm"] = float(climatology_value)
        result["notes"].append(
            "Baseline: the training-period (2000–2017) mean rainfall for "
            "this day of the year. No probability is available.")
    else:
        raise ValueError(f"Unknown model: {model_name}")

    result["band"] = imd_band(result["amount_mm"])
    return result
