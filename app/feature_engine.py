"""
MONSOONAI dashboard — feature engineering bridge (Phase 4)
===========================================================
Reuses src/features.py (Phase 3) instead of duplicating the feature
definitions. If the feature definitions ever change, they change in
one place (src/) and the dashboard follows automatically.

The only dashboard-specific piece is building the feature row for a
cutoff day t whose t+1 has not happened yet (the last day in the
dataset): a dummy next-day row is appended so build_features() can
compute the row for t, then the dummy row itself is discarded. The
dummy row carries no weather data, so no t+1 information can leak
into the features for t.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
SRC_FEATURES = PROJECT_ROOT / "src" / "features.py"

_spec = importlib.util.spec_from_file_location(
    "monsoonai_src_features", SRC_FEATURES)
_src = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_src)

# Re-exported, so the rest of the app uses these names only.
build_features = _src.build_features
FEATURE_COLUMNS = _src.FEATURE_COLUMNS
RAINY_DAY_MM = _src.RAINY_DAY_MM
HEAVY_MM = _src.HEAVY_MM
DAYS_SINCE_RAIN_CAP = _src.DAYS_SINCE_RAIN_CAP


def build_feature_table(daily_df, climatology_train):
    """Full feature table for the whole daily series (as in Phase 3)."""
    return build_features(daily_df, climatology_train)


def feature_row_for_cutoff(daily_df, climatology_train, cutoff_date):
    """Feature row for one cutoff day t (the day the prediction is made).

    daily_df: the processed daily series, sorted by date.
    cutoff_date: a pandas Timestamp for day t. Must be a date present
        in daily_df (the last available date is the usual case).
    Returns a one-row DataFrame with the 27 feature columns, or None
    if the date is not in the series or is too early (before t-7
    history exists).
    """
    df = daily_df.sort_values("time").reset_index(drop=True)
    if cutoff_date not in set(df["time"]):
        return None
    # Append a dummy row for t+1: a copy of the last real row with its
    # weather values set to NaN (keeps the numeric dtypes intact) and
    # its date moved to t+1 — except precipitation_sum, which is set to
    # 0.0 so that build_features() gives day t a (discarded) target
    # instead of dropping the row for a NaN target. That 0.0 never
    # becomes an input: no feature of t uses t+1 data (all windows end
    # at t), and the dummy row's own features are discarded.
    dummy = df.iloc[[-1]].copy()
    for col in dummy.columns:
        if col != "time":
            dummy[col] = np.nan
    dummy["precipitation_sum"] = 0.0
    dummy["time"] = pd.Timestamp(cutoff_date) + pd.Timedelta(days=1)
    extended = pd.concat([df, dummy], ignore_index=True)
    table = build_features(extended, climatology_train)
    row = table[table["time"] == pd.Timestamp(cutoff_date)]
    if row.empty:
        return None
    return row[FEATURE_COLUMNS].reset_index(drop=True)
