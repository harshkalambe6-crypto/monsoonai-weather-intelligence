# Config

There are no separate configuration files for this project yet.

The experiment settings that would normally live here are recorded
in `artifacts/training_settings.json` (random seed 42, chronological
splits, input window, thresholds, hyperparameter grids and the
selected hyperparameters, and the 27 feature names) and in
`artifacts/evaluation_summary.json` (the measured test metrics).

If the project grows — for example, a second city — put the
per-location settings (coordinates, date ranges, thresholds) in a
file here instead of hard-coding them in `src/`.
