"""
MONSOONAI — Phase 2 IMD cross-check extraction
================================================
Reads the IMD 0.25-degree daily gridded rainfall file for 2020
(data/raw/ind2020_rfp25.grd) and extracts the four grid points
surrounding Mumbai, then compares them with the Open-Meteo
(reanalysis) precipitation for the same year.

IMD file layout (from the IMD Pune page):
  * One record per day, 366 records for leap year 2020.
  * Each record: 135 (longitude) x 129 (latitude) float32 values.
  * First value is at 6.5 N, 66.5 E; last at 38.5 N, 100.0 E.
  * Longitude is fastest within a record, latitude ascending.
  * Value = rainfall in mm; -999.0 = undefined (sea / outside India).
  * Record 1 = 1 January 2020.

IMD day convention (VERIFIED, see docs/crosscheck-and-threshold.md):
  each IMD value labelled D is the 24 h accumulation ending 03:00 UTC
  (08:30 IST) on day D — i.e. mostly the previous calendar day.
  So the comparison is reported BOTH same-date and with the IMD
  series shifted by one day (IMD label D compared with Open-Meteo
  date D-1), and the residual mismatch is stated plainly.

Mumbai (19.0760 N, 72.8777 E) falls BETWEEN grid points:
  nearest longitudes 72.75 E / 73.00 E, latitudes 19.00 N / 19.25 N.
  The four surrounding points are extracted and averaged (simple mean
  of the four = a documented, simple choice; bilinear interpolation
  would be a Phase 3 refinement, not assumed here).

Run:  python3 src/extract_imd_mumbai.py
"""

import numpy as np
import pandas as pd

N_LON, N_LAT = 135, 129
LAT0, LON0, STEP = 6.5, 66.5, 0.25
MISSING = -999.0

raw = np.fromfile("data/raw/ind2020_rfp25.grd", dtype="<f4")
n_days = raw.size // (N_LON * N_LAT)
assert n_days == 366, f"expected 366 days, got {n_days}"
grid = raw.reshape(n_days, N_LAT, N_LON)  # [day, lat, lon]

# Grid indices for the four points around Mumbai.
lat_idx = {19.00: int(round((19.00 - LAT0) / STEP)),
           19.25: int(round((19.25 - LAT0) / STEP))}
lon_idx = {72.75: int(round((72.75 - LON0) / STEP)),
           73.00: int(round((73.00 - LON0) / STEP))}

dates = pd.date_range("2020-01-01", periods=n_days)
cols = {}
for lat, li in lat_idx.items():
    for lon, ji in lon_idx.items():
        s = grid[:, li, ji].astype(float)
        s[s == MISSING] = np.nan
        cols[f"imd_{lat}N_{lon}E"] = s
imd = pd.DataFrame(cols, index=dates)
imd["imd_4pt_mean"] = imd.mean(axis=1)

om = pd.read_csv("data/processed/mumbai_daily_2000-2024.csv",
                 parse_dates=["time"])
om2020 = om[(om["time"] >= "2020-01-01") & (om["time"] <= "2020-12-31")].copy()
om2020 = om2020.set_index("time")

both = imd.join(om2020[["precipitation_sum"]], how="inner")
both = both.rename(columns={"precipitation_sum": "openmeteo_mm"})
print(f"overlapping days: {len(both)}")
print("\n2020 annual totals (mm):")
for c in imd.columns:
    print(f"  {c}: {both[c].sum():.1f}")
print(f"  openmeteo: {both['openmeteo_mm'].sum():.1f}")

# Same-date comparison and 1-day-shifted comparison (IMD label D vs
# Open-Meteo D-1, matching the 03 UTC day convention).
for label, om_series in [("same date", both["openmeteo_mm"]),
                         ("IMD shifted +1d (IMD D vs OM D-1)",
                          both["openmeteo_mm"].shift(1))]:
    sub = pd.DataFrame({"imd": both["imd_4pt_mean"], "om": om_series}).dropna()
    corr = sub["imd"].corr(sub["om"])
    bias = (sub["om"] - sub["imd"]).mean()
    mae = (sub["om"] - sub["imd"]).abs().mean()
    print(f"\n{label}: n={len(sub)}, Pearson r = {corr:.3f}, "
          f"mean bias (OM - IMD) = {bias:.3f} mm/day, MAE = {mae:.3f} mm/day")

# Rainy-day agreement at the VERIFIED IMD threshold (>= 2.5 mm).
both["imd_rainy"] = both["imd_4pt_mean"] >= 2.5
both["om_rainy"] = both["openmeteo_mm"] >= 2.5
print("\nRainy days >= 2.5 mm in 2020:")
print(f"  IMD 4-pt mean: {both['imd_rainy'].sum()}, "
      f"Open-Meteo: {both['om_rainy'].sum()}, "
      f"both: {(both['imd_rainy'] & both['om_rainy']).sum()}, "
      f"IMD only: {(both['imd_rainy'] & ~both['om_rainy']).sum()}, "
      f"OM only: {(~both['imd_rainy'] & both['om_rainy']).sum()}")
print(f"  max daily: IMD {both['imd_4pt_mean'].max():.1f} mm, "
      f"OM {both['openmeteo_mm'].max():.1f} mm")

both.to_csv("data/processed/mumbai_imd_vs_openmeteo_2020.csv")
print("\nsaved data/processed/mumbai_imd_vs_openmeteo_2020.csv")
