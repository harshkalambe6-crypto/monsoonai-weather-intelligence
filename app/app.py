"""MONSOONAI — Streamlit dashboard (Phase 4).

Entry point. Run from the project root:
    streamlit run app/app.py
(Use the project venv: ~/workspace/monsoonai-venv/bin/streamlit)

Navigation is the sidebar radio — six pages, every item works, no
decorative buttons. All data is loaded once here (cached) and passed
to the pages as a context dict, so no page can show a different
version of the numbers.
"""

from pathlib import Path

import streamlit as st

# app/ is a plain directory, not a package: make its own modules
# importable no matter where Streamlit is launched from.
APP_DIR = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "views"))

import data_loader
from ui_common import FOOTER_TEXT

PAGES = [
    ("Overview", "overview"),
    ("Rainfall Prediction", "prediction"),
    ("Historical Analysis", "historical"),
    ("Extreme Rainfall", "extreme"),
    ("Model Performance", "performance"),
    ("Data & Methodology", "methodology"),
]

st.set_page_config(
    page_title="MONSOONAI — Mumbai Rainfall Intelligence",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="auto",
)

# --- Visual identity: deep navy / charcoal, atmospheric blue, --------
# restrained cyan. No gradients, no animations, no decoration.
st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    .stApp { background-color: #0b1220; }
    section[data-testid="stSidebar"] { background-color: #0d1526; }
    section[data-testid="stSidebar"] .stRadio label { color: #e5e7eb; }
    h1, h2, h3 { color: #e5e7eb; letter-spacing: -0.01em; }
    p, li, .stMarkdown { color: #d1d5db; }
    .stMetric { background-color: #111a2e; border: 1px solid #24344d;
                border-radius: 10px; padding: 12px 14px; }
    .stMetric label { color: #94a3b8 !important; }
    .stMetric [data-testid="stMetricDelta"] svg { display: none; }
    .stMetric [data-testid="stMetricDelta"] { white-space: normal;
                font-size: 12px; line-height: 1.4; }
    .stDataFrame { border: 1px solid #24344d; border-radius: 8px; }
    hr { border-color: #24344d; }
    a { color: #38bdf8; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Loading MONSOONAI data and models…")
def load_context():
    """Load everything the pages need, once. Fails loudly if a
    required file is missing — the app never invents a substitute."""
    missing = data_loader.check_required_files()
    if missing:
        raise data_loader.DataLoadError(
            "Required project files are missing:\n- " + "\n- ".join(missing)
            + "\nRun Phases 2–3 first, or check the project folder.")
    daily = data_loader.load_daily()
    predictions = data_loader.load_test_predictions()
    summary = data_loader.load_summary()
    settings = data_loader.load_settings()
    imd_comparison = data_loader.load_imd_comparison()
    # Regression metrics at full precision, recomputed from the saved
    # test predictions (see data_loader.compute_regression_metrics).
    regression = data_loader.compute_regression_metrics(predictions)
    climatology_train = data_loader.load_artefact("climatology_train.joblib")
    feature_columns = data_loader.load_artefact("feature_columns.joblib")

    # Derived metrics — recomputed from the saved artefacts with the
    # same logic as src/evaluate_models.py (never hard-coded).
    from feature_engine import build_feature_table
    feature_table = build_feature_table(daily, climatology_train)
    test_table = feature_table[
        feature_table["time"] >= "2021-01-01"].reset_index(drop=True)
    classification = data_loader.compute_classification_metrics(
        test_table, feature_columns)
    feature_importance = data_loader.compute_feature_importance(feature_columns)

    return {
        "daily": daily,
        "predictions": predictions,
        "summary": summary,
        "settings": settings,
        "imd_comparison": imd_comparison,
        "climatology_train": climatology_train,
        "feature_columns": feature_columns,
        "classification": classification,
        "regression": regression,
        "feature_importance": feature_importance,
        "year_wise": data_loader.year_wise_metrics(predictions),
        "error_by_month": data_loader.error_by_month(predictions),
        "worst_misses": data_loader.worst_misses(predictions, n=10),
        "project_root": data_loader.PROJECT_ROOT,
    }


def main():
    st.sidebar.markdown(
        '<div style="padding: 6px 0 2px 0;">'
        '<span style="font-size:26px; font-weight:800; color:#e5e7eb; '
        'letter-spacing:0.02em;">MONSOONAI</span><br>'
        '<span style="font-size:12px; color:#38bdf8; letter-spacing:0.08em;">'
        'TURNING WEATHER DATA INTO PREDICTIVE INTELLIGENCE</span></div>',
        unsafe_allow_html=True)
    st.sidebar.markdown(
        '<p style="color:#94a3b8; font-size:13px;">Mumbai next-day '
        'rainfall · historical reanalysis 2000–2024 · '
        'educational / research tool</p>',
        unsafe_allow_html=True)

    page_names = [name for name, _ in PAGES]
    choice = st.sidebar.radio("Navigate", page_names, index=0)
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<p style="color:#64748b; font-size:12px; line-height:1.6;">'
        'All model metrics are performance against Open-Meteo / ERA5 '
        'reanalysis, not rain-gauge observations. No live data. No '
        'operational warnings.</p>',
        unsafe_allow_html=True)

    try:
        ctx = load_context()
    except data_loader.DataLoadError as exc:
        st.error(
            "MONSOONAI could not start — required data or model files are "
            "missing. Nothing has been invented as a substitute.\n\n" + str(exc))
        st.markdown(
            "**Fix:** run the Phase 2 data pipeline, then Phase 3 training "
            "and evaluation (see docs/local-setup.md), and reload this page.")
        st.stop()
    except Exception as exc:  # corrupt artefact, unreadable file, …
        st.error(
            "MONSOONAI could not start — the data or models could not be "
            f"loaded. ({exc})")
        st.stop()

    module_name = dict(PAGES)[choice]
    page = __import__(module_name)
    page.render(ctx)


if __name__ == "__main__":
    main()
