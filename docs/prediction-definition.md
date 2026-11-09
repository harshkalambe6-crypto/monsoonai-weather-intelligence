# MONSOONAI — Prediction Definition

**Project:** MONSOONAI — AI weather forecasting & extreme rainfall intelligence (Mumbai, first location)
**Phase:** 2 — Data pipeline
**Date:** 9 November 2026
**Source:** Phase 1 research report (`phase1-research.md`, §6.1–§6.3 and §13 addendum, item 3); dataset `data/processed/mumbai_daily_2000-2024.csv`; baseline experiment `src/baseline_experiment.py`.
**Status:** This is the binding definition for Phase 3 model work. If a feature, target, or split disagrees with this document, this document wins — fix the code, not the definition.

---

## 1. The prediction, in one sentence

At the end of a day **t**, using only weather data from day **t** and earlier, predict how much rain will fall in Mumbai on the next day, **t+1**.

---

## 2. Prediction cutoff — the project definition

**Cutoff: end of day t, 23:59 Asia/Kolkata.**

This is the project definition, stated explicitly: a prediction for day t+1 is made at 23:59 on day t, Asia/Kolkata time. Anything that happened on day t (the full calendar day, 00:00–23:59 Asia/Kolkata) is known at prediction time. Anything dated t+1 or later is **not** known and must never be used as an input.

In plain terms: at the end of today, we look back at today and the days before it, and we guess tomorrow's rainfall. We never peek at tomorrow.

## 3. Timezone

**Asia/Kolkata (IST, UTC+5:30), for everything.**

- Every date in the dataset is an Asia/Kolkata calendar day.
- The daily means in the dataset (`temperature_2m_mean`, `relative_humidity_2m_mean`, `pressure_msl_mean`, `surface_pressure_mean`) were computed as the mean of the 24 hourly values of each Asia/Kolkata calendar day.
- The target date, the input window, and the day-of-year used for climatology are all Asia/Kolkata dates.

## 4. Input window

**Features may use days t−7 through t only — the past 8 days, including today.**

- The most recent day a feature may touch is **t**.
- The oldest day a feature may touch is **t−7**.
- No feature may use data from day t+1 or later. (The full leakage check is in `leakage-audit.md`.)

*Changed in Phase 3 (9 November 2026): the window was widened from t−6…t to t−7…t so the t−7 rainfall lag identified in the Phase 2 leakage audit sits inside the stated window. The t−7 lag is leakage-free (it is in the past); widening the definition was chosen over dropping the lag, because the weekly lag carries real signal. See `docs/leakage-audit.md`, "Phase 3 re-audit".*

## 5. Target (what we predict)

| Item | Definition |
|---|---|
| Target variable | `precipitation_sum` — daily total precipitation, in millimetres (mm) |
| Target date | **t+1** (the calendar day after the cutoff day t) |
| Target column (code) | `target_next_day_rain_mm`, built as `precipitation_sum.shift(-1)` in `src/baseline_experiment.py` |
| Units | mm of rain on day t+1 |

Example: if today is t = 15 July 2024, the target is the `precipitation_sum` recorded for 16 July 2024.

Notes:
- The last row of the dataset (31 December 2024) has no t+1, so it has no target and is dropped from training/evaluation.
- The regression target is the rainfall **amount** in mm. The rain/no-rain classification (Phase 1 §6.1) uses the same target with a threshold applied to it. The rainy-day threshold is **VERIFIED**: ≥ 2.5 mm (inclusive), per the IMD Met Glossary — "Rainy Day — Rainfall amount realised in a day is 2.5 mm or more" — corroborated by an IMD publication on mausam.imd.gov.in. Full citation in `docs/crosscheck-and-threshold.md` §4. The earlier ≥ 1 mm project choice is superseded.

## 6. Location — what "Mumbai" means here

- Requested point: 19.0760° N, 72.8777° E.
- The Open-Meteo Archive API actually returned the grid cell centred at **19.086115° N, 72.85291° E** (see `src/prepare_mumbai_daily.py`). That is the cell this project calls "Mumbai".
- Honest statement: "Mumbai rainfall" in this project means the value for the ~25 km grid cell containing Mumbai — a reanalysis grid cell, not a rain gauge in a specific neighbourhood.

## 7. Chronological split

Split by time, **never randomly**. The test set is strictly later than the training set.

| Split | Dates (inclusive) | Purpose |
|---|---|---|
| **Train** | 1 January 2000 – 31 December 2017 | Fit models; compute climatology means (see §8) |
| **Validation** | 1 January 2018 – 31 December 2020 | Tune models; choose between models |
| **Test** | 1 January 2021 – 31 December 2024 | Final evaluation, once only; never tune on it |

This matches `src/baseline_experiment.py` (train < 2018-01-01; validation 2018-01-01 to < 2021-01-01; test ≥ 2021-01-01) and mirrors the IndiaWeatherBench design (train 2000–2017 / validation 2018 / test 2019) cited in Phase 1 §6.3.

## 8. The four data categories — never mix them
Harsh's binding clarification (Phase 1 §13 addendum, item 1): these four categories must be clearly distinguished everywhere — in the data dictionary, in every chart, on every dashboard page, and in the README.

| # | Category | One-line definition | Where it appears in this project |
|---|---|---|---|
| 1 | **Historical reanalysis** | Past weather reconstructed by running a weather model that blends old observations together — model output about the past, not a direct measurement. | The Open-Meteo Archive API data (ERA5-based) that fills `mumbai_daily_2000-2024.csv` — **all** input features and the target come from this. This is what the model actually learns from. |
| 2 | **Observational datasets** | Direct measurements from instruments (rain gauges, weather stations), or grids built by interpolating those measurements. | IMD 0.25° gridded rainfall (interpolated rain-gauge observations) — the planned cross-check / ground-truth source for validating the reanalysis rainfall. Not yet downloaded in Phase 2. |
| 3 | **Model predictions** | Numbers produced by *this project's own* trained model (e.g. MONSOONAI's predicted rainfall for t+1). | The output of the Phase 3 models and the baselines (persistence, climatology). Predictions are never fed back in as input features. |
| 4 | **External forecasts** | Predictions made by other people's forecasting systems (e.g. a national weather service or a commercial forecast API) for a future date. | **Not used anywhere in this project yet.** The Open-Meteo Forecast API is a separate endpoint and is not part of the Phase 2 data. Any future "forecast" page must label external forecasts as such and never present them as MONSOONAI's own predictions. |

**The rule in one line:** reanalysis is the training data, observations are the cross-check, our model's outputs are predictions, and nobody else's forecasts are in the project at all — and every chart, table, and page must say which one it is showing.

## 9. What this definition does NOT allow

- No 7-day model forecast: only t+1 is predicted. A "coming days" view may show, at most, a clearly labelled **climatology outlook** (historical average), which is not a model forecast (Phase 1 §6.4).
- No feature may use t+1 data (see `leakage-audit.md`).
- No tuning on the test set, ever.
- No presenting reanalysis values as live observations, and no presenting the latest available date as "today" — the reanalysis lags by about 5 days.
