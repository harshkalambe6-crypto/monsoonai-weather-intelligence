# MONSOONAI — Local Setup Guide (Phase 4)

Run the dashboard on your own machine. No deployment, no accounts,
no API keys, no paid services.

## Requirements

- Python 3.12
- The project folder (`monsoonai/`) with Phases 2–3 complete:
  `data/processed/mumbai_daily_2000-2024.csv`,
  `artifacts/*.joblib`, `artifacts/evaluation_summary.json`,
  `artifacts/predictions_test.csv`. If any of these are missing, the
  app shows a clear error and does not start — it never invents data.

## Steps

```bash
# 1. Create the virtual environment (once)
python3 -m venv ~/workspace/monsoonai-venv
source ~/workspace/monsoonai-venv/bin/activate

# 2. Install the pinned dependencies (once)
pip install -r app/requirements.txt

# 3. Start the dashboard (from the project root)
streamlit run app/app.py
```

Open the URL Streamlit prints — usually http://localhost:8501.

## Reproduce the models (optional)

```bash
~/workspace/monsoonai-venv/bin/python src/train_models.py
~/workspace/monsoonai-venv/bin/python src/evaluate_models.py
```

## Refreshing the data (optional)

The dashboard uses the local processed dataset (through 31 Dec 2024).
To refresh it with newer archive data, re-run the Phase 2 pipeline
(`src/prepare_mumbai_daily.py`, then re-train with the commands
above). The Rainfall Prediction page has a button that checks whether
newer Open-Meteo archive data exists; it reports the result and never
auto-refreshes.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: streamlit` | Activate the venv first (`source ~/workspace/monsoonai-venv/bin/activate`), then `pip install -r app/requirements.txt`. |
| App shows “required data or model files are missing” | Phases 2–3 are not complete in this folder. Run the data pipeline and training (commands above). |
| Port 8501 already in use | `streamlit run app/app.py --server.port 8502` |
| Charts or pages look broken on a phone | The layout is responsive, but the desktop view is the primary one; report the screen width and page if something overflows. |

## What is NOT set up here

- No deployment (Streamlit Community Cloud is a Phase 6 task, on
  approval, verified live before it is claimed).
- No live weather feed. The app reads the local dataset only.
