# MONSOONAI — Baseline results (Phase 2, baselines only)

Date: 9 November 2026. Script: `src/baseline_experiment.py`
(readable, commented, fixed seed 42). No model beyond the two
baselines below was trained.

## Setup

- Data: `data/processed/mumbai_daily_2000-2024.csv` — Open-Meteo /
  ERA5 **reanalysis** daily series for Mumbai, 2000–2024.
- Target: next-day rainfall = `precipitation_sum` on day t+1, in mm.
- Cutoff: end of day t, 23:59 Asia/Kolkata. Features may use days
  t−6…t only (see `docs/prediction-definition.md` and
  `docs/leakage-audit.md` — no FAILs).
- Chronological split (never shuffled):
  train 2000–2017 (6,575 rows), validation 2018–2020 (1,096 rows),
  test 2021–2024 (1,460 rows).
- Rainy day = ≥ 2.5 mm (IMD-verified threshold, see
  `docs/crosscheck-and-threshold.md` §4).

## Results — test period 2021–2024 (1,460 days)

Test-set facts: 452 rainy days (31.0%), mean observed rainfall
6.51 mm/day, maximum 199.9 mm.

| Baseline | MAE (mm) | RMSE (mm) | R² | MAE rainy days only (mm) | RMSE rainy days only (mm) |
|---|---|---|---|---|---|
| **Persistence** (tomorrow = today) | **4.228** | **13.022** | **0.2968** | 12.501 | 23.017 |
| **Day-of-year climatology** (train-period means) | 5.447 | 13.419 | 0.2533 | 14.946 | 23.430 |

## Reading the numbers (honest interpretation)

- Persistence beats climatology on every metric — tomorrow's rain
  looks more like today's rain than like the average for that date.
  That is the bar any later model must clear.
- Both baselines are weak in absolute terms: on rainy days the
  average error is 12–15 mm, and RMSE ~23 mm. Daily rainfall is a
  hard, noisy target, and these numbers say so plainly.
- R² of ~0.30 (persistence) means most of the day-to-day variation
  is *not* explained by yesterday's rain alone. A later model that
  cannot beat MAE 4.23 mm / RMSE 13.02 mm on this test set is not a
  working model, however advanced it sounds.
- These are **reanalysis** numbers: the target itself is ERA5
  precipitation, which the IMD cross-check shows underestimates
  gauge-based annual rainfall by ~22%. Real-world error against
  gauges would be larger. See `docs/data-quality-note.md` §3.
