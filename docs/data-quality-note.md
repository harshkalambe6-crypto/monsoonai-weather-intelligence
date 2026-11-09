# MONSOONAI — Data-quality note (Phase 2, measured values)

Date: 9 November 2026. All numbers below were measured from files
actually on disk. Nothing here is estimated or invented.

## 1. The Mumbai series (primary data — HISTORICAL REANALYSIS)

- Source: Open-Meteo Historical Weather API (Archive API), underlying
  data ERA5 reanalysis. Licence CC BY 4.0, attribution
  "Weather data by Open-Meteo.com" required.
- Requested point: 19.0760° N, 72.8777° E (Mumbai).
- File: `data/raw/mumbai_openmeteo_daily_2000-2024.csv` (+ hourly file
  for daily means) → processed: `data/processed/mumbai_daily_2000-2024.csv`
- Rows: **9,132** (one per day, 2000-01-01 to 2024-12-31; 25 years,
  7 leap days — count checks out: 25 × 365 + 7 = 9,132).
- Columns (14): time, temperature_2m_max, temperature_2m_min,
  precipitation_sum, rain_sum, precipitation_hours,
  wind_speed_10m_max, wind_direction_10m_dominant, wind_gusts_10m_max,
  shortwave_radiation_sum, temperature_2m_mean,
  relative_humidity_2m_mean, pressure_msl_mean, surface_pressure_mean.

### Missing values — measured

| Column | Missing | % |
|---|---|---|
| every column | 0 | 0.0% |

**Zero missing values in all 14 columns.** This is expected, not a
surprise: the Open-Meteo docs state reanalysis data are "gap-free and
consistent" — gaps are filled by the reanalysis model by construction.
A null here would have meant an API fault, not a data gap. The check
was still run and logged (see `src/prepare_mumbai_daily.py` output).

### Rainfall summary (measured, 2000–2024)

- Rainy days ≥ 2.5 mm (IMD-verified threshold): **2,771 of 9,132 (30.3%)**
- Rainy days ≥ 1 mm: 3,191 (34.9%) — for reference only
- Dry days (exactly 0.00 mm): 5,468 (59.9%)

### Daily rainfall classification — corrected (9 November 2026)

A review found the original note listed rainy days (≥2.5 mm) and dry days
(0.00 mm) without naming the days in between, leaving 893 days
unaccounted for (2,771 + 5,468 = 8,239 of 9,132). Recalculated directly
from `data/processed/mumbai_daily_2000-2024.csv`, the three categories
are exhaustive and sum to 9,132:

| Category | Definition | Days | Share |
|---|---|---|---|
| Dry | precipitation_sum = 0.00 mm | 5,468 | 59.9% |
| Light rain | 0 < precipitation_sum < 2.5 mm | **893** | 9.8% |
| Rainy (IMD) | precipitation_sum ≥ 2.5 mm | 2,771 | 30.3% |
| **Total** | | **9,132** | 100.0% |

The 893 light-rain days split as 473 days with 0 < rain < 1 mm and
420 days with 1 ≤ rain < 2.5 mm (smallest positive value 0.1 mm,
largest 2.4 mm). Together they contribute only 885.9 mm of rain —
1.7% of the 25-year total — so they are numerous but hydrologically
small. Classification logic: a day is "dry" only at exactly 0.00 mm;
"rainy" only at or above the IMD-verified 2.5 mm threshold; everything
in between is "light rain". No counts were adjusted — the original
2,771 and 5,468 figures were correct; the middle category was simply
never named. Use this three-way classification in all later work
(Phase 3 onwards) and in the dashboard.
- Mean daily rainfall: 5.70 mm/day; mean annual total: **2,080.0 mm**
- Wettest year: 2020 (2,773.6 mm); driest year: 2015 (1,324.2 mm)
- Maximum single-day rainfall: **251.1 mm on 2016-09-22**
- Days ≥ 64.5 mm (IMD "heavy"): 121; ≥ 115.6 mm ("very heavy"): 21;
  > 204.4 mm ("extremely heavy"): 2
- Monsoon (Jun–Sep) share of total rainfall: **94.2%**
- Temperature range: max 41.3 °C, min 12.9 °C
- Daily-mean relative humidity range: 27.4–94.6%

### Monthly mean rainfall (mm/day, measured)

| Month | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mean mm/day | 0.02 | 0.02 | 0.05 | 0.00 | 0.94 | 14.87 | 22.57 | 15.42 | 11.18 | 2.33 | 0.29 | 0.25 |

The monsoon signal is sharp and real: June–September dominate, and
April averages 0.00 mm/day. This is the signal the model has to learn.

## 2. Cross-check — IMD gridded rainfall (OBSERVATIONAL data)

- Source: IMD 0.25° daily gridded rainfall (Pai et al. 2014), built by
  interpolating rain-gauge observations onto a grid. **Observational
  data — not reanalysis.**
- File: `data/raw/ind2020_rfp25.grd` (25,495,560 bytes — exact expected
  size for 135 × 129 grid × 366 days × 4 bytes; SHA-256 verified,
  see `docs/crosscheck-and-threshold.md`).
- Only ONE year (2020) was downloaded. Multi-year retrieval is a
  Phase 3 task, not claimed here.

### Alignment — spatial and temporal (clarification 2)

**Spatial.** The Open-Meteo API returned the ERA5 grid cell centred at
**19.086115° N, 72.85291° E** (a few km from the requested point).
Mumbai falls between IMD grid points (nearest longitudes 72.75° E /
73.00° E, latitudes 19.00° N / 19.25° N), so the IMD value used is the
simple mean of the four surrounding grid points — a documented, simple
choice. The four points disagree with each other by up to ~300 mm/year
(2020 totals 3,411–3,730 mm), so no single grid point should be called
"Mumbai rainfall" without saying which cell it is. Residual mismatch:
both sources are ~25 km grid cells, not a point gauge; neither resolves
neighbourhood-level rain.

**Temporal.** Open-Meteo daily values are calendar-day aggregates in
**Asia/Kolkata** (00:00–24:00 IST). IMD daily values are labelled by
the gauge-reading date: each value is the 24 h accumulation ending
**03:00 UTC (08:30 IST)** on the labelled date (VERIFIED — see
`docs/crosscheck-and-threshold.md` §3). So an IMD value labelled D
covers mostly the previous calendar day. The comparison below is
therefore reported both same-date and shifted by one day, and the
shifted version agrees better — consistent with the convention.

### IMD vs Open-Meteo comparison, 2020 (366 overlapping days)

| Comparison | Pearson r | Mean bias (OM − IMD) | MAE |
|---|---|---|---|
| Same date | 0.704 | −2.13 mm/day | 6.71 mm/day |
| IMD shifted +1 day (IMD D vs OM D−1) | **0.741** | −2.14 mm/day | **5.89 mm/day** |

- Annual totals 2020: IMD 4-point mean **3,553.0 mm** vs Open-Meteo
  **2,773.6 mm** — the reanalysis total is **~779 mm (~22%) lower**.
- Rainy days ≥ 2.5 mm in 2020: IMD 108, Open-Meteo 131, both 103,
  IMD-only 5, Open-Meteo-only 28.
- Maximum daily: IMD 203.1 mm, Open-Meteo 169.8 mm.

**Interpretation (plain language):** the two sources agree on *when*
it rains (correlation ~0.74, 103 of 108 IMD rainy days also rainy in
Open-Meteo) but disagree on *how much*: Open-Meteo spreads rain over
more days at lower intensity and underestimates the annual total by
about a fifth. That is the known reanalysis smoothing behaviour, now
measured for this location instead of assumed. The model will learn
from the reanalysis series, so its rainfall amounts should be read as
"reanalysis-scale" rainfall — systematically lower than IMD's
gauge-based totals. This must be stated on the dashboard and in the
README, not hidden.

**Open check:** the IMD grid-point totals have not yet been compared
against an IMD *station* climatology for Mumbai, and only one year
(2020) was compared. Both are Phase 3 tasks.

## 3. Reanalysis vs observation — what the model learns (clarification 6)

**The model learns from reanalysis data, not from observations.**

- The training series (Open-Meteo / ERA5) is a *reconstruction*: a
  weather model that has absorbed station, satellite, aircraft and
  buoy observations and filled in the gaps mathematically. Every value
  exists for every day and every place — which is why there are zero
  missing values — but no value is a direct reading from a rain gauge
  in Mumbai.
- The IMD gridded data are closer to observations (interpolated gauge
  readings), and the 2020 comparison shows they disagree with the
  reanalysis by ~22% on the annual total. Neither source is a
  neighbourhood rain gauge.
- **What this means for real-world generalisation:**
  1. The model learns the patterns *in the reanalysis*, including its
     smoothing bias. A model that scores well on reanalysis test data
     has proven it can predict reanalysis rainfall — not that it can
     predict what a gauge in Andheri or Colaba would record tomorrow.
  2. Real-world skill is likely *lower* than test-set skill, especially
     for extremes: the reanalysis already smooths extremes, so the
     model sees a tamer version of reality than the real world produces.
  3. The honest way to report performance is: metrics on the reanalysis
     test set, *plus* the IMD cross-check disagreement, side by side.
     The dashboard and README must say the model is trained on
     reanalysis data and validated against IMD gridded observations,
     and must label the product an educational/research tool — never
     an operational forecast or warning.

## 4. What is NOT yet known (UNVERIFIED / open)

- Missing-data % for IMD grid cells at Mumbai (only one year
  extracted; the 2020 extraction had no −999.0 values at the four
  Mumbai points — the −999.0 values in the file are off-land cells).
- Whether the IMD 4-point mean is the best Mumbai estimate (nearest
  point vs bilinear interpolation — undecided).
- IMD station climatology comparison for Mumbai (not done).
- Multi-year IMD retrieval (only 2020 downloaded).
