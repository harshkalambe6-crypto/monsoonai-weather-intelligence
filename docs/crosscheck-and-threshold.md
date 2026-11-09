# MONSOONAI Phase 2 — IMD cross-check + rainy-day threshold verification

Date: 2026-11-09 (checks run ~07:37–07:45 UTC / ~13:07–13:15 IST)
Scope: facts only. Anything not verified is marked UNVERIFIED. No dashboard, no model built.

## Verdicts (summary)

| Item | Verdict |
|---|---|
| IMD 0.25° gridded rainfall, 2020 file | **DOWNLOADED AND VERIFIED** — `data/raw/ind2020_rfp25.grd`, 25,495,560 bytes (exact expected size) |
| CHIRPS fallback | **NOT USED** — not needed; IMD download succeeded |
| IMD daily rainfall-day convention (03 UTC–03 UTC) | **VERIFIED** (via IMD-authored report + peer-reviewed papers citing Pai et al. 2014; see §3) |
| Rainy-day threshold ≥ 2.5 mm | **VERIFIED** (IMD Met Glossary + IMD publication on mausam.imd.gov.in; see §4) |

---

## 1. TASK A — IMD gridded rainfall cross-check

### 1.1 Source page

- Page: https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html
  ("Climate Monitoring and Prediction Group — Yearly Gridded Rainfall (0.25 x 0.25) data Binary File")
- Fetched 2026-11-09 (page text via browser.open; raw HTML via curl, 14,159 bytes). The page states:
  - "IMD New High Spatial Resolution (0.25X0.25 degree) Long Period (1901-2024) Daily Gridded Rainfall Data Set Over India."
  - "Data is arranged in 135x129 grid points."
  - "The first data in the record is at 6.5N & 66.5E … The last data record corresponds to 38.5N & 100.0E."
  - "The yearly data file consists of 365/366 records corresponding to non leap/ leap years."
  - Citation: Pai D.S. et al., 2014, MAUSAM, 65, 1, pp 1–18.
  - Contact: Climate Prediction Group, IMD Pune; cmagpune@gmail.com.
- **There is no direct download link on the page.** The only links in the HTML are CSS files, `#`, and the reference paper `ref_paper_MAUSAM.pdf`. Downloads are served by an HTML **POST form**, not a GET link:
  - `<form name="rain" action="rainfall.php" method="post">` with a `<select name="rain">` of years 1901–2025 and a "Download" submit button.

### 1.2 Download attempt (2020) — SUCCEEDED

Because there is no direct URL, the form was submitted with curl:

```
curl -sL -A "Mozilla/5.0" -d "rain=2020" \
  "https://www.imdpune.gov.in/cmpg/Griddata/rainfall.php" \
  -o ind2020_rfp25.grd
```

- HTTP 200, `Content-Type: application/octet-stream`,
  `Content-disposition: attachment; filename=Rainfall/ind2020_rfp25.grd`.
- File on disk: `data/raw/ind2020_rfp25.grd`
- Size: **25,495,560 bytes**
- Expected size: 135 × 129 grid × 366 days (2020 is a leap year) × 4 bytes/float
  = 135 × 129 × 366 × 4 = **25,495,560 bytes — exact match**.
- SHA-256: `e19532760221e68711132c98f05cc3ceb7b399e55dbe9bd35b02589bbf2e46ff`
- No direct-download URL for a yearly `.grd` file exists on this page; the working
  route is the POST above. (A GET on `rainfall.php` without the form field was not
  tried — the POST is the page's own mechanism and it worked.)

### 1.3 Binary verification (read as little-endian float32, 366 records of 135×129)

- Total floats: 6,373,890 (= 366 × 135 × 129). ✓
- Missing-value code −999.0: 4,557,066 values (grid points outside India / sea — expected for a land-only product on a rectangular grid).
- All other values ≥ 0.0; global max 539.9 mm in a day; only 4 values > 500 mm.
- No negative values other than −999.0.
- Mumbai check — Mumbai (19.0760° N, 72.8777° E) falls **between** grid points
  (grid spacing 0.25°; nearest longitudes 72.75° E / 73.00° E, nearest latitudes
  19.00° N / 19.25° N). Annual totals and rainy-day counts (≥ 2.5 mm) for 2020
  at the four surrounding grid points:

  | Grid point | 2020 total (mm) | Rainy days ≥ 2.5 mm | Max daily (mm) |
  |---|---|---|---|
  | 72.75° E, 19.00° N | 3,563.3 | 103 | 273.4 |
  | 73.00° E, 19.00° N | 3,507.3 | 92 | 300.6 |
  | 72.75° E, 19.25° N | 3,730.0 | 105 | 239.9 |
  | 73.00° E, 19.25° N | 3,411.6 | 101 | 186.8 |

  - January days are 0.0 mm at all four points; the daily maxima fall in the
    June–August monsoon window. Values are internally plausible (non-negative,
    monsoon-seasonal, −999 only off-land).
  - **Open check for Phase 2:** these grid-point annual totals (~3,400–3,700 mm)
    have NOT yet been compared against an IMD station climatology for Mumbai,
    and the four surrounding grid points disagree with each other by up to
    ~300 mm/year. Choice of grid point (nearest vs bilinear interpolation) and a
    station comparison are still to be decided — do not treat any single grid
    point as "Mumbai rainfall" without that step.

### 1.4 CHIRPS fallback — NOT USED

- IMD succeeded, so no CHIRPS data was downloaded. No CHIRPS file is on disk.
- Fallback reference (for the record only, not used):
  https://data.chc.ucsb.edu/products/CHIRPS-2.0/ (global daily, 0.05°, 1981–present, NetCDF).
  The global daily files are large; a point extraction for Mumbai would need a
  subsetting route, which was not pursued because it was not needed.
- Consequence: the cross-check dataset currently on disk is IMD-only (one year,
  2020). Multi-year IMD downloads (e.g. 2000–2024) and any CHIRPS comparison
  remain Phase 2 work, not done here.

---

## 2. (Task A3) IMD daily rainfall-day convention

**Verdict: VERIFIED — each IMD daily value is the 24-hour accumulation ending at
03:00 UTC (08:30 IST) on the labelled date; i.e. the labelled date is the date
the gauge was read, and the accumulation runs 03:00 UTC previous day → 03:00 UTC
labelled date.**

Caveat: the IMD download page itself (§1.1) states **no** day convention, so
verification comes from IMD-authored reports and peer-reviewed papers citing the
dataset's source paper (Pai et al. 2014), not from the download page.

Evidence:

1. IMD-authored cyclone report (RSMC New Delhi, IMD):
   https://rsmcnewdelhi.imd.gov.in/uploads/report/26/26_627fa8_Deep%20Depression%20over%20Bay%20of%20Bengal%20during%2011-14%20Oct%202020.pdf
   > "The daily rainfall distribution **ending at 0300 UTC** of each date during
   > 09-15 October, 2020 based on merged gridded rainfall data of IMD/NCMRWF…"
   > "The 24 hour cumulative rainfall (≥ 7 cm) **ending at 0300 UTC (0830 hours IST)**
   > of date during 11th th October 2020…"

2. Peer-reviewed paper (Beria et al., Hydrol. Earth Syst. Sci., 21, 6117–2017,
   on the IMD gridded dataset, citing Pai et al. 2014):
   https://hess.copernicus.org/articles/21/6117/2017/hess-21-6117-2017.pdf
   > "It is to be noted that **IMD measures rainfall accumulation at 08:30 IST
   > (Indian Standard time or 03:00 UTC). The accumulated rainfall for the
   > previous day is provided as the rainfall estimate for the current day.**
   > For instance, the IMD rainfall estimate at a gauging station for
   > 14 September 2014 refers to the rainfall accumulation from **08:30 IST
   > (03:00 UTC) on 13 September 2014 to 08:30 IST (03:00 UTC) on
   > 14 September 2014**."

3. Corroborating recent paper (arXiv, WRF study over the Western Himalaya,
   citing Pai et al. 2014): https://arxiv.org/pdf/2610.17896.pdf
   > "The IMD gridded product does not [accumulate on the UTC calendar day]:
   > **each daily value represents the 24 hours ending at 0830 IST, that is
   > 0300 UTC (Pai et al. 2014)**… the accumulation from 0830 IST of one day
   > to 0830 IST of the next is reported as the daily rainfall of the later
   > day… The label therefore corresponds to the date on which the gauge was
   > read, not the date on which most of the rain fell."

**Implication for MONSOONAI (Phase 2, not resolved here):** the IMD date label is
offset by ~1 day relative to a UTC/IST calendar-day accumulation such as the
Open-Meteo daily series already on disk
(`data/raw/mumbai_openmeteo_daily_2000-2024.csv`). Any IMD ↔ Open-Meteo
comparison must apply an explicit, documented date shift (IMD date *d* ≈
accumulation ending 08:30 IST on *d*); do not join the two series on the raw
date column.

---

## 3. TASK B — Rainy-day threshold (≥ 2.5 mm)

**Verdict: VERIFIED — IMD defines a rainy day as a day with rainfall of
2.5 mm or more.**

### Primary citations

1. **IMD Met Glossary (IMD, Pune)** — "Rainy Day" entry (document is IMD Pune's
   own glossary; consulted via the studyres mirror, as no live imdpune.gov.in
   copy of the glossary was located in this check):
   https://studyres.com/doc/2399302/met-glossary----imd---pune
   > "**Rainy Day — Rainfall amount realised in a day is 2.5 mm or more.**"
   The same glossary is internally consistent: "Light rain — Rainfall amount
   realised in a day is between 2.5 to 7.5 mm", "Very light rain — … 0.1 to
   2.4 mm", and spatial-distribution classes count stations "reporting at
   least 2.5 mm rainfall".

2. **IMD publication, mausam.imd.gov.in** (Northeast monsoon chapter, using the
   IMD gridded data 1972–2021 — i.e. the same dataset as §1):
   https://mausam.imd.gov.in/responsive/pdf_viewer_css/met1/Chapter-3 page 37-51/Chapter-3 .2.pdf
   > "**During the NE monsoon season, a rainy day is assumed to be a day with
   > rainfall of 2.5 mm or more.** Fig. 3.4 shows the spatial distribution of
   > the mean number of rainy days during the NE monsoon season."
   > Fig. 3.4 is captioned "Number of rainy days (> 2.5mm) during October to
   > December (1972-2021). Source: IMD gridded Data".

3. **MAUSAM journal paper by IMD authors** (Dubey & Krishnakumar, "Trends in
   precipitation extremes over Central India", MAUSAM 65(1), 2014):
   https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/download/928/773/3337
   > "IMD definition a 'rainy day' is a day when the rainfall amount is **equal
   > to or exceeding 2.5 mm**."

### Attempts that did not add a citation

- IMD FAQ PDF `http://imd.gov.in/section/nhac/wxfaq.pdf` (cited as the IMD
  source of the same definition in an IIT Bombay PoCRA note,
  https://www.cse.iitb.ac.in/~pocra/Dashboard_map_definitions.pdf):
  a fetch of this URL failed in the text-fetch tool and was **not retried**;
  it is recorded here as inconclusive, not as evidence. It is not needed —
  citations 1–3 above already verify the threshold.

### Note on wording

Sources phrase the boundary as "2.5 mm or more" / "equal to or exceeding
2.5 mm" (inclusive). The MAUSAM paper and the IMD monsoon chapter both use
the inclusive form; use `rainfall >= 2.5` mm, not `> 2.5` mm. (One figure
caption writes "(> 2.5mm)" loosely; the definitional text is inclusive.)

---

## 4. Files produced / changed

| Path | What it is |
|---|---|
| `data/raw/ind2020_rfp25.grd` | IMD 0.25° daily gridded rainfall, 2020 (leap year, 366 records), 25,495,560 bytes, SHA-256 `e1953276…2e46ff` — **new, this task** |
| `docs/crosscheck-and-threshold.md` | This document — **new, this task** |
| `data/raw/mumbai_openmeteo_daily_2000-2024.csv` | Pre-existing (Phase 1/2 Open-Meteo); untouched |
| `data/raw/mumbai_openmeteo_hourly_2000-2024.csv` | Pre-existing; untouched (noted as present on disk; not used here) |

## 5. Remaining UNVERIFIED / open items for Phase 2

- **UNVERIFIED:** whether the IMD download page's 2025 option is complete data
  (page lists 2025; only 2020 was downloaded).
- **UNVERIFIED:** IMD Mumbai grid-point totals vs IMD station climatology
  (§1.3 open check); grid-point selection / interpolation method undecided.
- **UNVERIFIED:** the exact IMD ↔ Open-Meteo date alignment for the 2000–2024
  comparison (convention verified in §2; the applied shift is a Phase 2 decision).
- **UNVERIFIED:** no live imdpune.gov.in copy of the Met Glossary was located;
  the glossary citation rests on the studyres mirror of IMD Pune's document,
  corroborated by the mausam.imd.gov.in publication and the MAUSAM paper.
- CHIRPS was not obtained; a CHIRPS-based cross-check is still available as a
  future fallback but was not needed here.
- Only ONE IMD year (2020) was downloaded, per the task. Multi-year retrieval
  (2000–2024) is not done.
