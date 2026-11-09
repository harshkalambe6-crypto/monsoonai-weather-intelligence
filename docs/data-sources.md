# MONSOONAI — Data sources (Phase 2, actual acquisitions)

**Data categories used in this project — never mix them:**
- **Historical reanalysis** — past weather reconstructed by a weather model
  from many observations (ERA5, served by Open-Meteo). This is what the
  Mumbai series below is.
- **Observational datasets** — direct measurements or interpolations of
  gauge/station measurements (IMD gridded rainfall, CHIRPS).
- **Model predictions** — outputs of MONSOONAI's own models (baselines so
  far; no advanced model yet).
- **External forecasts** — predictions from other forecasting systems
  (e.g. Open-Meteo Forecast API). **Not used anywhere in this project yet.**

## 1. Primary source — Open-Meteo Historical Weather API (Archive API)

- Docs: https://open-meteo.com/en/docs/historical-weather-api
- Terms: https://open-meteo.com/en/terms
- Licence: **CC BY 4.0** — attribution required wherever the data appears:
  "Weather data by Open-Meteo.com" with a link to https://open-meteo.com/
- Underlying data: ERA5 reanalysis (0.25°, 1940–present), updated daily
  with ~5 days delay. **Reanalysis, not station observations.**
- Cost: free, no API key, no registration (non-commercial use).
  Limits: < 10,000 calls/day, 5,000/hour, 600/minute.

### Request 1 — daily values (HTTP 200)

Exact URL (also saved in `docs/openmeteo-request-url.txt`):

```
https://archive-api.open-meteo.com/v1/archive?latitude=19.0760&longitude=72.8777&start_date=2000-01-01&end_date=2024-12-31&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,precipitation_hours,wind_speed_10m_max,wind_direction_10m_dominant,wind_gusts_10m_max,shortwave_radiation_sum&timezone=Asia%2FKolkata&format=csv
```

Saved as: `data/raw/mumbai_openmeteo_daily_2000-2024.csv` (9,132 data rows).

**Correction to the Phase 1 plan:** the first request also asked for daily
`temperature_2m_mean`, `relative_humidity_2m`, `pressure_msl` and
`surface_pressure`. The API returned **HTTP 400**:
"Cannot initialize ForecastVariableDaily from invalid String value
relative_humidity_2m". Those four are **hourly-only variables** — the
Archive API's daily parameter list does not include them (verified on the
docs page, 9 Nov 2026). They were therefore obtained from the hourly
request below and averaged, not from a daily variable.

### Request 2 — hourly values, for daily means (HTTP 200)

```
https://archive-api.open-meteo.com/v1/archive?latitude=19.0760&longitude=72.8777&start_date=2000-01-01&end_date=2024-12-31&hourly=temperature_2m,relative_humidity_2m,pressure_msl,surface_pressure&timezone=Asia%2FKolkata&format=csv
```

Saved as: `data/raw/mumbai_openmeteo_hourly_2000-2024.csv`
(219,168 data rows = 9,132 days × 24 hours).

### Actual returned columns (observed in the files, not assumed)

Daily file header row (after 3 metadata lines):
`time, temperature_2m_max (°C), temperature_2m_min (°C),
precipitation_sum (mm), rain_sum (mm), precipitation_hours (h),
wind_speed_10m_max (km/h), wind_direction_10m_dominant (°),
wind_gusts_10m_max (km/h), shortwave_radiation_sum (MJ/m²)`

Hourly file header row:
`time, temperature_2m (°C), relative_humidity_2m (%),
pressure_msl (hPa), surface_pressure (hPa)`

**Grid cell actually returned:** the CSV metadata row reports
latitude **19.086115**, longitude **72.85291**, elevation 6.0 m —
the centre of the ERA5 grid cell the API selected, a few km from the
requested point (19.0760, 72.8777). See `docs/data-quality-note.md`
for the alignment discussion.

### Processed dataset

`src/prepare_mumbai_daily.py` merges the two files into
`data/processed/mumbai_daily_2000-2024.csv` (9,132 rows, 14 columns).
Daily means of temperature, relative humidity, mean sea-level pressure
and surface pressure are the simple mean of the 24 hourly values for
each Asia/Kolkata calendar day. This derivation is documented in the
script's header comment.

## 2. Cross-check source — IMD gridded rainfall / CHIRPS

See `docs/crosscheck-and-threshold.md` for the full outcome. Summary:
**IMD download WORKED** — one year (2020) obtained via the page's POST
form (`rain=2020` to `rainfall.php`), file
`data/raw/ind2020_rfp25.grd`, 25,495,560 bytes (exact expected size),
SHA-256 verified. CHIRPS was therefore **not used** (recorded as the
unused fallback). IMD daily convention VERIFIED: each value labelled D
is the 24 h accumulation ending 03:00 UTC (08:30 IST) on D. Rainy-day
threshold VERIFIED: ≥ 2.5 mm (IMD Met Glossary). The 2020 IMD vs
Open-Meteo comparison (4-point Mumbai mean vs reanalysis) is in
`docs/data-quality-note.md` §2: Pearson r = 0.741 (1-day shifted),
Open-Meteo annual total ~22% lower than IMD.
