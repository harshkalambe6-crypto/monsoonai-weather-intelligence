# MONSOONAI — GitHub Publishing & Deployment Guide (Phase 6)

Prepared 9 November 2026. The repository does **not** exist yet and
nothing has been pushed or deployed. This document is the exact
checklist for the parent agent (which has the browser) to follow.

## 1. GitHub About text (set after the repo is created)

**Description:**

> MONSOONAI — AI-powered weather intelligence for Mumbai: next-day rainfall prediction from historical reanalysis, honestly evaluated. Educational/research tool, not an operational forecast.

**Topics:**

`python`, `pandas`, `scikit-learn`, `streamlit`, `machine-learning`, `weather`, `rainfall-prediction`, `monsoon`, `india`, `data-science`

**Website:** leave empty until Streamlit Cloud gives a live URL (see §4).
Do not add any other link.

## 2. Create the repository (browser — Muse cannot create repos via the API)

1. Sign in to GitHub as **harshkalambe6-crypto**.
2. Create a new repository:
   - **Name:** `monsoonai-weather-intelligence`
   - **Visibility:** Public
   - **Branch:** `main`
   - Do **not** initialise with a README, `.gitignore`, or licence —
     all files come from the push below. (Initialising would create
     a commit the push must then overwrite.)
3. Confirm the empty repo exists at
   `https://github.com/harshkalambe6-crypto/monsoonai-weather-intelligence`.

## 3. Push the files

The local source directory is:

```
/home/hatch/workspace/your_files/monsoonai/
```

### 3a. Text files — snapshot push (44 files, ~1.6 MB total, under the 16 MiB limit)

Push these with the snapshot-push procedure
(`/opt/hatch/bin/github push-files`, NUL-delimited manifest,
branch `main`, source dir as above):

```
README.md
LICENSE
.gitignore
requirements.txt
runtime.txt
app/.streamlit/config.toml
app/README.md
app/app.py
app/charts.py
app/data_loader.py
app/feature_engine.py
app/predict.py
app/requirements.txt
app/ui_common.py
app/views/__init__.py
app/views/extreme.py
app/views/historical.py
app/views/methodology.py
app/views/overview.py
app/views/performance.py
app/views/prediction.py
artifacts/evaluation_summary.json
artifacts/predictions_test.csv
artifacts/training_settings.json
config/README.md
data/processed/mumbai_daily_2000-2024.csv
data/processed/mumbai_imd_vs_openmeteo_2020.csv
docs/baseline-results.md
docs/crosscheck-and-threshold.md
docs/data-quality-note.md
docs/data-sources.md
docs/github-publishing.md
docs/leakage-audit.md
docs/local-setup.md
docs/model-evaluation-report.md
docs/openmeteo-request-url.txt
docs/phase1-research.md
docs/phase4-completion-report.md
docs/prediction-definition.md
notebooks/README.md
src/baseline_experiment.py
src/evaluate_models.py
src/extract_imd_mumbai.py
src/features.py
src/prepare_mumbai_daily.py
src/train_models.py
tests/screenshot.py
tests/test_app.py
```

Suggested commit message:

```
Initial commit: MONSOONAI — Mumbai next-day rainfall prediction (Phases 1-4)
```

After the push, record the commit SHA in the sync record beside the
source directory, as with the other projects.

### 3b. Binary files — GitHub web UI (19 files, ~21.5 MB total)

The snapshot push cannot carry binaries, so these go through the
GitHub web UI (Upload files) into the same paths. Largest single
file: `artifacts/random_forest_classifier.joblib` (10,735,673 bytes)
— well under GitHub's 100 MB per-file limit. No file exceeds 50 MB;
nothing was excluded for size.

**Model artefacts (7 files, ~20.2 MB) — the app cannot run without them:**

```
artifacts/linear_regression.joblib            (2,745 bytes)
artifacts/logistic_regression.joblib          (2,817 bytes)
artifacts/random_forest_regressor.joblib      (7,046,641 bytes)
artifacts/random_forest_classifier.joblib     (10,735,673 bytes)
artifacts/random_forest_heavy_classifier.joblib (2,411,033 bytes)
artifacts/feature_columns.joblib              (390 bytes)
artifacts/climatology_train.joblib            (9,612 bytes)
```

**Evaluation figures (4 files, ~0.4 MB):**

```
docs/figures/actual_vs_predicted_scatter.png
docs/figures/test_timeseries.png
docs/figures/error_by_month.png
docs/figures/residuals_vs_observed.png
```

**Dashboard screenshots (8 files, ~0.8 MB):**

```
assets/screenshots/01-overview-desktop.png
assets/screenshots/02-prediction-desktop.png
assets/screenshots/03-historical-desktop.png
assets/screenshots/04-extreme-desktop.png
assets/screenshots/05-performance-desktop.png
assets/screenshots/06-methodology-desktop.png
assets/screenshots/01-overview-mobile.png
assets/screenshots/02-prediction-mobile.png
```

Verify after uploading: the repo file listing shows all 7 joblib
files under `artifacts/`, and the README's screenshot images render
(they reference `assets/screenshots/...`).

### 3c. Files deliberately NOT pushed

| File / folder | Size | Why excluded |
|---|---|---|
| `data/raw/ind2020_rfp25.grd` | 25,495,560 bytes | IMD binary; must not be redistributed. Reproduce with the commands in `docs/data-sources.md`. |
| `data/raw/mumbai_openmeteo_daily_2000-2024.csv` | ~0.5 MB | Raw intermediate; the processed CSV is committed instead. Reproducible from the URL in `docs/data-sources.md`. |
| `data/raw/mumbai_openmeteo_hourly_2000-2024.csv` | 8.5 MB | Hourly intermediate used only to compute daily means. Reproducible from the URL in `docs/data-sources.md`. |
| `__pycache__/`, `*.pyc` | — | Bytecode; covered by `.gitignore`. |
| `.venv/` / venv | — | The virtual environment lives outside the repo. |
| Playwright Chromium | — | Local screenshot tooling only; not a project file. |

## 4. Deploy to Streamlit Community Cloud

**Prerequisite:** the repo from §2–3 must exist and contain
`app/app.py`, `requirements.txt`, `runtime.txt`, `artifacts/` and
`data/processed/`. Do not start this step before the binary uploads
in §3b are verified — the app fails to start without the joblib files.

1. Sign in to https://share.streamlit.io/ with the GitHub account
   **harshkalambe6-crypto** (Streamlit Community Cloud, free tier).
2. **New app** → **Use existing repo**:
   - Repository: `harshkalambe6-crypto/monsoonai-weather-intelligence`
   - Branch: `main`
   - Main file path: `app/app.py`
3. **Advanced settings:** confirm the Python version is **3.12**
   (the repo's `runtime.txt` pins `python-3.12`; if Streamlit
   offers a version choice, pick 3.12 — the default Python 3.14
   broke the Supermarket project deploy for the same reason).
4. **Deploy.** First build takes a few minutes (it installs the
   pinned dependencies). First page load takes ~6 seconds
   (model artefacts loading).
5. **Verify before claiming anything is live:**
   - Open the Streamlit URL in a logged-out / fresh browser session.
   - Check the Overview page loads with 9,132 days, 2,080 mm mean
     annual rainfall, and the headline results (RF MAE 4.191,
     LR RMSE 11.059 / R² 0.493, F1 0.880).
   - Open all six pages; check the Extreme Rainfall page shows
     precision 0.137 / 88 false alarms and the "NOT suitable for
     operational warnings" statement.
   - Check the Rainfall Prediction page shows the "NOT a live
     forecast" label and the 2025-01-01 historical demonstration.
   - Only after all of that passes, add the Streamlit URL to the
     repo's Website field (§1) and update the README status line
     ("Deployment: pending" → the live URL).
6. **If the deploy fails:** read the Streamlit Cloud logs first.
   Common causes: a missing joblib file (§3b not completed),
   a wrong Python version (must be 3.12), or a dependency install
   failure (pinned versions are in `requirements.txt`). Do not
   change the app code to work around a deploy failure without
   recording what changed and re-running `tests/test_app.py`.

## 5. After deployment — Phase 7 (separate step, Harsh's approval)

- LinkedIn project description + launch post (honest: educational /
  research tool, heavy-rain weakness stated, no operational
  forecast claim). Draft for approval first; nothing published
  without Harsh's approval.
- Demo-video plan and interview explanation sheet.
- The README status line and this document updated with the live URL.
