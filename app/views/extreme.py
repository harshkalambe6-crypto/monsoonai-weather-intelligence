"""MONSOONAI — Page 4: Extreme Rainfall.

The honest heavy-rain story, prominently: missed events, false alarms,
precision and recall. Heavy-rain prediction is the weakest part of
this project and this page says so first — it is a finding, not a
failure to hide. Nothing here may be read as an operational warning.
"""

import pandas as pd
import streamlit as st

from ui_common import category_pills, footer, page_header, warning_box


def render(ctx):
    page_header(
        "Extreme Rainfall — what the models can and cannot do",
        "Heavy rain (≥ 64.5 mm, IMD band) in the test period 2021–2024 · "
        "21 heavy days out of 1,460")
    category_pills(["reanalysis", "prediction"])

    cls = ctx["classification"]
    heavy_clf = cls["heavy_classifier"]
    thresholded = cls["heavy_thresholded"]
    worst = ctx["worst_misses"]

    warning_box(
        "NOT suitable for operational warnings. Heavy-rain prediction is "
        "currently unreliable: the dedicated classifier catches 14 of 21 "
        "heavy days but raises 88 false alarms, and the regression models "
        "catch 0–2 of 21. Do not use this system to decide whether heavy "
        "rain will occur. MONSOONAI is an educational / research tool.")

    # --- The headline numbers, prominently -----------------------------------
    st.markdown("### Dedicated heavy-rain classifier (Random Forest, test period)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Precision", f"{heavy_clf['precision_heavy']:.3f}",
                "13.7% of heavy alarms were real")
    col2.metric("Recall", f"{heavy_clf['recall_heavy']:.3f}",
                "14 of 21 heavy days caught")
    col3.metric("False alarms", "88",
                "~6 false alarms per catch")
    col4.metric("F1 score", f"{heavy_clf['f1_heavy']:.3f}",
                "accuracy is meaningless here")
    st.markdown(
        "Confusion matrix [[true negatives, false positives], "
        "[false negatives, true positives]]: "
        f"**{heavy_clf['confusion']}** — 1,351 correct non-heavy days, "
        "88 false alarms, 7 missed heavy days, 14 caught. A model that "
        "always predicted “not heavy” would score 98.6% accuracy and be "
        "useless, which is why accuracy is not the headline metric.")

    # --- Regression models thresholded ----------------------------------------
    st.markdown("### Regression models, thresholded at 64.5 mm")
    st.markdown(
        "What happens if we simply call a day “heavy” whenever a "
        "regression model predicts ≥ 64.5 mm?")
    rows = []
    for name, vals in thresholded.items():
        label = {"linear_regression": "Linear Regression",
                 "random_forest": "Random Forest",
                 "persistence": "Persistence (tomorrow = today)"}[name]
        rows.append({
            "Model": label,
            "Predicted heavy days": vals["predicted_heavy"],
            "Caught (TP)": vals["tp"],
            "False alarms (FP)": vals["fp"],
            "Missed (FN)": vals["fn"],
            "Precision": round(vals["precision"], 3),
            "Recall": round(vals["recall"], 3),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.markdown(
        "**Linear Regression caught none of the 21 heavy days. Random "
        "Forest caught 2. Persistence — simply repeating today's rain — "
        "caught 6**, because heavy rain in Mumbai often lasts more than "
        "one day. The trained models are *worse* than the naive baseline "
        "at heavy rain. The models almost never predict more than ~114 mm "
        "(Random Forest predicted maximum) against an observed maximum of "
        "199.9 mm — they compress the extremes towards the middle.")

    # --- Worst misses -----------------------------------------------------------
    st.markdown("### Worst misses — the heavy days the models did not see")
    st.markdown(
        "The 10 largest Random Forest errors in the test period. 8 of 10 "
        "are under-predictions of heavy rain.")
    worst_display = worst.copy()
    worst_display.columns = ["Date (t+1)", "Observed (mm)",
                             "Predicted RF (mm)", "Predicted LR (mm)",
                             "Error RF (mm)", "|Error| (mm)"]
    worst_display["Date (t+1)"] = pd.to_datetime(
        worst_display["Date (t+1)"]).dt.date
    for col in ["Observed (mm)", "Predicted RF (mm)",
                "Predicted LR (mm)", "Error RF (mm)", "|Error| (mm)"]:
        worst_display[col] = worst_display[col].round(1)
    st.dataframe(worst_display, width="stretch", hide_index=True)
    st.caption(
        "Worst single miss: 16 May 2021 — observed 199.9 mm, Random "
        "Forest predicted 32.2 mm (error −167.7 mm). 2 Dec 2021 is the "
        "opposite failure: observed 0.8 mm, predicted 91.5 mm — rain "
        "expected that never arrived.")

    # --- Why it is hard ---------------------------------------------------------
    st.markdown("### Why heavy rain is hard here")
    st.markdown(
        "- **Rare:** 21 heavy days in the 4-year test period (1.4%); "
        "85 heavy days in 18 training years. The models see few examples.\n"
        "- **Noisy target:** daily rainfall is the hardest common "
        "meteorological target; extremes are the noisiest part of it.\n"
        "- **Reanalysis smooths extremes:** the target itself is a "
        "smoothed reconstruction — Open-Meteo caps the 2020 daily maximum "
        "at 169.8 mm where IMD records 203.1 mm. The model inherits that "
        "smoothing, so it under-predicts the peaks it was never shown.\n"
        "- **No NWP inputs:** the models see only the last 8 days of "
        "surface weather. A genuine heavy-rain warning needs numerical "
        "weather-prediction fields this project does not have.")
    st.markdown(
        "**What would be needed to do better:** more heavy-rain examples "
        "(multi-city data, or a longer record), pressure-level features "
        "(e.g. 850 hPa humidity), and evaluation against IMD gauge data "
        "rather than reanalysis. None of that is claimed here — this page "
        "records the current limit, and any future improvement must be "
        "measured the same way before it is claimed.")

    footer()
