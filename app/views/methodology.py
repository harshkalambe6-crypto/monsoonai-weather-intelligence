"""MONSOONAI — Page 6: Data & Methodology.

Sources, alignment, spatial resolution, reanalysis limitations, feature
definitions, leakage audit summary and reproducibility. Everything a
reviewer — or an interviewer — needs to judge whether the project is
scientifically defensible.
"""

import pandas as pd
import streamlit as st

from ui_common import category_pills, footer, info_box, page_header, warning_box


def render(ctx):
    page_header(
        "Data & Methodology — how this was built",
        "Sources, alignment, limitations, features and reproducibility")
    category_pills(["reanalysis", "observation", "prediction"])

    settings = ctx["settings"]
    daily = ctx["daily"]
    imd = ctx["imd_comparison"]

    # --- Sources -------------------------------------------------------------------
    st.markdown("### Data sources")
    st.markdown(
        "| Source | Category | What it is | Licence / terms |\n"
        "|---|---|---|---|\n"
        "| **Open-Meteo Historical Weather API** (Archive API), ERA5-based | "
        "Historical reanalysis | Daily weather for one lat/lon, 1940–present; "
        "the primary dataset (9,132 days, 2000–2024) | CC BY 4.0 — "
        "attribution “Weather data by Open-Meteo.com” required |\n"
        "| **IMD 0.25° gridded rainfall** (Pai et al. 2014) | Observational "
        "data | Rain-gauge observations interpolated to a 0.25° grid, "
        "1901–2024; 2020 downloaded as the cross-check | Government data — "
        "citation required; no confirmed open licence; raw files are not "
        "redistributed |\n"
        "| **CHIRPS v2.0** | Observational data | Satellite + station "
        "precipitation, 0.05°, 1981–present | Free for research / "
        "non-commercial use; documented fallback, not used (IMD worked) |\n"
        "| **IndiaWeatherBench / IMDAA** | Historical reanalysis | Gridded "
        "benchmark, 2000–2019, 6-hourly | CC BY-NC-SA 4.0; not used as a "
        "primary source — built for spatial deep learning, not a first "
        "single-location model |\n"
        "| **ERA5 (Copernicus CDS)** | Historical reanalysis | Global "
        "reanalysis behind Open-Meteo; direct download not used in v1 | "
        "Copernicus licence, attribution required |")
    st.caption(
        "Full source list with URLs: phase1-research.md §2 and §12. "
        "No dataset was presented as downloaded or integrated unless it "
        "actually was.")

    # --- Alignment -------------------------------------------------------------------
    st.markdown("### Spatial and temporal alignment (verified in Phase 2)")
    st.markdown(
        "- **Spatial:** Open-Meteo returned the grid cell centred at "
        "**19.086115° N, 72.85291° E** for the requested Mumbai point "
        "(19.0760° N, 72.8777° E) — a few km away. Mumbai falls between "
        "IMD grid points (19.00°/19.25° N, 72.75°/73.00° E), so the IMD "
        "value used is the mean of the four surrounding points, which "
        "disagree by up to ~300 mm/year.\n"
        "- **Temporal:** Open-Meteo days are **Asia/Kolkata calendar "
        "days** (00:00–24:00 IST). IMD daily values labelled D are the "
        "24 hours ending **03:00 UTC (08:30 IST)** on D — verified from "
        "an IMD-authored report and peer-reviewed papers.\n"
        "- **Measured agreement (2020, 366 days):** same-date Pearson "
        "r = 0.704; 1-day-shifted r = 0.741 — consistent with the "
        "day-definition offset. Mean bias (Open-Meteo − IMD) "
        "−2.13 mm/day; MAE 6.71 mm/day (5.89 mm/day shifted).")
    st.markdown("#### IMD vs Open-Meteo, 2020 — the cross-check that matters")
    st.markdown(
        "- Annual totals: **IMD 3,553.0 mm vs Open-Meteo 2,773.6 mm** — "
        "reanalysis ~779 mm (**~22%**) lower.\n"
        "- Rainy days ≥ 2.5 mm: IMD 108, Open-Meteo 131, both 103, "
        "IMD-only 5, Open-Meteo-only 28.\n"
        "- Maximum daily: IMD 203.1 mm, Open-Meteo 169.8 mm.\n"
        "- The two sources agree on *when* it rains (103 of 108 IMD rainy "
        "days also rainy in Open-Meteo) but not *how much*.")
    st.dataframe(
        imd.head(10)[["time", "imd_4pt_mean", "openmeteo_mm"]].rename(
            columns={"imd_4pt_mean": "IMD 4-point mean (mm)",
                     "openmeteo_mm": "Open-Meteo (mm)"}),
        width="stretch", hide_index=True)
    st.caption("First 10 rows of the 2020 comparison table "
               "(data/processed/mumbai_imd_vs_openmeteo_2020.csv).")

    # --- Resolution and limitations ------------------------------------------------------
    st.markdown("### Spatial resolution and reanalysis limitations")
    warning_box(
        "“Mumbai rainfall” in this project means the value for the ~25 km "
        "grid cell containing Mumbai — a reanalysis grid cell, not a rain "
        "gauge in a specific neighbourhood. Neighbourhood-level extremes "
        "(e.g. a cloudburst over one suburb) cannot be resolved.")
    st.markdown(
        "- **Reanalysis ≠ observation.** Open-Meteo / ERA5 precipitation "
        "is model-derived. It underestimates annual totals by ~22% vs IMD "
        "gauge data, spreads rain over more days, and caps daily maxima "
        "lower. The model learns from reanalysis, so its test-set skill "
        "overstates real-world gauge skill — worst for heavy rain, exactly "
        "where accuracy matters most.\n"
        "- **No live data.** The reanalysis lags ~5 days behind real time; "
        "the dataset ends 31 Dec 2024. Nothing in this app is “today's "
        "weather”.\n"
        "- **One location.** Mumbai only. No India-wide or multi-city "
        "generalisation was tested or is claimed.\n"
        "- **One horizon.** Next-day (t+1) only. A 7-day forecast from "
        "lagged features alone is not defensible and is not shown.\n"
        "- **Open checks:** IMD station climatology comparison for Mumbai "
        "not yet done; only 2020 of IMD retrieved; nearest-point vs "
        "bilinear interpolation not yet compared.")

    # --- Prediction definition ---------------------------------------------------------------
    st.markdown("### Prediction definition (binding)")
    st.markdown(
        f"- **Cutoff:** end of day t, **23:59 Asia/Kolkata**.\n"
        f"- **Timezone:** Asia/Kolkata (IST, UTC+5:30), for everything.\n"
        f"- **Input window:** days **t−7 … t** (past 8 days, including today).\n"
        f"- **Target:** `precipitation_sum` on day **t+1**, in mm.\n"
        f"- **Rainy day:** ≥ 2.5 mm (IMD Met Glossary, verified).\n"
        f"- **Heavy rain:** ≥ 64.5 mm (IMD “heavy” band).\n"
        f"- **Splits (chronological, identical for every model):** train "
        f"{settings['splits']['train']}, validation "
        f"{settings['splits']['validation']}, test "
        f"{settings['splits']['test']}. Never random, never tune on test.")

    # --- Features --------------------------------------------------------------------------------
    st.markdown("### Features — 27, all dated t or earlier")
    st.markdown(
        "| Group | Features |\n"
        "|---|---|\n"
        "| Lagged rainfall | rain at t, t−1, t−2, t−3, t−7 |\n"
        "| Rolling rainfall | 3-day and 7-day sum and mean (windows end at t) |\n"
        "| Rain history | days since last rain (capped at 30); rainy days in last 7 days |\n"
        "| Temperature | max / min / mean at t; 3-day mean |\n"
        "| Humidity | relative humidity at t; 3-day mean |\n"
        "| Pressure | mean sea-level pressure at t; change over last 3 days |\n"
        "| Wind | max speed at t; direction as sin / cos |\n"
        "| Seasonal | day-of-year sin / cos; month; monsoon flag (Jun–Sep) |\n"
        "| Climatology | day-of-year mean rainfall, computed from **training data only** |")
    st.markdown(
        "**Leakage audit (Phase 2, re-audited in Phase 3): no FAILs.** "
        "Every feature uses data dated t or earlier only. Three fixes "
        "were applied in Phase 3: window widened to t−7…t so the t−7 lag "
        "sits inside it; climatology from training data only; days-since-"
        "rain capped at 30. Full audit: docs/leakage-audit.md. Feature "
        "code: src/features.py (the dashboard reuses it, it does not "
        "redefine features).")

    # --- Models ----------------------------------------------------------------------------------
    st.markdown("### Models")
    st.markdown(
        "- **Linear Regression** — pipeline: StandardScaler + "
        "LinearRegression. No hyperparameters to tune.\n"
        "- **Random Forest Regressor** — grid max_depth {None, 10, 20} × "
        "n_estimators {200, 400}, scored by validation MAE. Best: "
        "**max_depth 10, n_estimators 200** (validation MAE 3.911 mm).\n"
        "- **Logistic Regression** — rain/no-rain classifier "
        "(max_iter 1000).\n"
        "- **Random Forest Classifier** — rain/no-rain, class_weight "
        "balanced, best max_depth 10, n_estimators 400 (validation F1 "
        "0.9154). Same settings for the heavy-rain classifier.\n"
        "- **Baselines** — persistence (tomorrow = today) and day-of-year "
        "climatology (train period only). A model that cannot beat these "
        "is not a working model.\n"
        "- **Not used:** XGBoost and LSTM — deliberately excluded. XGBoost "
        "only on evidence it beats Random Forest; LSTM is not justified "
        "for 9k rows of lag features.")

    # --- Reproducibility ----------------------------------------------------------------------------
    st.markdown("### Reproducibility")
    st.markdown(
        "- **Python:** 3.12 · **Packages:** scikit-learn 1.9.1, pandas "
        "3.1.1, NumPy 2.5.4, matplotlib 3.11.2, joblib 1.6.0, "
        "Streamlit 1.67.0, Plotly 7.1.0\n"
        "- **Random seed:** 42 (fixed in training and evaluation).\n"
        "- **Data:** data/processed/mumbai_daily_2000-2024.csv "
        "(9,132 rows × 14 columns, 0 missing values).\n"
        "- **Re-run training and evaluation:**\n"
        "```\n"
        "~/workspace/monsoonai-venv/bin/python src/train_models.py\n"
        "~/workspace/monsoonai-venv/bin/python src/evaluate_models.py\n"
        "```\n"
        "- **Run this dashboard locally:** see docs/local-setup.md "
        "(or app/README.md). No deployment has been done — the app runs "
        "on your own machine only until deployment is separately approved "
        "and verified.")
    info_box(
        "Interview explanation, in one sentence: “I predicted next-day "
        "Mumbai rainfall from the last 8 days of reanalysis weather, "
        "compared Linear Regression and Random Forest against persistence "
        "and climatology baselines on a strict chronological split, and "
        "reported the honest result — strong rain/no-rain classification, "
        "modest rainfall-amount skill, and heavy-rain prediction that "
        "does not work yet.”")

    footer()
