# MONSOONAI — Leakage Audit

**Project:** MONSOONAI — Mumbai next-day rainfall
**Phase:** 2 — Data pipeline
**Date:** 9 November 2026
**Source:** Phase 1 research report (`phase1-research.md`, §6.2 feature list); dataset `data/processed/mumbai_daily_2000-2024.csv`; baseline experiment `src/baseline_experiment.py`.
**Rule being audited:** to predict rainfall on day **t+1**, a feature may use data dated **t or earlier only**. Any feature that needs data from t+1 (or later) is leakage and is FAIL.

**Prediction setup (from `prediction-definition.md`):** cutoff is end of day t, 23:59 Asia/Kolkata; input window is days t−6 through t; target is `precipitation_sum` on day t+1, in mm.

**Correction noted while auditing:** Phase 1 §2.4/§3.1 listed daily `relative_humidity_2m`, `pressure_msl`, `surface_pressure`, and `temperature_2m_mean` as if the Open-Meteo Archive API returned them as daily variables. It does not — the API has no such daily variables. In this project those four columns (`temperature_2m_mean`, `relative_humidity_2m_mean`, `pressure_msl_mean`, `surface_pressure_mean`) were computed in `src/prepare_mumbai_daily.py` as the mean of the 24 hourly values for each Asia/Kolkata calendar day. That computation uses only hours within the same calendar day, so it does not introduce leakage — but the columns are derived, not raw API daily output, and must be labelled that way in the data dictionary.

---

## Audit table

"Uses" means the latest date the feature needs. PASS = uses data dated t or earlier only. FAIL = would need data from t+1 or later.

### Lagged rainfall

| Feature | Uses | Verdict | Why |
|---|---|---|---|
| Rainfall at t (`precipitation_sum` on day t) | t | **PASS** | Day t is fully over at the 23:59 cutoff, so today's rainfall is known. |
| Rainfall at t−1 | t−1 | **PASS** | Yesterday's rainfall is in the past. |
| Rainfall at t−2 | t−2 | **PASS** | Two days ago; in the past. |
| Rainfall at t−3 | t−3 | **PASS** | Three days ago; in the past. |
| Rainfall at t−7 | t−7 | **PASS** | Seven days ago; in the past. (Note: t−7 is one day outside the t−6…t input window in `prediction-definition.md` — it is still leakage-free because it is *earlier* than t, but the window definition should be widened to t−7…t, or this lag dropped, before Phase 3. See "Fixes needed".) |

### Rolling rainfall

| Feature | Uses | Verdict | Why |
|---|---|---|---|
| 3-day rolling sum of rainfall, up to t (days t−2…t) | t | **PASS** | The window ends at t; it adds up only days that are already over. |
| 3-day rolling mean of rainfall, up to t (days t−2…t) | t | **PASS** | Same window as above; only past days are averaged. |
| 7-day rolling sum of rainfall, up to t (days t−6…t) | t | **PASS** | The window ends at t; it never reaches into t+1. |
| 7-day rolling mean of rainfall, up to t (days t−6…t) | t | **PASS** | Same window as above; only past days are averaged. |
| Days since last rain | t and earlier | **PASS** | Defined as: count back from day t (inclusive) to the most recent day with rain. If it rained on day t, the value is 0. It looks backwards only, never forwards. |
| Rainy-day count in last 7 days (days t−6…t) | t | **PASS** | Counts rainy days in a window that ends at t. Uses the IMD-verified rainy-day threshold of ≥ 2.5 mm (see `docs/crosscheck-and-threshold.md` §4). |

### Temperature

| Feature | Uses | Verdict | Why |
|---|---|---|---|
| Maximum temperature at t (`temperature_2m_max`) | t | **PASS** | Day t's maximum is known once day t is over. |
| Minimum temperature at t (`temperature_2m_min`) | t | **PASS** | Day t's minimum is known once day t is over. |
| Mean temperature at t (`temperature_2m_mean`) | t | **PASS** | Daily mean computed from day t's own 24 hourly values only (see correction note above); no hours from t+1 are involved. |
| 3-day mean temperature (days t−2…t) | t | **PASS** | Averages the daily means of three days that are all over by the cutoff. |

### Humidity

| Feature | Uses | Verdict | Why |
|---|---|---|---|
| Relative humidity at t (`relative_humidity_2m_mean`) | t | **PASS** | Daily mean computed from day t's own 24 hourly values only; no hours from t+1 are involved. |
| 3-day mean humidity (days t−2…t) | t | **PASS** | Averages the daily means of three days that are all over by the cutoff. |

### Pressure

| Feature | Uses | Verdict | Why |
|---|---|---|---|
| Mean sea-level pressure at t (`pressure_msl_mean`) | t | **PASS** | Daily mean computed from day t's own 24 hourly values only; no hours from t+1 are involved. |
| Pressure change over last 3 days: pressure at t minus pressure at t−3 | t | **PASS** | Both days in the subtraction (t and t−3) are dated t or earlier. |

### Wind

| Feature | Uses | Verdict | Why |
|---|---|---|---|
| Maximum wind speed at t (`wind_speed_10m_max`) | t | **PASS** | Day t's maximum is known once day t is over. |
| Dominant wind direction at t, encoded as sin/cos (`wind_direction_10m_dominant`) | t | **PASS** | Day t's direction is known once day t is over. Sin/cos encoding only changes how the number is represented; it adds no new information and no future data. |

### Seasonal (calendar) features

| Feature | Uses | Verdict | Why |
|---|---|---|---|
| Day of year, encoded as sin/cos | Calendar date t | **PASS** | The date itself is known at prediction time; it uses no weather data at all, past or future. |
| Month | Calendar date t | **PASS** | Same as above — the calendar month of day t is known. |
| Monsoon-season flag (June–September) | Calendar date t | **PASS** | Decided purely from day t's calendar month; uses no weather data. |

### Climatology

| Feature | Uses | Verdict | Why |
|---|---|---|---|
| Day-of-year mean rainfall (climatology) | Training period only | **PASS — CONDITIONAL** | This feature is safe **only if** the mean for each day of year is computed from the **training data only (1 Jan 2000 – 31 Dec 2017)**. That is exactly what `src/baseline_experiment.py` does (`train.groupby(day_of_year).mean()`). If the means were computed from the full dataset, or from validation/test years, the feature would silently contain information about the very days being predicted — that would be leakage, FAIL. Rule for Phase 3: compute climatology inside the training split and never recompute it using later data. |

---

## Rules the audit confirms

1. **Rolling windows must end at t, not include t+1.** A "3-day mean" that ran t−1…t+1 would be leakage. Every rolling feature above is defined with its window ending at t.
2. **Days since last rain is defined using days up to and including t.** Count back from t; 0 means it rained on day t itself. Never count forward to the next rainy day.
3. **Climatology is computed from training data only** (2000–2017). Never from the full series, never from validation or test years.
4. **Daily means are same-day means.** `temperature_2m_mean`, `relative_humidity_2m_mean`, `pressure_msl_mean`, and `surface_pressure_mean` each average only the 24 hourly values of their own calendar day — no hours leak across the midnight boundary.

---

## Verdict

**FAILs: none.** Every feature proposed in Phase 1 §6.2 uses data dated t or earlier only, as defined above — **no feature is rejected outright for leakage.**

**Cleared for Phase 3 (as defined in this audit):** all lagged-rainfall features; all rolling rainfall sums/means; days since last rain; rainy-day count in last 7 days; temperature (max/min/mean at t, 3-day mean); humidity (at t, 3-day mean); pressure (at t, 3-day change); wind max and sin/cos direction at t; day-of-year sin/cos, month, and monsoon-season flag; and the day-of-year climatology mean.

**NOT cleared as written — fixes needed before Phase 3:**

1. **Rainfall at t−7 vs the input window (fix the definition, not the feature).** The t−7 lag reaches one day before the t−6…t input window stated in `prediction-definition.md`. It is leakage-free (it is in the past), but the window definition and the feature list disagree. Fix: either widen the stated input window to t−7…t, or drop the t−7 lag. Do this before Phase 3 starts.
2. **Climatology — conditional clearance only.** The day-of-year climatology feature is cleared **only** under the training-data-only rule above. Any Phase 3 code that computes climatology from the full dataset, or recomputes it after seeing validation/test data, turns this PASS into a FAIL. The rule must be enforced in code review, not just in this document.
3. **Days since last rain — needs a cap (small fix).** The definition works when it rained recently, but a long dry spell could make the count run back past the start of the dataset (or grow without bound). Before Phase 3, fix a rule — for example, cap the value at 30 days, or at the number of days since the start of the series — and write the chosen cap into the feature code.

---

## Phase 3 re-audit (9 November 2026)

The final feature list in `src/features.py` (27 features) was re-audited
against the same rule before training. Verdict: **no FAILs.**

The three fixes from Phase 2 were applied as follows:

1. **Input window widened to t−7…t.** The t−7 rainfall lag was KEPT
   (it is leakage-free past data and adds a weekly-lag signal) and the
   stated window in `docs/prediction-definition.md` §4 was widened to
   match it. The window definition and the feature list now agree.
2. **Climatology from training data only.** The day-of-year mean
   rainfall feature is computed in `src/train_models.py` from the
   training period (2000–2017) only, saved as
   `artifacts/climatology_train.joblib`, and mapped into the feature
   table by day-of-year. `src/features.py` receives it as an argument
   and never computes it from the full series. The evaluation script
   loads the same saved series — no recomputation from later data.
3. **Days since last rain capped at 30.** Implemented in
   `src/features.py` (`DAYS_SINCE_RAIN_CAP = 30`); a dry spell longer
   than 30 days is recorded as 30, so the feature cannot run back past
   the start of the dataset or grow without bound.

Additional checks on the final feature list:

- All rolling windows (3-day and 7-day sums/means) end at t.
- `rainy_days_last7` counts rainy days (≥ 2.5 mm, IMD-verified) in
  the window t−6…t only.
- `pressure_change_3d` is pressure at t minus pressure at t−3.
- Wind direction is encoded as sin/cos of day t's direction.
- Seasonal features (day-of-year sin/cos, month, monsoon flag) use
  the calendar date of day t only.
- Regression predictions are clipped at zero in
  `src/evaluate_models.py` (rainfall cannot be negative). This is a
  post-processing step applied identically to both models; it changes
  no training data and introduces no future information.
- No target, prediction, or test-period value is used as an input
  feature anywhere in `src/features.py`, `src/train_models.py`, or
  `src/evaluate_models.py`.

**Phase 3 verdict: all 27 features PASS. No leakage found.**
