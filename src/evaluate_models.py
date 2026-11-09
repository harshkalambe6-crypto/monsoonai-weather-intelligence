"""
MONSOONAI — Phase 3 model evaluation (TEST SET, once only)
===========================================================
Loads the models trained by src/train_models.py and evaluates them on
the untouched test period 2021-01-01 to 2024-12-31, alongside the
Phase 2 baselines (persistence and day-of-year climatology) on the
SAME test rows, with the SAME metrics.

This script runs the test evaluation ONCE. It does not tune anything:
if a number here is bad, it is reported as bad — the models are not
re-trained to chase a better test score.

Metrics reported (test period, unless stated):
  * Regression: MAE, RMSE, R2 — overall and on rainy days only
    (observed t+1 >= 2.5 mm, the IMD-verified threshold).
  * Heavy rain (>= 64.5 mm): observed count, predicted count,
    precision / recall / F1 for the heavy class, MAE on heavy days.
  * Classification (rain / no-rain): precision, recall, F1,
    confusion matrix, ROC-AUC.
  * Residual analysis: error by month, error vs observed rainfall,
    top 10 worst test days (dates, observed, predicted).
  * Plots saved to docs/figures/: actual-vs-predicted scatter,
    test-period time series, error by month, residuals vs observed.

IMPORTANT — what these numbers are (Harsh's clarification 6):
every metric here is performance against Open-Meteo / ERA5 REANALYSIS
rainfall, not against rain-gauge observations. The IMD cross-check
(Phase 2) shows reanalysis underestimates gauge-based annual rainfall
by ~22% and smooths extremes, so real-world skill against gauges is
expected to be LOWER, especially for heavy rain. No number in this
script's output is observational accuracy.

Outputs:
  * docs/model-evaluation-report.md  (full report, written by hand
    from the numbers this script prints — see the script output)
  * artifacts/predictions_test.csv   (test rows with all predictions)
  * docs/figures/*.png               (plots)

Run:  python3 src/evaluate_models.py
"""

import json
import sys
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.metrics import (classification_report, confusion_matrix,
                             mean_absolute_error, mean_squared_error,
                             r2_score, roc_auc_score)

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import HEAVY_MM, RAINY_DAY_MM, build_features

RANDOM_STATE = 42
DATA = "data/processed/mumbai_daily_2000-2024.csv"
ARTIFACTS = Path("artifacts")
FIGURES = Path("docs/figures")
FIGURES.mkdir(parents=True, exist_ok=True)

# --- Rebuild the feature table exactly as in training ------------------
df = pd.read_csv(DATA, parse_dates=["time"]).sort_values("time").reset_index(drop=True)
climatology_train = joblib.load(ARTIFACTS / "climatology_train.joblib")
feat = build_features(df, climatology_train)
feature_columns = joblib.load(ARTIFACTS / "feature_columns.joblib")

test = feat[feat["time"] >= "2021-01-01"].reset_index(drop=True)
X_test = test[feature_columns]
y_true = test["target_next_day_rain_mm"].values
dates = test["time"]
print(f"test rows: {len(test)} "
      f"({dates.min().date()} to {dates.max().date()})")
print(f"test rainy days (>= {RAINY_DAY_MM} mm): {(y_true >= RAINY_DAY_MM).sum()} "
      f"({100 * (y_true >= RAINY_DAY_MM).mean():.1f}%)")
print(f"test heavy days (>= {HEAVY_MM} mm): {(y_true >= HEAVY_MM).sum()}")
print(f"test mean observed rainfall: {y_true.mean():.3f} mm/day, "
      f"max: {y_true.max():.1f} mm")

# --- Baselines on the SAME test rows ------------------------------------
# Persistence: tomorrow = today (rain on day t).
persistence = test["rain_t"].values
# Climatology: train-period day-of-year mean (the feature column).
climatology = test["climatology_doy"].values


def regression_metrics(name, y_pred):
    """MAE / RMSE / R2 overall and on rainy days only. Returns a dict."""
    rainy = y_true >= RAINY_DAY_MM
    heavy = y_true >= HEAVY_MM
    m = {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": mean_squared_error(y_true, y_pred) ** 0.5,
        "R2": r2_score(y_true, y_pred),
        "MAE_rainy": mean_absolute_error(y_true[rainy], y_pred[rainy]),
        "RMSE_rainy": mean_squared_error(y_true[rainy], y_pred[rainy]) ** 0.5,
        "n_rainy": int(rainy.sum()),
        "MAE_heavy": (mean_absolute_error(y_true[heavy], y_pred[heavy])
                      if heavy.sum() else float("nan")),
        "n_heavy": int(heavy.sum()),
    }
    print(f"\n{name}")
    print(f"  overall:       MAE = {m['MAE']:.3f} mm, "
          f"RMSE = {m['RMSE']:.3f} mm, R2 = {m['R2']:.4f}")
    print(f"  rainy days only (n = {m['n_rainy']}): "
          f"MAE = {m['MAE_rainy']:.3f} mm, RMSE = {m['RMSE_rainy']:.3f} mm")
    print(f"  heavy days only (n = {m['n_heavy']}): "
          f"MAE = {m['MAE_heavy']:.3f} mm")
    return m


results = {}
results["persistence"] = regression_metrics("Persistence (tomorrow = today)",
                                            persistence)
results["climatology"] = regression_metrics(
    "Day-of-year climatology (train-period means)", climatology)

# --- Trained models -------------------------------------------------------
lr = joblib.load(ARTIFACTS / "linear_regression.joblib")
rf = joblib.load(ARTIFACTS / "random_forest_regressor.joblib")
logreg = joblib.load(ARTIFACTS / "logistic_regression.joblib")
rfc = joblib.load(ARTIFACTS / "random_forest_classifier.joblib")
rfc_heavy = joblib.load(ARTIFACTS / "random_forest_heavy_classifier.joblib")

pred_lr = lr.predict(X_test)
pred_rf = rf.predict(X_test)
# Rainfall cannot be negative — clip at zero (a modelling choice, not
# a metric change: it can only move predictions towards reality).
pred_lr = np.clip(pred_lr, 0, None)
pred_rf = np.clip(pred_rf, 0, None)
results["linear_regression"] = regression_metrics("Linear Regression", pred_lr)
results["random_forest"] = regression_metrics("Random Forest Regressor", pred_rf)

# --- Heavy-rain performance (regression predictions thresholded) --------
print("\n=== Heavy rain (>= 64.5 mm) — regression predictions "
      "thresholded at 64.5 mm ===")
heavy_true = y_true >= HEAVY_MM
for name, pred in [("Linear Regression", pred_lr),
                   ("Random Forest", pred_rf),
                   ("Persistence", persistence)]:
    heavy_pred = pred >= HEAVY_MM
    tp = int((heavy_true & heavy_pred).sum())
    fp = int(((~heavy_true) & heavy_pred).sum())
    fn = int((heavy_true & (~heavy_pred)).sum())
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    print(f"{name}: observed heavy {heavy_true.sum()}, predicted heavy "
          f"{heavy_pred.sum()}, TP {tp}, FP {fp}, FN {fn}, "
          f"precision {prec:.3f}, recall {rec:.3f}")

# --- Classification: rain / no-rain --------------------------------------
print("\n=== Rain / no-rain classification (>= 2.5 mm) ===")
y_cls = (y_true >= RAINY_DAY_MM).astype(int)
for name, model in [("Logistic Regression", logreg),
                    ("Random Forest Classifier", rfc)]:
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    print(f"\n{name}")
    print(classification_report(y_cls, pred, digits=4,
                                target_names=["no rain", "rain"]))
    print("Confusion matrix [[TN, FP], [FN, TP]]:")
    print(confusion_matrix(y_cls, pred))
    print(f"ROC-AUC: {roc_auc_score(y_cls, proba):.4f}")

# --- Heavy-rain classifier ------------------------------------------------
print("\n=== Heavy-rain classification (>= 64.5 mm) — Random Forest ===")
y_heavy = (y_true >= HEAVY_MM).astype(int)
pred_heavy = rfc_heavy.predict(X_test)
print(classification_report(y_heavy, pred_heavy, digits=4,
                            target_names=["not heavy", "heavy"],
                            zero_division=0))
print("Confusion matrix [[TN, FP], [FN, TP]]:")
print(confusion_matrix(y_heavy, pred_heavy))

# --- Residual analysis ----------------------------------------------------
print("\n=== Residual analysis (Random Forest, test period) ===")
resid_rf = pred_rf - y_true
resid_lr = pred_lr - y_true
worst = (pd.DataFrame({"date": dates, "observed_mm": y_true,
                       "predicted_rf_mm": pred_rf,
                       "predicted_lr_mm": pred_lr,
                       "error_rf_mm": resid_rf})
         .assign(abs_error=lambda d: d["error_rf_mm"].abs())
         .sort_values("abs_error", ascending=False).head(10))
print("Top 10 worst Random Forest misses (by |error|):")
print(worst.to_string(index=False))
print(f"\nResidual bias (mean predicted - observed): "
      f"RF {resid_rf.mean():+.3f} mm, LR {resid_lr.mean():+.3f} mm")
print(f"RF residuals: {np.sum(resid_rf > 0)} over-predictions, "
      f"{np.sum(resid_rf < 0)} under-predictions of {len(resid_rf)} days")
print(f"RF predicted max: {pred_rf.max():.1f} mm vs observed max "
      f"{y_true.max():.1f} mm")
print(f"LR predicted max: {pred_lr.max():.1f} mm vs observed max "
      f"{y_true.max():.1f} mm")

# Error by month (mean absolute error, test period).
months = dates.dt.month
err_by_month = pd.DataFrame({
    "month": months,
    "abs_err_persistence": np.abs(persistence - y_true),
    "abs_err_lr": np.abs(pred_lr - y_true),
    "abs_err_rf": np.abs(pred_rf - y_true),
    "observed": y_true,
}).groupby("month").mean(numeric_only=True)
print("\nMean absolute error by month (mm):")
print(err_by_month.round(2).to_string())

# --- Save predictions ------------------------------------------------------
out = test[["time"]].copy()
out["observed_next_day_rain_mm"] = y_true
out["pred_persistence_mm"] = persistence
out["pred_climatology_mm"] = climatology
out["pred_linear_regression_mm"] = pred_lr
out["pred_random_forest_mm"] = pred_rf
out["pred_rain_prob_logreg"] = logreg.predict_proba(X_test)[:, 1]
out["pred_rain_prob_rf"] = rfc.predict_proba(X_test)[:, 1]
out["pred_heavy_prob_rf"] = rfc_heavy.predict_proba(X_test)[:, 1]
out.to_csv(ARTIFACTS / "predictions_test.csv", index=False)
print("\nPredictions saved to artifacts/predictions_test.csv")

# --- Plots -----------------------------------------------------------------
plt.rcParams.update({"font.size": 10})

# 1. Actual vs predicted scatter (LR and RF).
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, pred, title in [(axes[0], pred_lr, "Linear Regression"),
                        (axes[1], pred_rf, "Random Forest")]:
    ax.scatter(y_true, pred, s=8, alpha=0.45)
    lim = max(y_true.max(), pred.max()) * 1.05
    ax.plot([0, lim], [0, lim], "r--", linewidth=1, label="perfect prediction")
    ax.set_xlabel("Observed next-day rainfall (mm) — reanalysis")
    ax.set_ylabel("Predicted next-day rainfall (mm)")
    ax.set_title(f"{title}\ntest 2021–2024 (n = {len(y_true)})")
    ax.legend()
fig.tight_layout()
fig.savefig(FIGURES / "actual_vs_predicted_scatter.png", dpi=150)
plt.close(fig)

# 2. Test-period time series (observed vs both models).
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(dates, y_true, label="Observed (reanalysis)", linewidth=0.8)
ax.plot(dates, pred_lr, label="Linear Regression", linewidth=0.8, alpha=0.8)
ax.plot(dates, pred_rf, label="Random Forest", linewidth=0.8, alpha=0.8)
ax.set_xlabel("Date (prediction day t+1)")
ax.set_ylabel("Rainfall (mm)")
ax.set_title("Next-day rainfall, test period 2021–2024 — observed vs predicted")
ax.legend()
fig.tight_layout()
fig.savefig(FIGURES / "test_timeseries.png", dpi=150)
plt.close(fig)

# 3. Mean absolute error by month.
fig, ax = plt.subplots(figsize=(10, 4))
x = np.arange(1, 13)
width = 0.25
ax.bar(x - width, err_by_month["abs_err_persistence"], width, label="Persistence")
ax.bar(x, err_by_month["abs_err_lr"], width, label="Linear Regression")
ax.bar(x + width, err_by_month["abs_err_rf"], width, label="Random Forest")
ax.set_xticks(x)
ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
ax.set_xlabel("Month of the predicted day")
ax.set_ylabel("Mean absolute error (mm)")
ax.set_title("Mean absolute error by month — test period 2021–2024")
ax.legend()
fig.tight_layout()
fig.savefig(FIGURES / "error_by_month.png", dpi=150)
plt.close(fig)

# 4. Residuals vs observed rainfall (Random Forest).
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(y_true, resid_rf, s=8, alpha=0.45)
ax.axhline(0, color="r", linestyle="--", linewidth=1)
ax.set_xlabel("Observed next-day rainfall (mm) — reanalysis")
ax.set_ylabel("Residual, predicted − observed (mm)")
ax.set_title("Random Forest residuals vs observed rainfall — test 2021–2024")
fig.tight_layout()
fig.savefig(FIGURES / "residuals_vs_observed.png", dpi=150)
plt.close(fig)

print("Plots saved to docs/figures/")

# --- Machine-readable metrics ----------------------------------------------
summary = {
    "test_period": "2021-01-01 to 2024-12-31",
    "test_rows": int(len(y_true)),
    "test_rainy_days_ge_2.5mm": int((y_true >= RAINY_DAY_MM).sum()),
    "test_heavy_days_ge_64.5mm": int((y_true >= HEAVY_MM).sum()),
    "regression": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                        for kk, vv in v.items()}
                   for k, v in results.items()},
    "settings": json.loads((ARTIFACTS / "training_settings.json").read_text()),
}
(ARTIFACTS / "evaluation_summary.json").write_text(json.dumps(summary, indent=2))
print("Metrics saved to artifacts/evaluation_summary.json")
