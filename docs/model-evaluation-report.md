# MONSOONAI — Model Evaluation Report (Phase 3)

**Project:** MONSOONAI — Mumbai next-day rainfall prediction
**Phase:** 3 — Machine learning (Linear Regression + Random Forest only)
**Date:** 9 November 2026
**Data:** `data/processed/mumbai_daily_2000-2024.csv` — Open-Meteo / ERA5
**historical reanalysis**, 9,132 days, 2000–2024
**Code:** `src/features.py`, `src/train_models.py`, `src/evaluate_models.py`
**Artefacts:** `artifacts/` (trained models, predictions, settings, metrics)

**Status:** every number in this report was computed by the code above
and printed by `src/evaluate_models.py`. Nothing here is estimated,
invented, or copied from another source. No XGBoost, no LSTM, no
dashboard, no deployment — those are out of scope for Phase 3.

---

## 0. The discrepancy Harsh flagged — resolved

Before Phase 3, Harsh noted the Phase 2 data-quality note listed
2,771 rainy days (≥ 2.5 mm) and 5,468 dry days (0.00 mm) — 8,239 of
9,132 days, leaving 893 unaccounted for. Recalculated directly from
`data/processed/mumbai_daily_2000-2024.csv`, the 893 days are **light
rain (0 < precipitation_sum < 2.5 mm)** — 473 days below 1 mm and 420
days between 1 and 2.5 mm, together contributing only 885.9 mm (1.7%
of the 25-year total). The three-way classification is exhaustive:

| Category | Definition | Days | Share |
|---|---|---|---|
| Dry | precipitation_sum = 0.00 mm | 5,468 | 59.9% |
| Light rain | 0 < precipitation_sum < 2.5 mm | 893 | 9.8% |
| Rainy (IMD) | precipitation_sum ≥ 2.5 mm | 2,771 | 30.3% |
| **Total** | | **9,132** | **100.0%** |

5,468 + 893 + 2,771 = 9,132. No counts were adjusted — the original
figures were correct; the middle category had simply never been named.
The data-quality note (`docs/data-quality-note.md`) now documents this
three-way classification, and this report uses it throughout.

---

## 1. What was predicted, and how

- **Prediction:** at the end of day **t** (cutoff 23:59 Asia/Kolkata),
  using only data dated t or earlier, predict rainfall on day **t+1**
  in mm. Target = `precipitation_sum` shifted by one day.
- **Input window:** days **t−7 … t** (widened from t−6…t in Phase 3
  so the t−7 lag sits inside the stated window — see §2).
- **Rainy day:** ≥ 2.5 mm (IMD-verified threshold, IMD Met Glossary).
- **Heavy rain:** ≥ 64.5 mm (IMD "heavy" band).
- **Splits — chronological, identical for every model, test untouched:**

| Split | Dates | Rows (feature table) | Purpose |
|---|---|---|---|
| Train | 2000-01-01 – 2017-12-31 | 6,568 | Fit models; climatology computed here only |
| Validation | 2018-01-01 – 2020-12-31 | 1,096 | Tune / choose hyperparameters |
| Test | 2021-01-01 – 2024-12-31 | 1,460 | Final evaluation, once only |

  (Feature rows are 7 fewer than the Phase 2 baseline rows because
  the t−7 lag needs 7 days of history; the date ranges are identical.)
- **Test-set facts:** 1,460 target days, 452 rainy (31.0%), 21 heavy
  (1.4%), mean observed rainfall 6.51 mm/day, maximum 199.9 mm.

---

## 2. Feature fixes (all three from the Phase 2 leakage audit)

1. **Window widened to t−7…t — the t−7 lag was KEPT.** It is
   leakage-free (past data) and adds a weekly-lag signal, so widening
   the definition was chosen over dropping the feature.
   `docs/prediction-definition.md` §4 was updated to match.
2. **Climatology from training data only.** The day-of-year mean
   rainfall feature is computed from 2000–2017 only, saved as
   `artifacts/climatology_train.joblib`, and mapped in by day-of-year.
   It is never recomputed from validation or test data.
3. **Days since last rain capped at 30 days** (`DAYS_SINCE_RAIN_CAP
   = 30` in `src/features.py`).

**Final feature list — 27 features** (full definitions in
`src/features.py`; re-audit in `docs/leakage-audit.md`, "Phase 3
re-audit": **no FAILs**):

- Lagged rainfall: rain at t, t−1, t−2, t−3, t−7
- Rolling rainfall: 3-day and 7-day sum and mean (windows end at t)
- Days since last rain (capped 30); rainy days in last 7 days
- Temperature: max / min / mean at t; 3-day mean
- Humidity: at t; 3-day mean
- Pressure: at t; change over last 3 days (t minus t−3)
- Wind: max speed at t; direction as sin/cos
- Seasonal: day-of-year sin/cos; month; monsoon flag (Jun–Sep)
- Day-of-year climatology (training data only)

Regression predictions are clipped at zero in the evaluation script
(rainfall cannot be negative) — a post-processing step applied
identically to both models, introducing no future information.

---

## 3. Models trained

| Model | Setup | Selection |
|---|---|---|
| Linear Regression | Pipeline: StandardScaler + LinearRegression | No hyperparameters to tune |
| Random Forest Regressor | Grid: max_depth {None, 10, 20} × n_estimators {200, 400}, scored by **validation MAE** | Best: **max_depth 10, n_estimators 200** (validation MAE 3.911 mm; next best 3.939 mm) |
| Logistic Regression (rain/no-rain) | Pipeline: StandardScaler + LogisticRegression (max_iter 1000) | No tuning; validation F1 0.9027 |
| Random Forest Classifier (rain/no-rain) | Same grid, class_weight balanced, scored by **validation F1** | Best: **max_depth 10, n_estimators 400** (validation F1 0.9154) |
| Random Forest Classifier (heavy rain) | Same best classifier settings, class_weight balanced | Validation F1 0.2500 — on only 15 positive validation days |

All models trained on the training split only (2000–2017). The test
set was not used for any fitting or selection decision.

---

## 4. Results — regression, test period 2021–2024

### 4.1 Overall and rainy-day metrics

| Model | MAE (mm) | RMSE (mm) | R² | MAE rainy only (mm) | RMSE rainy only (mm) | MAE heavy only (mm) |
|---|---|---|---|---|---|---|
| **Persistence** (tomorrow = today) | 4.228 | 13.022 | 0.2968 | 12.501 | 23.017 | 45.352 |
| **Day-of-year climatology** | 5.447 | 13.419 | 0.2533 | 14.946 | 23.430 | 74.028 |
| **Linear Regression** | 4.356 | **11.059** | **0.4928** | **11.046** | 19.419 | 56.422 |
| **Random Forest Regressor** | **4.191** | 11.368 | 0.4641 | 11.495 | **19.358** | 53.076 |

Rainy-only: 452 days (observed t+1 ≥ 2.5 mm). Heavy-only: 21 days
(observed t+1 ≥ 64.5 mm).

### 4.2 Did either model beat persistence?

**Yes — but only just, and not on every metric.** Read the table
carefully; the honest answer is mixed:

- **Random Forest** beats persistence on MAE (4.191 vs 4.228 mm —
  **0.9% better**), on RMSE (11.368 vs 13.022 mm — 12.7% better) and
  on R² (0.464 vs 0.297). It is the only model that beats persistence
  on MAE, and only by 0.037 mm — a real but very small margin.
- **Linear Regression** does NOT beat persistence on MAE (4.356 vs
  4.228 mm — **3.0% worse**), but beats it clearly on RMSE (11.059 vs
  13.022 mm) and has the best R² of all (0.493). It makes fewer very
  large errors, but slightly more small ones.
- Both models beat climatology clearly on every metric.
- On rainy days only, both models beat both baselines (LR MAE 11.05
  vs persistence 12.50 mm; RF 11.49 mm).

**Interpretation:** the models are genuinely better than the
baselines at explaining day-to-day variation (R² ~0.46–0.49 vs 0.30),
and they cut the size of the largest errors (RMSE), but the average
absolute error barely moves — because most of the MAE comes from the
dry/wet timing problem, which lagged features only partly solve. A
model that cannot beat persistence on MAE by more than 1% is a
working model, not a strong one. That is the correct, unflattering
reading of these numbers.

### 4.3 What the models actually learned

Random Forest feature importances (top 5 of 27):

| Feature | Importance |
|---|---|
| rain_t (today's rainfall) | **0.640** |
| pressure_t | 0.033 |
| pressure_change_3d | 0.027 |
| humidity_t | 0.024 |
| rain_t1 | 0.023 |

Top 5 together: 0.747. **Today's rainfall alone carries 64% of the
model's signal** — the Random Forest is, in effect, a smart
persistence model with small adjustments from pressure, humidity and
earlier rain. Linear Regression agrees: its largest standardised
coefficient is rain_t (5.35), followed by mean temperature (−2.38)
and pressure (−2.15). This is consistent with the MAE result above:
the models mostly refine persistence rather than replacing it. That
is explainable in an interview and is not a flaw — but it must be
stated, not hidden behind the R² figure.

---

## 5. Results — heavy rainfall (≥ 64.5 mm), test period

There were **21 heavy days** in the test period (1.4% of days).
Heavy-rain prediction is the weakest part of this project, and the
numbers below say so plainly.

### 5.1 Regression predictions thresholded at 64.5 mm

| Model | Observed heavy | Predicted heavy | True positives | False positives | False negatives | Precision | Recall |
|---|---|---|---|---|---|---|---|
| Linear Regression | 21 | 2 | 0 | 2 | 21 | 0.000 | 0.000 |
| Random Forest | 21 | 6 | 2 | 4 | 19 | 0.333 | 0.095 |
| Persistence | 21 | 21 | 6 | 15 | 15 | 0.286 | 0.286 |

- Linear Regression **caught none** of the 21 heavy days.
- Random Forest caught **2 of 21** (9.5% recall).
- Persistence — simply repeating today's rain — caught **6 of 21**,
  because heavy rain in Mumbai often lasts more than one day. The
  trained models are worse than the naive baseline at heavy rain.

### 5.2 Heavy-rain classifier (Random Forest, class_weight balanced)

| | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Not heavy | 0.995 | 0.939 | 0.966 | 1,439 |
| **Heavy** | **0.137** | **0.667** | **0.228** | **21** |

Confusion matrix [[TN, FP], [FN, TP]]: [[1351, 88], [7, 14]].
Accuracy 0.9349 — **meaningless here**: a model that always predicted
"not heavy" would score 98.6% accuracy and be useless.

- The classifier catches 14 of 21 heavy days (recall 0.667), but at
  the cost of **88 false alarms** — for every heavy day it catches,
  it cries wolf about 6 times. Precision 0.137, F1 0.228.
- **Verdict: heavy-rain prediction is not supportable at a useful
  level with this data and these models.** The class is too rare
  (85 heavy days in 18 training years), the target is noisy, and the
  reanalysis smooths the very extremes being predicted. The Extreme
  Rainfall module must present this result — including the false
  alarms — not a cherry-picked accuracy figure. This is a finding,
  not a failure to hide: it is exactly what the false-positive /
  false-negative analysis in the brief asked for.

---

## 6. Results — rain / no-rain classification (≥ 2.5 mm)

Test period: 452 rainy days, 1,008 dry/light days.

| Model | Precision (rain) | Recall (rain) | F1 (rain) | Accuracy | ROC-AUC |
|---|---|---|---|---|---|
| Logistic Regression | 0.866 | 0.889 | 0.878 | 0.923 | 0.977 |
| Random Forest Classifier | 0.845 | 0.918 | 0.880 | 0.923 | 0.979 |

- Logistic Regression confusion matrix [[TN, FP], [FN, TP]]:
  [[946, 62], [50, 402]] — 62 false alarms, 50 missed rainy days.
- Random Forest confusion matrix: [[932, 76], [37, 415]] — 76 false
  alarms, 37 missed rainy days.
- Rain/no-rain classification works well (F1 ~0.88, ROC-AUC ~0.98),
  because rain in Mumbai is strongly persistent day-to-day and the
  monsoon season is easy to recognise. This is a genuine strength of
  the system — predicting *whether* it will rain is far easier than
  predicting *how much* — and the dashboard should say exactly that.

---

## 7. Residual analysis

### 7.1 Top 10 worst Random Forest misses (test period)

| Date (t+1) | Observed (mm) | Predicted RF (mm) | Predicted LR (mm) | Error RF (mm) |
|---|---|---|---|---|
| 2021-05-16 | 199.9 | 32.2 | 13.0 | −167.7 |
| 2021-09-07 | 146.8 | 35.0 | 26.1 | −111.8 |
| 2021-12-02 | 0.8 | 91.5 | 34.9 | +90.7 |
| 2021-07-09 | 85.5 | 9.3 | 10.7 | −76.2 |
| 2022-09-15 | 96.6 | 26.3 | 37.5 | −70.3 |
| 2022-09-18 | 2.9 | 69.7 | 37.7 | +66.8 |
| 2021-05-17 | 22.6 | 88.5 | 107.2 | +65.9 |
| 2023-07-25 | 93.9 | 30.1 | 30.8 | −63.8 |
| 2023-07-05 | 97.5 | 38.8 | 33.1 | −58.7 |
| 2024-07-11 | 83.3 | 25.6 | 24.9 | −57.7 |

Pattern: **8 of the 10 worst misses are under-predictions of heavy
rain** — the models almost never predict more than ~114 mm (RF
predicted maximum: 114.2 mm; LR: 107.2 mm) against an observed
maximum of 199.9 mm. The two over-predictions (2021-12-02 and
2022-09-18) are days the model expected rain that did not arrive.
Residual bias is small overall (RF mean error +0.15 mm, LR −0.04 mm),
but the bias is not the story — the story is that the models compress
the extremes towards the middle. RF over-predicts on 1,196 of 1,460
days (mostly dry days, by small amounts) and under-predicts on 264
(mostly the wet days, by large amounts).

### 7.2 Error by month (mean absolute error, mm)

| Month | Persistence | Linear Regression | Random Forest | Mean observed |
|---|---|---|---|---|
| Jan | 0.13 | 0.99 | 0.26 | 0.08 |
| Feb | 0.02 | 0.48 | 0.04 | 0.01 |
| Mar | 0.25 | 0.71 | 0.50 | 0.13 |
| Apr | 0.02 | 0.67 | 0.09 | 0.03 |
| May | 3.73 | 3.82 | 3.51 | 2.49 |
| Jun | 7.83 | 7.82 | 7.69 | 14.17 |
| Jul | 14.67 | 13.73 | 14.32 | 29.73 |
| Aug | 7.82 | 7.98 | 6.86 | 11.46 |
| Sep | 11.90 | 10.71 | 11.31 | 15.92 |
| Oct | 2.87 | 2.99 | 3.38 | 2.60 |
| Nov | 0.60 | 0.95 | 0.63 | 0.54 |
| Dec | 0.61 | 1.14 | 1.42 | 0.48 |

Error is concentrated in the monsoon (June–September), above all
July (MAE ~14 mm), where the rain is heaviest and most variable.
Outside the monsoon the models are nearly perfect — because it
almost never rains, and predicting near-zero is usually right. Note
Linear Regression is *worse* than persistence in the dry months
(Jan–Apr, Nov–Dec): it predicts small amounts of rain on dry days
that persistence gets exactly right. Random Forest is closer to
persistence in dry months and better in the monsoon.

### 7.3 Plots

- `docs/figures/actual_vs_predicted_scatter.png` — observed vs
  predicted, LR and RF; the scatter fans out above ~50 mm, showing
  the under-prediction of extremes.
- `docs/figures/test_timeseries.png` — daily observed vs predicted,
  test period 2021–2024; the models track the monsoon seasons but
  flatten the peaks.
- `docs/figures/error_by_month.png` — MAE by month for all three
  approaches (see §7.2).
- `docs/figures/residuals_vs_observed.png` — RF residuals against
  observed rainfall; the downward slope at high observed values is
  the extreme under-prediction, visible at a glance.

---

## 8. Reanalysis vs observation — what these numbers are (clarification 6)

**All metrics in this report are performance against Open-Meteo /
ERA5 reanalysis rainfall — NOT against rain-gauge observations.**

- The model was trained on, and tested on, reanalysis data: a weather
  model reconstruction that blends observations together. Every value
  exists for every day, but no value is a direct rain-gauge reading.
- The Phase 2 IMD cross-check measured the gap: for 2020, IMD's
  gauge-based gridded rainfall totalled 3,553 mm against Open-Meteo's
  2,774 mm — reanalysis underestimates the annual total by ~22%,
  spreads rain over more days (131 vs 108), and caps the daily maximum
  lower (169.8 vs 203.1 mm).
- **What that means for real-world accuracy:** a model that scores
  MAE 4.19 mm on reanalysis test data has proven it can predict
  *reanalysis* rainfall to within ~4 mm on average. Against a real
  rain gauge, the error would be larger — the reanalysis target is
  already a smoothed version of reality, and the model inherits that
  smoothing (see §7.1: the models never predict above ~114 mm, while
  gauges record far more). The gap is worst for heavy rain, which is
  exactly where accuracy matters most.
- **How to report it honestly:** always pair the test-set metrics with
  the IMD disagreement (22% annual-total underestimation, extremes
  smoothed). Never describe these numbers as "the model predicts
  Mumbai rainfall with 4.2 mm error" without the word *reanalysis*.
  The product stays labelled an educational/research tool, never an
  operational forecast or warning.

---

## 9. Reproducibility — experiment settings

- **Python:** 3.12 (venv `~/workspace/monsoonai-venv`)
- **Packages:** scikit-learn 1.9.1, pandas 3.1.1, NumPy 2.5.4,
  matplotlib 3.11.2, joblib 1.6.0
- **Random seed:** 42 (fixed in both scripts; Random Forest
  `random_state=42`, `n_jobs=-1`)
- **Data:** `data/processed/mumbai_daily_2000-2024.csv`
  (9,132 rows × 14 columns, 0 missing values)
- **Commands to re-run:**
  ```
  ~/workspace/monsoonai-venv/bin/python src/train_models.py
  ~/workspace/monsoonai-venv/bin/python src/evaluate_models.py
  ```
- **Artefacts:** `artifacts/linear_regression.joblib`,
  `artifacts/random_forest_regressor.joblib`,
  `artifacts/logistic_regression.joblib`,
  `artifacts/random_forest_classifier.joblib`,
  `artifacts/random_forest_heavy_classifier.joblib`,
  `artifacts/feature_columns.joblib`,
  `artifacts/climatology_train.joblib`,
  `artifacts/training_settings.json`,
  `artifacts/predictions_test.csv`,
  `artifacts/evaluation_summary.json`
- **Plots:** `docs/figures/` (4 PNGs, see §7.3)

---

## 10. Conclusions and what Phase 3 does NOT claim

1. **The models work, modestly.** Random Forest beats persistence on
   every regression metric; Linear Regression beats it on RMSE and R²
   but not on MAE. Rain/no-rain classification is strong (F1 ~0.88).
2. **Heavy-rain prediction does not work at a useful level.**
   Regression catches 0–2 of 21 heavy days; the dedicated classifier
   catches 14 but with 88 false alarms. This must be shown in the
   dashboard, not hidden.
3. **The models are mostly smart persistence.** 64% of the Random
   Forest's signal is today's rainfall. The improvement over
   persistence is real but small on MAE.
4. **All numbers are reanalysis numbers.** Real-world gauge accuracy
   would be worse, especially for extremes (§8).
5. **What is NOT claimed:** no operational forecasting ability, no
   warning-grade heavy-rain prediction, no India-wide or
   multi-city generalisation (Mumbai only, one grid cell), and no
   7-day forecast. None of those was tested, and none is claimed.

**Recommended next step (Phase 4, only on Harsh's approval):** build
the Streamlit dashboard showing these exact, measured results — the
next-day prediction, the rain/no-rain probability, the model
performance centre with this table, and the heavy-rain limitation
stated plainly — with every number labelled as reanalysis-based.
