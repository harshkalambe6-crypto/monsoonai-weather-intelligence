# MONSOONAI — Phase 1 Research Report

**Project:** MONSOONAI — AI-Powered Weather Forecasting & Extreme Rainfall Intelligence Platform
**Author of project:** Harsh Ganesh Kalambe, B.Sc. Data Science (2nd year), KES Shroff College, Mumbai
**Phase:** 1 — Research and Planning ONLY
**Date:** 9 November 2026
**Status:** Research only. No code written, no data downloaded, no dataset integrated, no model trained, no dashboard built. Nothing in this report claims a download or a result that does not exist yet.

**Honesty rule used throughout:** every fact is either cited to a source URL below or marked **UNVERIFIED**. No column names, metrics, download links, or percentages are invented. Where a number could not be established, the report says so plainly instead of guessing.

---

## 1. Executive summary

**Top recommendation (short version):**

- **Dataset:** **Open-Meteo Historical Weather API (Archive API)** as the primary Phase 2 source, for one Mumbai point location, with **IMD gridded rainfall (0.25°)** as the cross-check / ground-truth source for validation.
- **Scope:** **Maharashtra-focused, starting with ONE location — Mumbai (19.0760° N, 72.8777° E)** — as a single daily time series. Expand to a small set of Maharashtra locations only after the Mumbai model is validated.
- **First model:** **next-day (t+1) rainfall regression + rain/no-rain classification**, with a **persistence baseline** and a **day-of-year climatology baseline**, compared against **Linear Regression and Random Forest**. XGBoost only if it measurably beats Random Forest on the same split. **LSTM is NOT justified yet** (see §7).
- **India-wide modelling is NOT recommended** for this project (see §8 for the evidence and comparison table).

Why this combination: Open-Meteo is the only source that is free, keyless, documented, and directly returns a clean daily CSV/JSON time series for one latitude/longitude with temperature, humidity, pressure, wind and precipitation in a single call — which is what a beginner can actually build on in Phase 2. IMD gridded rainfall is the authoritative Indian ground reference, but it arrives as yearly binary `.grd` files that need a custom reader, which is a real Phase 2 work item, not a five-minute download. ERA5 direct (CDS) is powerful but has the highest access friction (account + licence acceptance + queued jobs + NetCDF handling). IndiaWeatherBench is a research-grade gridded benchmark built for deep-learning spatial forecasting, not for a first single-location tabular model, and its download size could not be verified.

---

## 2. Data sources investigated

### 2.1 India Meteorological Department (IMD) — gridded rainfall and temperature

**What it is:** IMD's Climate Monitoring and Prediction Group publishes long-period daily gridded datasets over India, built from rain-gauge / station observations interpolated onto a grid.

**Rainfall (primary):**
- Source page: https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html
- Resolution: **0.25° × 0.25°** (~27 km), grid 135 × 129 points, longitude 66.5° E–100.0° E, latitude 6.5° N–38.5° N.
- Time range: **1901–2024** (124 years, per the IMD page; the underlying paper covers 1901–2010, the product has been extended).
- Temporal resolution: **daily**; one file per year, 365/366 records per file.
- Unit: **millimetres (mm)**. Missing/undefined value: **−999.0**.
- Format: **binary `.grd`** (unformatted Fortran direct-access, 4-byte floats, one record per day, 135 × 129 values per record). **Not CSV, not NetCDF.** A reader must be written (IMD publishes sample Fortran and C reader code on the same page).
- Citation required: Pai et al. (2014), *Development of a new high spatial resolution (0.25° × 0.25°) long period (1901–2010) daily gridded rainfall data set over India*, MAUSAM, 65(1), pp. 1–18.
- Disclaimer on the page: IMD "cannot guarantee that the data are correct in all circumstances" and accepts no liability for errors.

**Temperature (secondary):**
- Source page: https://www.imdpune.gov.in/cmpg/Griddata/Max_1_Bin.html (maximum temperature; minimum/mean pages are linked from the same group)
- Resolution: **1.0° × 1.0°**, 31 × 31 grid points, latitude 7.5° N–37.5° N, longitude 67.5° E–97.5° E.
- Time range: **1951–2024**. Daily. Unit: **°C**. Undefined value: **99.9**.
- Known quality note on the IMD page: **gridded data for 2008 onwards are based on a relatively smaller number of stations (~180)** received operationally in real time, versus ~395 stations for the earlier period (per a citing paper). This is a documented inhomogeneity to note in Phase 2.
- Citation required: Srivastava et al. (2009), *Development of High Resolution Daily Gridded Temperature Data Set (1969–2005) for the Indian Region*, Atmospheric Science Letters, DOI: 10.1002/asl.232.

**Access method:** download from the IMD Pune pages above. There is **no public API** documented on these pages. **Exact per-year file download URLs are UNVERIFIED** — the IMD page exposes "Click here" links whose targets were not confirmed in this research, and no direct download URL is reproduced here. The R package `imdR` (CRAN, https://github.com/Subhradip25/imdR) documents that it downloads these `.grd` files from IMD Pune programmatically, which corroborates that the files are downloadable, but the exact URL pattern must be confirmed in Phase 2 before any download step is written.

**Licence / usage conditions:** **UNVERIFIED as a formal licence.** No open licence (e.g. CC-BY) is stated on the IMD gridded-data pages. What is stated is a citation requirement and a disclaimer. Treat IMD data as **government data requiring attribution/citation, with no confirmed open-licence text** — Phase 2 must check IMD's data policy / terms on https://mausam.imd.gov.in/ before redistributing any derived file, and must not redistribute raw IMD files in the GitHub repo.

**Known gaps / quality issues (documented):**
- Gridded values are **interpolations from stations**, not point observations: a 0.25° cell (~27 km) smooths localised extremes. This matters most on the Konkan coast / Western Ghats, where rainfall varies sharply over tens of kilometres.
- Station network density changed over time (see temperature note above); early-1900s coverage is sparser than recent decades.
- Undefined value −999.0 (rainfall) / 99.9 (temperature) must be handled as missing, not as a measurement.
- The product is updated with a lag; the page lists data to 2024, so "current" data is not available from this source.

**Downloadable now?** Plausibly yes via the IMD Pune pages (and via `imdR`), but **not verified by an actual download in Phase 1** — nothing has been downloaded. Phase 2's first task is to confirm the download links and test one year file.

### 2.2 IndiaWeatherBench

- Paper: https://arxiv.org/abs/2509.00653 — Nguyen, Singh, Naharas, Bandarkar, Grover, *IndiaWeatherBench: A Dataset and Benchmark for Data-Driven Regional Weather Forecasting over India* (arXiv:2509.00653, submitted 31 Aug 2025).
- Code: https://github.com/tung-nd/IndiaWeatherBench
- Dataset (Hugging Face): https://huggingface.co/datasets/tungnd/IndiaWeatherBench

**What it is:** a curated, ML-ready subset of the **IMDAA** regional reanalysis (Indian Monsoon Data Assimilation and Analysis, produced by NCMRWF with the UK Met Office and IMD). The raw IMDAA data are hourly, 1979–2020, 0.12° (~12 km), 57+ variables across 63 pressure levels — but the raw archive is several terabytes and, per the paper, downloading it from https://rds.ncmrwf.gov.in/ is "non-trivial, requiring manual access procedures and resulting in slow transfer speeds".

**IndiaWeatherBench contents (from the Hugging Face page, verified 9 Nov 2026):**
- Time range: **2000–2019 (20 years)**, 6-hourly (00, 06, 12, 18 UTC).
- Region: 6° N–36.72° N, 66.6° E–97.25° E, ~256 × 256 grid.
- Variables: **43 channels** — single-level: TMP (2 m temperature), UGRD/VGRD (10 m wind), APCP (precipitation), PRMSL (mean sea-level pressure), TCDCRO (cloud cover); pressure-level: TMP, HGT, UGRD, VGRD, RH at 50, 250, 500, 600, 700, 850, 925 hPa; static: MTERH (terrain height), LAND (land cover).
- Splits (standardised): train 2000–2017 (~26,500 samples), validation 2018 (~1,500), test 2019 (~1,500).
- Formats: **Zarr** (chunked, xarray/dask-compatible) and **HDF5** (one `.h5` file per time step, pre-split into train/val/test).
- Baselines in the paper: U-Nets, Transformers, graph neural networks.

**Licence:** **CC BY-NC-SA 4.0** (Creative Commons Attribution–NonCommercial–ShareAlike 4.0). Free for non-commercial, educational and research use. Commercial use requires contacting `director@ncmrwf.gov.in`; publications using the data should be sent a copy to the same address.

**Download size: UNVERIFIED.** The Hugging Face page does not state a total size in the text retrieved, and no download was attempted. Expect it to be large (tens to hundreds of GB for the full 20-year, 43-channel, 256 × 256, 6-hourly archive is plausible, but that is an estimate, not a fact — do not quote it as a measured size). Phase 2 must check the Hugging Face file listing before committing to this source.

**Suitability for MONSOONAI:** **not recommended as the primary Phase 2 source.** It is built for spatial deep-learning forecasting (predicting full grids 6 hours ahead), which is a different and much harder problem than the single-location daily rainfall prediction proposed here. It is a strong *reference* and a possible Phase 6+ extension (e.g. validating a model against IMDAA precipitation for Maharashtra), but using it as the first dataset would force a beginner to handle Zarr/HDF5 gridded tensors, GPU-scale training, and 6-hourly horizons before any working model exists.

### 2.3 ERA5 reanalysis (Copernicus Climate Data Store)

- CDS home: https://cds.climate.copernicus.eu/
- Dataset (hourly single levels): `reanalysis-era5-single-levels` (CDS catalogue name — verified in CDS documentation; the exact catalogue URL was not reproduced here because CDS links are session-dependent).
- Documentation: https://confluence.ecmwf.int/pages/viewpage.action?pageId=600770874 (how to download ERA5) and the ERA5 single-levels Product User Guide (ECMWF Confluence).

**What it is:** ECMWF's fifth-generation global atmospheric reanalysis — model + observations assimilated into a consistent historical record. **Hourly, 1940–present, 0.25° × 0.25° grid, ~5 days behind real time.**

**Variables relevant to rainfall prediction (single-levels dataset, verified from the ECMWF Product User Guide):**
| CDS / ERA5 variable name | Unit | Notes |
|---|---|---|
| `total_precipitation` | m (accumulated) | Convert to mm/day by summing hourly values × 1000 |
| `2m_temperature` | K | Convert to °C |
| `2m_dewpoint_temperature` | K | Humidity proxy; relative humidity is derived, not a direct ERA5 single-level variable |
| `mean_sea_level_pressure` | Pa | |
| `surface_pressure` | Pa | |
| `10m_u_component_of_wind`, `10m_v_component_of_wind` | m s⁻¹ | |
| `100m_u_component_of_wind`, `100m_v_component_of_wind` | m s⁻¹ | |
| `total_cloud_cover` | 0–1 | |
| `boundary_layer_height` | m | |

Note: **ERA5 has no direct "relative humidity" single-level variable** — it must be computed from temperature and dewpoint. Any Phase 2 feature list must say this explicitly rather than listing humidity as a raw column.

**Access method:** free **registration required** (ECMWF account), licence acceptance via the CDS web interface (licence acceptance can only be done through the web form, per ECMWF docs), then download via the web form or the **CDS API** (`cdsapi` Python package + API key). Requests enter a processing queue; large requests can take hours. Format: **NetCDF or GRIB**. There is also a newer CDS "ERA5 hourly time-series" catalogue entry designed for fast single-point long time series (noted as experimental in ECMWF docs).

**Licence:** Copernicus licence — free for research, commercial and operational use **with attribution** (cite the CDS dataset DOI, e.g. 10.24381/cds.adbb2d47 for ERA5 single levels — the DOI is given on the CDS dataset page; confirm it in Phase 2).

**Download size for India-only daily data (estimate, NOT measured):** restricting to ~6 single-level variables, daily aggregates, an India bounding box (~30 × 25 grid cells at 0.25°), 25 years (2000–2024) is on the order of **tens to a few hundred MB as NetCDF** (rough arithmetic: ~9,125 days × ~750 cells × 6 variables ≈ 41 million values). This is an **estimate only** — the actual size depends on compression, the exact variable set and the CDS request. Hourly data for the same box/period would be roughly 24× larger and is **not** recommended for the first build.

**Known issues:** reanalysis precipitation is **model-derived, not observed** — it is known in the literature to smooth and typically underestimate intense, localised daily rainfall relative to gauges (this is a methodological caveat to test in Phase 2 by comparing ERA5/Open-Meteo precipitation against IMD gridded rainfall for the same Mumbai cell; it is **not** a measured result of this report). ~5-day lag means no "today" data. CDS queue times and the licence-acceptance step are the main practical frictions.

**Suitability:** **second-priority source.** Best used in Phase 2 as the *feature* source (temperature, pressure, wind, humidity) behind the Open-Meteo API — which is itself ERA5-based — rather than downloaded directly. Direct CDS download becomes worthwhile only if Phase 2 needs variables Open-Meteo does not expose, or a longer record than Open-Meteo's archive.

### 2.4 Open-Meteo Historical Weather API (Archive API) — RECOMMENDED PRIMARY SOURCE

- Docs: https://open-meteo.com/en/docs/historical-weather-api
- Terms: https://open-meteo.com/en/terms
- Endpoint: `https://archive-api.open-meteo.com/v1/archive`

**What it is:** a free weather API that serves historical reanalysis data (ERA5 0.25° from 1940, ERA5-Land 0.1° from 1950, ECMWF IFS 9 km from 2017) through a simple HTTP GET that returns JSON/CSV for one latitude/longitude and a date range. No account, no API key for non-commercial use.

**Verified facts (from the official docs page, 9 Nov 2026):**
- Time range: **1940–present** (ERA5); ERA5-Land from 1950; IFS from 2017. Update frequency: daily, **~5 days delay** for ERA5/ERA5-Land (so the most recent ~5 days are not yet in the archive).
- Data are described as **"gap-free and consistent"** — reanalysis fills gaps by construction. There is therefore no missing-value percentage to measure in the returned series (any missing values would be an API failure, not a data gap); Phase 2 must still log and check for nulls.
- Daily aggregations are simple 24-hour aggregations of hourly values; `timezone` is required when daily variables are requested.
- Recommended for long-term consistency: use ERA5 (or ERA5-Land) only, not IFS, when studying decades, because IFS model versions change over time (per the docs page).

**Variables (daily, verified from the docs page):** the daily parameter set includes `temperature_2m_max`, `temperature_2m_min`, `temperature_2m_mean`, `precipitation_sum`, `rain_sum`, `precipitation_hours`, `relative_humidity_2m` (daily aggregates exist — the docs' daily table lists the available aggregations; the exact daily variable names must be confirmed from the live docs/API response in Phase 2 and written into the data dictionary), `pressure_msl`, `surface_pressure`, `wind_speed_10m_max`, `wind_direction_10m_dominant`, `wind_gusts_10m_max`, `shortwave_radiation_sum`, plus `weather_code`. Hourly variables include `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `precipitation`, `rain`, `pressure_msl`, `surface_pressure`, `cloud_cover`, `wind_speed_10m`, `wind_direction_10m`, `wind_gusts_10m`. Units: temperature °C, precipitation mm, pressure hPa, wind km/h (convertible to m/s), humidity %.

**Example request shape (endpoint + parameters as documented; not executed in Phase 1):**
`https://archive-api.open-meteo.com/v1/archive?latitude=19.0760&longitude=72.8777&start_date=2000-01-01&end_date=2024-12-31&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m,pressure_msl,wind_speed_10m_max&timezone=Asia%2FKolkata&format=csv`

**Free tier / rate limits (from https://open-meteo.com/en/terms, verified):** fewer than **10,000 API calls per day, 5,000 per hour, 600 per minute**; **non-commercial use only**. Note: Open-Meteo weights long requests — a request for more than 14 days and/or more than 10 variables counts as more than one call (per Open-Meteo's own documentation/blog). A single 25-year daily pull for one location is therefore a handful of weighted calls, far inside the limit; the whole Maharashtra set (5–10 locations) is still trivially inside it.

**Licence:** API data under **CC BY 4.0**; attribution required — display **"Weather data by Open-Meteo.com"** with a link to https://open-meteo.com/ wherever the data appears (app footer + README + About page). Server code is AGPLv3, which does not affect API consumers.

**Suitability:** **highly suitable as the primary Phase 2 source.** It gives, in one documented call, exactly the daily multi-variable time series the proposed model needs (rainfall + temperature + humidity + pressure + wind), in CSV/JSON, with no key, no registration, and no binary-format reader. Its limitation is also its nature: it is **reanalysis, not station observations** — so Phase 2 must cross-check its precipitation against IMD gridded rainfall for the same Mumbai grid cell and report the agreement (correlation, bias) honestly, rather than presenting Open-Meteo values as "observed Mumbai rainfall".

**What it is NOT:** it is not a forecast API (the Forecast API is a separate endpoint, `https://api.open-meteo.com/v1/forecast`, 16-day horizon). The Archive API gives history only. Any "7-day forecast" page in the app must therefore be labelled as **model-generated predictions from historical patterns**, not as an official or NWP forecast — or omitted until a genuine forecast source is integrated.

### 2.5 Other legitimate public datasets (one line each)

| Dataset | Suitability for MONSOONAI |
|---|---|
| **CHIRPS v2.0** (Climate Hazards Group, UCSB) — https://www.chc.ucsb.edu/data/chirps ; download: https://data.chc.ucsb.edu/products/CHIRPS-2.0/ | Daily precipitation only, 1981–present, 0.05° (~5 km), quasi-global 50° S–50° N, satellite + station blend, NetCDF/TIFF, free for research/non-commercial use. **Good second cross-check for rainfall** (finer than IMD/ERA5), but precipitation-only, so it cannot supply temperature/humidity features. |
| **NASA POWER** (Prediction of Worldwide Energy Resources) — https://power.larc.nasa.gov/ ; API docs: https://power.larc.nasa.gov/docs/services/api/ | Free, **no API key**, daily point data from 1981, parameters include `T2M` (2 m temperature), `RH2M` (relative humidity), `PRECTOTCORR` (corrected precipitation, mm/day), wind. **Good backup/alternative feature source** if Open-Meteo is unavailable; coarser (~0.5°, model-based MERRA-2/GEOS) and precipitation is a model estimate. |
| **GHCN-Daily** (NOAA Global Historical Climatology Network) — https://www.ncei.noaa.gov/access/monitoring/daily-report (access via NOAA NCEI) | Station observations (real gauges), global, daily. **Useful as a station-level ground truth** for Mumbai if a nearby station with a long record exists, but station availability/coverage for Mumbai specifically is **UNVERIFIED** — check in Phase 2; do not assume a Mumbai station is present. |
| **IMD station data / Mausam portal** — https://mausam.imd.gov.in/ | Official station observations, but access terms and bulk-download availability for a student project are **UNVERIFIED**; the gridded products (§2.1) are the documented route. Do not plan on station data until access is confirmed. |
| **IMDAA raw archive** — https://rds.ncmrwf.gov.in/ | The source behind IndiaWeatherBench; hourly, 1979–2020, 0.12°, 57+ variables. **Not recommended** — terabyte-scale, manual access procedures, slow transfer (per the IndiaWeatherBench paper). Use IndiaWeatherBench instead if gridded reanalysis is ever needed. |

---

## 3. Sample data schemas (verified column/variable names only)

### 3.1 Open-Meteo Archive API — daily CSV (expected columns)

These are the **documented daily variable names** from https://open-meteo.com/en/docs/historical-weather-api. The exact column names in a returned CSV are the variable names requested, plus `time`. **No file has been downloaded, so the returned schema has not been observed** — Phase 2 must save one real response and record the actual header row in the data dictionary.

| Column (as requested) | Unit | Meaning |
|---|---|---|
| `time` | yyyy-mm-dd | Date (Asia/Kolkata timezone) |
| `temperature_2m_max` / `temperature_2m_min` / `temperature_2m_mean` | °C | Daily max / min / mean 2 m temperature |
| `precipitation_sum` | mm | Daily total precipitation |
| `rain_sum` | mm | Daily liquid precipitation only |
| `relative_humidity_2m` (daily aggregation — exact name to confirm from live response) | % | Daily relative humidity |
| `pressure_msl` | hPa | Daily mean sea-level pressure |
| `surface_pressure` | hPa | Daily surface pressure |
| `wind_speed_10m_max` | km/h | Daily max 10 m wind speed |
| `wind_direction_10m_dominant` | ° | Dominant daily wind direction |
| `wind_gusts_10m_max` | km/h | Daily max wind gusts |

### 3.2 IMD gridded rainfall — `.grd` binary (no columns)

There are **no column names** — the file is a flat binary array: one record per day, each record 135 × 129 float32 values in grid order (longitude fastest, latitude 6.5° N → 38.5° N, longitude 66.5° E → 100.0° E), value = rainfall in mm, −999.0 = undefined. After extraction, the Phase 2 CSV schema should be: `date, lat, lon, rainfall_mm` (plus `tmax_c, tmin_c` from the 1° temperature grids, noting the resolution mismatch). This schema is a **proposal**, not an observed file.

### 3.3 ERA5 single levels (CDS NetCDF)

Variables are the CDS names in §2.3 (`total_precipitation` in metres, `2m_temperature` in kelvin, `mean_sea_level_pressure` in pascals, `10m_u_component_of_wind` / `10m_v_component_of_wind` in m s⁻¹). Dimensions: `valid_time` (hourly), `latitude`, `longitude`. After daily aggregation the Phase 2 CSV schema should mirror §3.1 with a `source` column recording `ERA5`. **UNVERIFIED:** the exact NetCDF dimension/variable naming in a downloaded file (to be recorded in Phase 2).

### 3.4 IndiaWeatherBench (HDF5/Zarr)

43 channels named per §2.2 (e.g. `APCP` precipitation, `TMP` 2 m temperature, `PRMSL` mean sea-level pressure). One HDF5 file per 6-hour time step. **UNVERIFIED:** the exact per-file key names and units — to be recorded only after a file is actually opened in Phase 2 (not planned for the primary build).

---

## 4. Maharashtra-focused vs India-wide — the location question

**The question Harsh asked:** does the available data support reliable location-specific predictions, or is location-specific modelling not defensible? Decide from the data, not from interest.

### 4.1 What the data actually supports

**A single-location daily time series is the best-supported design in the data:**

1. **Every source above resolves Mumbai as a point/grid cell.** Mumbai (19.0760° N, 72.8777° E) falls inside the IMD 0.25° rainfall grid (nearest grid points ≈ 19.00° N / 72.75° E and 19.25° N / 73.00° E — the city spans roughly 18.92° N–19.23° N, so a single cell is already an approximation of a ~30 km-wide city), inside ERA5/Open-Meteo's 0.25° grid, and inside CHIRPS's 0.05° grid. A daily series of ~9,100 rows (2000–2024) for one location is a clean, well-understood tabular ML problem.
2. **Mumbai is a good first location for a scientific reason, not just a personal one:** it has one of the strongest, most studied monsoon rainfall signals in India — a sharp June–September season, high inter-annual variability, and documented extreme events (notably the 26 July 2005 deluge). That gives the model a real signal to learn, real extremes to evaluate against, and a real story for the Extreme Rainfall module. It is also Harsh's home city, which makes the interview explanation genuine — but the data reasons above are what make it defensible.
3. **Maharashtra as a small multi-location set is supported, with a condition:** the same sources resolve Pune (~18.52° N, 73.86° E), Nashik, Nagpur, Kolhapur and other Maharashtra cities as separate points/cells. A Maharashtra set of 5–8 locations is feasible **as separate per-location models** (or one model with location as a feature, only after per-location baselines exist). What is *not* supported is treating Maharashtra as one homogeneous region — rainfall regimes differ sharply across the state (Konkan coast vs. Western Ghats vs. rain-shadow Marathwada vs. Vidarbha), so a single pooled model would average away the signal.

**An India-wide model is NOT defensible for this project:**

1. **Spatial heterogeneity:** India contains multiple monsoon regimes (south-west monsoon, north-east monsoon, western disturbances, orographic rainfall in the Himalayas and Western Ghats, arid Rajasthan). A single tabular model trained on all-India daily data would need spatial features, interaction terms, and far more data to avoid learning a meaningless national average. The gridded deep-learning approach (IndiaWeatherBench) exists precisely because India-wide forecasting is a spatial problem — and it needs GPU-scale models.
2. **Compute:** an India-wide daily gridded dataset at 0.25° is 135 × 129 ≈ 17,400 cells × ~9,100 days ≈ 158 million values *per variable* — before features. That does not fit the free deployment budget (§6) and is not a beginner tabular problem.
3. **Evaluation honesty:** an India-wide model can report a deceptively good national R² while being useless in any specific place. Location-specific evaluation (per-city MAE, per-city extreme-event recall) is the honest standard, and it requires location-specific modelling anyway.
4. **Map claims:** an India-wide map page would imply model coverage everywhere. With a Maharashtra set, the map can honestly show exactly the locations the model covers and grey out the rest — which is the correct product behaviour.

### 4.2 Maharashtra locations — proposed set (for after Mumbai v1)

| Location | Approx. coordinates | Why it adds value (regime contrast) |
|---|---|---|
| **Mumbai** (v1) | 19.0760° N, 72.8777° E | Konkan coast, extreme monsoon rain, Harsh's city |
| Pune | 18.52° N, 73.86° E | Leeward of the Western Ghats — much drier than Mumbai, tests generalisation |
| Nashik | 19.99° N, 73.79° E | North Maharashtra, Godavari basin |
| Kolhapur | 16.70° N, 74.23° E | Southern Maharashtra, heavy Ghats rainfall |
| Nagpur | 21.15° N, 79.09° E | Vidarbha — different regime, hotter, later monsoon |
| Chhatrapati Sambhajinagar (Aurangabad) | 19.88° N, 75.34° E | Marathwada rain-shadow — driest test case |

Coordinates above are approximate city centres (Mumbai's is verified; the others are standard published values and should be confirmed from the geocoding API in Phase 2 — do not hard-code them without checking). **Do not add these locations until the Mumbai model is validated.**

### 4.3 Comparison table — Maharashtra-focused vs India-wide

| Dimension | Maharashtra-focused (Mumbai first, then 5–8 cities) | India-wide |
|---|---|---|
| **Data availability** | All sources resolve every Maharashtra city as a point/cell; Open-Meteo returns each city in one call | Same sources cover India, but as 17,400 grid cells, not a usable table without spatial processing |
| **Spatial resolution** | 0.25° reanalysis / 0.05° CHIRPS per location; city is approximated by 1 cell — honest and stated | 0.25° nationally, but a single national model cannot represent sub-regional regimes |
| **Missing data** | Open-Meteo/ERA5: gap-free by construction; IMD: −999.0 undefined cells to handle; missing-% **not measurable until Phase 2** (see §5) | Same per-cell issues, multiplied across cells and compounded by regions with sparse stations (e.g. Himalayas, deserts) |
| **Model reliability** | One clean time series per city; per-city metrics are interpretable; extremes are real local events | National average metrics hide local failure; high risk of a model that looks good and predicts nothing useful anywhere |
| **Compute** | ~9k rows/city; trains in seconds–minutes on a laptop; Random Forest fits easily | Gridded spatial model needs GPU-scale training; not feasible on free tier |
| **Deployment** | Fits Streamlit 1 GB RAM easily (small CSV + pickled sklearn model, a few MB) | Full-grid model + data would exceed free-tier memory and the 1 GB GitHub file guidance |
| **Interview-explainability** | "I predicted next-day Mumbai rainfall from the last 7 days of rain, temperature, humidity and pressure" — explainable in one sentence | "I trained a national model" invites questions about spatial modelling the student cannot yet answer |
| **Expansion path** | Add one Maharashtra city at a time, same pipeline, same evaluation | Requires a different architecture (spatial deep learning) — effectively a second project |
| **Verdict** | **Recommended** | **Not recommended for this project** |

**Final recommendation:** **Maharashtra-focused, Mumbai first.** The data support reliable *location-specific* prediction **at the grid-cell / reanalysis scale** — with the honest caveat that "Mumbai rainfall" in this project means the value for the ~25 km grid cell containing Mumbai, not a rain gauge in a specific neighbourhood. That caveat must appear on the dashboard and in the README. Location-specific modelling **is** defensible on that basis; what is **not** defensible is claiming street-level, gauge-accurate, or operational-warning-grade predictions.

---

## 5. Historical data coverage and missing data

**No missing-data percentage is given in this report, because none was measured.** No dataset was downloaded in Phase 1, so no percentage could be honestly computed. What IS known, per source:

| Source | Coverage | What is known about gaps |
|---|---|---|
| IMD rainfall 0.25° | 1901–2024 daily | Undefined value −999.0 marks cells/days without data (ocean cells, and days/cells outside station coverage). Station density changed over time; early decades are sparser. Missing-% per Mumbai cell: **to be measured in Phase 2** by counting −999.0 values in the extracted series. |
| IMD temperature 1° | 1951–2024 daily | Undefined value 99.9. Documented inhomogeneity: 2008+ based on ~180 stations vs ~395 earlier. |
| Open-Meteo / ERA5 | 1940–present, daily | **Gap-free by construction** (reanalysis). The docs state this explicitly. Expected missing-% in a returned series: 0% (any nulls would be an API/processing fault, to be logged). ~5-day lag on the most recent data. |
| IndiaWeatherBench | 2000–2019, 6-hourly | Preprocessed benchmark; missing-data handling is part of its pipeline. Missing-%: **UNVERIFIED**. |
| CHIRPS | 1981–present, daily | Satellite + station blend; provisional data for ~20 days after month-end, later replaced with final values. Missing-%: **UNVERIFIED** for the Mumbai cell. |
| NASA POWER | 1981–present, daily | Model-based (MERRA-2/GEOS); fill value −999 in API responses. Missing-%: **UNVERIFIED**. |

**Phase 2 must produce, for the chosen Mumbai series, a one-page data-quality note:** row count, date range, count and % of missing/undefined values per variable, count of rainy days, and the IMD-vs-Open-Meteo precipitation comparison (correlation, mean bias). Until that note exists, no missing-% claim may appear in the README or dashboard.

**IMD rainfall thresholds (verified, for the Extreme Rainfall module):** per IMD's own press-release legends (e.g. IMD press releases, https://mausam.imd.gov.in/ and https://internal.imd.gov.in/press_release/20250222_pr_3731.pdf): **light < 15 mm; moderate 15.6–64.4 mm; heavy 64.5–115.5 mm; very heavy 115.6–204.4 mm; extremely heavy > 204.4 mm** (all per 24 hours). Use these exact bands for risk classification, labelled as IMD's classification, not the model's own invention. **Rainy-day definition (≥ 2.5 mm in 24 h) is UNVERIFIED in this research** — it is the commonly cited IMD convention, but Phase 2 must confirm it from an IMD source before using it as the classification threshold; until then, use ≥ 1 mm as a documented, explicit project choice, or confirm 2.5 mm first.

---

## 6. Proposed prediction problem, methodology, and horizon

### 6.1 The prediction problem (recommended)

**Primary task — next-day rainfall, two framings, one dataset:**
1. **Regression:** predict tomorrow's rainfall amount in mm (target = `precipitation_sum` at t+1).
2. **Classification:** predict rain vs no-rain tomorrow (target = 1 if tomorrow's rainfall ≥ threshold, else 0; threshold to be confirmed, §5).
3. **Extreme-rainfall classification (secondary, later):** predict whether tomorrow exceeds the IMD "heavy" band (≥ 64.5 mm). This is a **rare-event** problem — heavy-rain days are a small minority of days, and extremely heavy days rarer still. It must be evaluated with precision/recall/F1 and a confusion matrix, **never** with accuracy alone (a model that always predicts "no heavy rain" would score high accuracy and be useless). The exact frequency of each band in Mumbai must be measured in Phase 2 before any claim about feasibility is made.

**Why next-day, not 7-day:** see §6.4.

### 6.2 Features — only what is genuinely available at prediction time

All features are computed from data dated **t or earlier** when predicting t+1. No feature may use t+1 information (no leakage).

| Feature group | Features (proposed) |
|---|---|
| Lagged rainfall | rainfall at t, t−1, t−2, t−3, t−7 |
| Rolling rainfall | 3-day and 7-day rolling sum and mean of rainfall up to t; days since last rain; count of rainy days in last 7 days |
| Temperature | tmax, tmin, mean at t; 3-day mean temperature |
| Humidity | relative humidity at t; 3-day mean |
| Pressure | mean sea-level pressure at t; change in pressure over last 3 days (t minus t−3) |
| Wind | max wind speed at t; dominant direction encoded (sin/cos of direction, not raw degrees) |
| Seasonal | day of year (sin/cos encoded), month, monsoon-season flag (June–September) |
| Climatology | day-of-year mean rainfall (computed from the training period only, to avoid leakage) |

**Deliberately excluded for v1:** pressure-level variables, satellite imagery, NWP forecast fields (not available to a free student pipeline), and any feature from the target day. ERA5 pressure-level data (e.g. 850 hPa humidity) are a genuine Phase 4+ improvement, not a v1 feature.

### 6.3 Chronological split and evaluation

- **Split by time, never randomly:** e.g. train 2000–2017, validation 2018–2020, test 2021–2024 (exact years to be fixed in Phase 2 after inspecting the series; the principle is that the test set is strictly later than training). This mirrors IndiaWeatherBench's own train/val/test design (2000–2017 / 2018 / 2019).
- **Baselines (mandatory, reported alongside every model):** (a) **persistence** — tomorrow's rainfall = today's rainfall; (b) **climatology** — tomorrow's rainfall = the training-period mean for that day of year; (c) **seasonal naive** — tomorrow = same date last year. A model that cannot beat persistence + climatology is not a working model, however advanced it sounds.
- **Regression metrics:** MAE, RMSE, R² — with the explicit note that R² is weak for zero-inflated rainfall (most days are dry); MAE/RMSE on rainy days only should also be reported.
- **Classification metrics:** precision, recall, F1, confusion matrix, and ROC-AUC (with the caveat that ROC-AUC flatters imbalanced problems — report precision-recall alongside). For the extreme-rainfall task, report false-positive and false-negative counts explicitly.
- **Error analysis (mandatory):** actual vs predicted plots, error by month (expect monsoon months to dominate error), and a case review of the largest misses (e.g. the biggest observed extreme days and whether the model caught any of them).
- **No metric may be reported before it is computed.** The README and dashboard must show "not yet evaluated" until Phase 3 runs.

### 6.4 Is the prediction horizon scientifically defensible?

- **Next-day (t+1) from lagged features: defensible, with modest expectations.** Lagged rainfall, rolling sums, humidity and pressure carry real short-term persistence signal, especially in the monsoon season. Expect the model to beat climatology modestly, not dramatically — daily rainfall is a hard, noisy target, and honest reporting of a modest improvement is the correct outcome. This is the standard framing for a first rainfall-ML project.
- **Multi-day (t+2 to t+7) from lagged features only: NOT defensible as a forecast.** Skill from lagged surface variables decays within 1–2 days; a 7-day "forecast" built only on past rain/temperature would be mostly climatology with extra steps. A genuine 7-day horizon requires NWP forecast fields as inputs (which this project does not have for free at the required resolution). **Decision:** the app's Forecast page must show **next-day prediction only** (plus, at most, a clearly-labelled "climatology outlook" for the coming days, which is a historical average, not a model forecast). Any 7-day model-forecast claim must not appear.
- **Temperature/humidity "predictions":** same logic — next-day values from lags are defensible as a modelling exercise; multi-day is not. These are secondary targets, only after rainfall works.
- **"Current weather" / "latest observation":** the data sources lag by ~5 days (ERA5/Open-Meteo) and IMD gridded data lag further. The dashboard must label the latest available date honestly (e.g. "Latest data: 4 Nov 2026 (5-day reanalysis lag)") and must not present reanalysis as a live observation. Live "current weather" would need the Open-Meteo Forecast API (a different endpoint, 16-day horizon, model-based) — a possible Phase 4 addition, labelled as forecast-model output, not observation.

---

## 7. ML methodology — model comparison

| Model | Role in v1 | Justification |
|---|---|---|
| Persistence + climatology | **Baseline (mandatory)** | The bar every model must clear; trivially explainable |
| Linear Regression (with lag/rolling features) | First real model | Interpretable coefficients; the honest starting point; a beginner can explain it in an interview |
| Random Forest Regressor / Classifier | Main comparison model | Handles non-linearity and interactions; robust to the zero-inflated target; no scaling needed; trains in minutes on ~9k rows |
| XGBoost | Compare **only if** it measurably beats Random Forest on the same chronological test split | Strong tabular model, but adds a dependency and tuning surface; include it on evidence, not for the name |
| LSTM / time-series deep learning | **NOT justified for v1** | ~9k daily rows for one location is a small dataset for sequence deep learning; a Random Forest on lag features captures the same short-term signal with far less complexity, compute, and explanation burden. Revisit only if (a) the tabular models plateau, (b) the project expands to multi-location gridded data, and (c) GPU/time budget exists. Recommending it now would be decoration. |

**Tuning:** light hyperparameter search for Random Forest / XGBoost only (e.g. a small grid over depth and tree count, validated on the validation years, not the test years). No tuning on the test set, ever.

**Reproducibility:** fixed random seeds, a `requirements.txt` with pinned versions, and a single training script that regenerates the model artefact from the raw downloaded CSV — so the pipeline can be re-run from a fresh environment.

---

## 8. Technical architecture (practical, beginner-buildable, free)

- **Language / DS stack:** Python 3.12; Pandas, NumPy, scikit-learn, Matplotlib, Seaborn, Plotly (charts), `requests` (Open-Meteo), `xarray`/`netCDF4` only if ERA5 direct download is ever needed (avoid in v1).
- **Model artefact:** a pickled scikit-learn pipeline (a few MB at most for ~9k rows) + a small feature-definition module. No model server.
- **Data storage:** **SQLite** (single file, `data/monsoonai.db`) or simply versioned CSVs under `data/processed/` for v1; SQLite is preferred because the brief asks for it and it handles the multi-city expansion cleanly. **Do not commit raw downloaded data to GitHub** — store it locally / in `.gitignore`, and document the exact download commands so anyone can reproduce it. (Large files: GitHub's guidance is to keep individual files under 100 MB; a single-city daily CSV is kilobytes, so this is not a constraint — the constraint only bites for gridded data, which is another reason to stay location-based.)
- **App:** **Streamlit** (single `app.py` + `pages/` for the 7 required pages: Overview, Forecast, Weather Map, Historical Analysis, Extreme Rainfall, Model Performance, About & Methodology). Every navigation item must work; the map uses Plotly `scatter_mapbox` / `density_mapbox` with real coordinates for covered cities only, and greys out / omits uncovered regions — no fake values for uncovered locations.
- **Repo:** `monsoonai-weather-intelligence` (proposed name), structure as in the master brief (`app/`, `data/`, `notebooks/`, `src/data_processing/`, `src/features/`, `src/models/`, `src/evaluation/`, `artifacts/`, `assets/`, `tests/`, `config/`, `README.md`, `requirements.txt`, `.gitignore`, `LICENSE` — MIT is the usual choice for a student portfolio repo; confirm with Harsh).
- **No paid services anywhere:** no API keys, no paid hosting, no paid datasets.

---

## 9. Computational requirements and free deployment feasibility

**Training (local, Phase 3):**
- Mumbai daily series 2000–2024: ~9,100 rows × ~20 features — a few MB in memory. Linear Regression and Random Forest train in seconds to a few minutes on an ordinary laptop (4 GB+ RAM). No GPU needed. XGBoost likewise. This is the key feasibility fact: the location-based design keeps compute trivial.
- India-wide gridded training would need orders of magnitude more memory and, for deep learning, a GPU — **not feasible** on this budget (see §4.1).

**Deployment (Streamlit Community Cloud, free tier):**
- Limits (widely documented for the free tier; Streamlit's own docs should be re-checked at deployment time as limits change): **~1 GB RAM per app**, shared CPU, apps sleep after a period of inactivity (commonly cited as ~12 hours without traffic; exact figure varies by source and was **not verified against Streamlit's official docs in this research** — mark as to-confirm), unlimited public apps, public GitHub repo required, no custom domain on the free tier.
- Feasibility: **feasible.** The app loads a small CSV + a pickled sklearn model (a few MB) and renders Plotly charts — comfortably inside 1 GB if data loading is cached (`@st.cache_data`) and the model is cached (`@st.cache_resource`), and if the app does **not** load gridded NetCDF/Zarr files at runtime. Runtime API calls to Open-Meteo must be avoided or strictly cached (the app should ship with the processed CSV, not call the API on every visit — both for the rate limit and for reproducibility).
- **Fallback if Streamlit Cloud is unavailable:** run locally with `streamlit run app.py` (documented in the README) and include a short screen recording in the repo as a demo backup.

**Local environment:** Python 3.12, a virtual environment, `pip install -r requirements.txt`. Nothing in the design needs a GPU, a database server, or a paid cloud service.

---

## 10. Phased execution plan (Phases 2–7)

| Phase | Work | Realistic effort note | Exit criterion (must be met before the next phase) |
|---|---|---|---|
| **2 — Data pipeline** | Confirm IMD download links; pull Open-Meteo daily CSV for Mumbai (2000–2024); extract the IMD Mumbai grid cell for the same period; build the data-quality note (§5); save raw + processed CSVs; write the data dictionary | Days, not weeks — the Open-Meteo pull is one API call; the IMD `.grd` reader is the main work item (half a day to a day for a beginner with guidance) | Data-quality note exists; IMD-vs-Open-Meteo precipitation comparison computed and reported; no missing-% claimed without measurement |
| **3 — Machine learning** | Feature engineering per §6.2; chronological split; baselines; Linear Regression + Random Forest (+ XGBoost on evidence); regression + classification evaluation; error analysis; save best validated model | 1–2 weeks of focused work for a beginner | Every model beats (or honestly fails to beat) the baselines on the test years, with metrics computed and saved — no fabricated numbers |
| **4 — Application** | Streamlit app, 7 pages, real model outputs only; map with covered locations only; next-day forecast page (no 7-day model claims); About & Methodology page with sources, licences, limitations | 1–2 weeks | Every navigation item works; every number on screen traces to the model or the data; no decorative dead buttons |
| **5 — Testing** | Re-run pipeline from a fresh environment; test missing/invalid inputs; verify charts, location selection, startup, error handling | Days | Fresh-environment reproduction passes; test list with pass/fail recorded |
| **6 — GitHub & deployment** | Professional README (with real screenshots), repo description/topics, deploy to Streamlit Community Cloud, verify the live app | Days | Live URL verified loading; README screenshots are of the actual app |
| **7 — Portfolio presentation** | LinkedIn project description + launch post (honest: educational/research tool, not an operational forecast), demo-video plan, interview explanation sheet, technical documentation | Days | Post draft approved by Harsh before publishing; nothing published without his approval |

Total realistic scope for a beginner working alongside studies: **roughly 4–8 weeks** from Phase 2 to a deployed v1, assuming a few focused sessions per week. This is an estimate, not a commitment.

---

## 11. Limitations and risks

1. **Not an operational forecast.** The model predicts from historical patterns only. It must be labelled "educational and research-oriented predictive tool" on every page; its output must never be described as an official warning.
2. **Reanalysis ≠ observation.** Open-Meteo/ERA5 precipitation is model-derived. Cross-checking against IMD gridded rainfall is mandatory, and any disagreement must be reported, not hidden.
3. **Grid-cell ≠ city.** "Mumbai rainfall" here means the grid cell containing Mumbai (~25 km). Neighbourhood-level extremes (e.g. a cloudburst over one suburb) cannot be resolved.
4. **Extreme events are rare and hard.** Heavy/very-heavy days are a small minority; the model will likely miss some extremes (false negatives). The Extreme Rainfall module must show this honestly with a confusion matrix.
5. **IMD access friction.** Download links, the binary format, and the licence are the biggest Phase 2 unknowns. If IMD proves impractical, the fallback is Open-Meteo + CHIRPS as the cross-check — document the switch, don't silently drop the validation.
6. **CDS/ERA5 friction.** Account + licence acceptance + queued jobs + NetCDF. Avoid direct CDS use in v1; use it only if Open-Meteo lacks a needed variable.
7. **IndiaWeatherBench size/complexity.** Unverified download size; gridded deep learning is out of scope for v1.
8. **Streamlit free-tier limits.** 1 GB RAM, sleep-on-idle, public repo. Design the app to fit (cached small data + small model); keep a local-run path and a demo video as backup.
9. **Licences.** Open-Meteo CC BY 4.0 (attribution mandatory); IndiaWeatherBench CC BY-NC-SA 4.0 (non-commercial only); IMD licence text unverified — check before redistributing anything derived from IMD; ERA5 Copernicus licence (attribution). No dataset may be presented as "ours", and no raw third-party file should be committed to GitHub without checking its terms.
10. **Scope creep.** The brief lists 7 pages, a map, extremes, and a performance centre. The risk is building the shell before the model works. Mitigation: Phases 2–3 (data + model) must be complete and validated before any dashboard work in Phase 4.
11. **Interview risk (the point of the project).** Harsh must be able to explain every step. Keep the code readable, the feature list short, and the methodology section written in plain language. A model he cannot explain is worse than a simpler model he can.

---

## 12. Sources

All URLs below were used in this research (searched and/or opened 9 November 2026). Nothing has been downloaded from any of them.

- IMD gridded rainfall 0.25°: https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html
- IMD gridded temperature 1°: https://www.imdpune.gov.in/cmpg/Griddata/Max_1_Bin.html
- IMD main portal: https://mausam.imd.gov.in/
- IMD press release (rainfall classification legend): https://internal.imd.gov.in/press_release/20250222_pr_3731.pdf
- `imdR` R package (IMD download/processing): https://github.com/Subhradip25/imdR
- IndiaWeatherBench paper: https://arxiv.org/abs/2509.00653
- IndiaWeatherBench code: https://github.com/tung-nd/IndiaWeatherBench
- IndiaWeatherBench dataset (Hugging Face): https://huggingface.co/datasets/tungnd/IndiaWeatherBench
- IMDAA portal (NCMRWF): https://rds.ncmrwf.gov.in/
- Copernicus Climate Data Store: https://cds.climate.copernicus.eu/
- ERA5 download guide (ECMWF Confluence): https://confluence.ecmwf.int/pages/viewpage.action?pageId=600770874
- ERA5 reanalysis Q&A (Copernicus): https://atmosphere.copernicus.eu/reanalysis-qas
- Open-Meteo Historical Weather API docs: https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo terms (free tier, limits, CC BY 4.0): https://open-meteo.com/en/terms
- Open-Meteo forecast API (for reference only — not used in Phase 1): https://open-meteo.com/en/docs
- CHIRPS (UCSB Climate Hazards Center): https://www.chc.ucsb.edu/data/chirps
- CHIRPS data download: https://data.chc.ucsb.edu/products/CHIRPS-2.0/
- NASA POWER: https://power.larc.nasa.gov/
- NASA POWER API docs: https://power.larc.nasa.gov/docs/services/api/
- Pai et al. (2014), MAUSAM 65(1): cited via the IMD page (full reference in §2.1)
- Srivastava et al. (2009), Atmospheric Science Letters, DOI: 10.1002/asl.232 (cited via the IMD page)

### What could NOT be verified in Phase 1

- Exact per-year IMD `.grd` download URLs (page links not confirmed).
- The formal licence/terms text for IMD gridded data (no open licence found on the IMD pages).
- IndiaWeatherBench total download size.
- Exact daily variable names as returned by the Open-Meteo Archive API (documented names listed; live response not observed).
- A missing-data percentage for any dataset (no data downloaded; none invented).
- The IMD rainy-day threshold (≥ 2.5 mm) — commonly cited, not confirmed from an IMD source in this research.
- Streamlit Community Cloud's exact current sleep/idle timeout (commonly cited ~12 h; not verified against official docs).
- GHCN-Daily station availability/coverage for Mumbai specifically.
- ERA5 India-only daily download size (only a rough arithmetic estimate is given, labelled as such).
- The exact CDS catalogue URL for `reanalysis-era5-single-levels` (CDS links are session-dependent; the dataset name is verified in CDS docs).

---

## 13. Decision requested from Harsh

Please approve (or amend) before Phase 2 begins:

1. **Primary dataset:** Open-Meteo Archive API for Mumbai, cross-checked against IMD gridded rainfall.
2. **Scope:** Maharashtra-focused, Mumbai first; 5–8 Maharashtra cities only after Mumbai v1 is validated. **Not** India-wide.
3. **Problem:** next-day rainfall regression + rain/no-rain classification; extreme-rainfall (≥ 64.5 mm) classification as a secondary task. **No** 7-day model forecast claims.
4. **Models:** persistence + climatology baselines, Linear Regression, Random Forest, XGBoost only on evidence. **No LSTM in v1.**
5. **Architecture:** Python / Pandas / scikit-learn / Streamlit / SQLite / GitHub / Streamlit Community Cloud, all free, no API keys.

**No implementation until Harsh approves this report.**

---

## 13. Addendum — Harsh's clarifications (accepted 9 November 2026, part of the project requirements)

Phase 1 is accepted in principle. The following six clarifications are now binding project requirements, and Phase 2 is scoped to data acquisition, data-quality analysis, alignment, and a simple baseline experiment only. No full dashboard and no advanced model development until the data is validated.

1. **Four-way data labelling, everywhere.** Historical reanalysis, observational datasets, model predictions, and external forecasts must be clearly distinguished — in the data dictionary, in every chart, on every dashboard page, and in the README. Never mix these categories.
2. **Spatial and temporal alignment must be verified, not assumed.** Phase 2 must verify that the selected Open-Meteo and IMD datasets can be aligned meaningfully for the same Mumbai location and the same dates — same grid cell / point, same timezone, same daily aggregation — and document the alignment method and any residual mismatch (e.g. grid-cell vs point, reanalysis day definition vs IMD's 03 UTC–03 UTC day).
3. **Exact prediction definition.** Phase 2 must define and document: the prediction cutoff time, the timezone (Asia/Kolkata), the input window (which past days' data may be used), and the next-day target (t+1 rainfall, date and definition). No feature or target may be defined loosely.
4. **Leakage audit.** Every feature must be audited for future-data leakage before any model is trained. Only data dated t or earlier may be used to predict t+1. The audit result must be written down.
5. **Rainy-day threshold from an authoritative IMD reference.** The ≥2.5 mm convention must be verified and documented from an IMD source before use. Until verified, no rainy-day threshold claim may appear in the code, dashboard, or README.
6. **Reanalysis vs observation — stated plainly.** The project must explain, in the README and About page, whether the model is learning from reanalysis data or observational data, and what that means for real-world generalisation (reanalysis precipitation is model-derived and smooths local extremes; IMD gridded data are interpolated gauge observations; neither is a neighbourhood rain gauge).

Phase 2 exit criteria: (a) Open-Meteo Mumbai daily CSV acquired and documented; (b) IMD Mumbai grid-cell series acquired if the download links can be confirmed, otherwise the fallback (Open-Meteo + CHIRPS cross-check) documented and the switch explained; (c) a one-page data-quality note with real row counts, date ranges, and measured missing-value counts per variable; (d) alignment verified and documented; (e) prediction cutoff/timezone/input window/target defined; (f) leakage audit written; (g) rainy-day threshold verified from IMD or explicitly left unverified; (h) a simple baseline experiment only — persistence and day-of-year climatology on the chronological split, with MAE/RMSE reported. No dashboard, no Random Forest / XGBoost / LSTM until these are done.
