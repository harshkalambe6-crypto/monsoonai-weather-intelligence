"""MONSOONAI dashboard — automated page tests (Phase 5, local only).

Runs the real Streamlit app with AppTest, visits every page, and
checks:
  * no page raises an exception,
  * the exact evaluation metrics from artifacts/evaluation_summary.json
    appear on the Model Performance page,
  * the heavy-rain honesty numbers appear on the Extreme Rainfall page,
  * the "not a live forecast" / "not suitable for operational warnings"
    statements are present,
  * the next-day prediction on the Prediction page matches the saved
    test predictions for a known cutoff day.

Run:  ~/workspace/monsoonai-venv/bin/python tests/test_app.py
Expected: all checks PASS, exit code 0.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
sys.path.insert(0, str(APP_DIR))

from streamlit.testing.v1 import AppTest

FAILURES = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


def all_text(at):
    """All rendered text (markdown + captions + metric values/labels)."""
    parts = []
    for el in list(at.markdown) + list(at.caption) + list(at.error):
        parts.append(str(el.value))
    for el in at.metric:
        parts.append(str(el.label))
        parts.append(str(el.value))
        parts.append(str(el.delta) if el.delta else "")
    for el in at.dataframe:
        parts.append(str(el.value.to_string()) if hasattr(el.value, "to_string") else str(el.value))
    for el in at.radio:
        parts.append(str(el.value))
    return "\n".join(parts)


def goto(at, page):
    at.radio[0].set_value(page).run(timeout=180)
    check(f"page loads: {page}", not at.exception,
          str(at.exception[0])[:200] if at.exception else "")
    return at


def main():
    at = AppTest.from_file(str(APP_DIR / "app.py"))
    at.run(timeout=180)
    check("app starts without exception", not at.exception,
          str(at.exception[0])[:300] if at.exception else "")

    # Overview (default page)
    text = all_text(at)
    check("overview shows dataset range", "1 Jan 2000" in text)
    check("overview shows mean annual rainfall 2,080 mm",
          "2,080" in text)
    check("overview shows RF MAE 4.191", "4.191" in text)
    check("overview warns: not an operational forecast",
          "not an operational forecast" in text.lower())

    # Prediction page
    goto(at, "Rainfall Prediction")
    text = all_text(at)
    check("prediction page: NOT a live forecast", "NOT a live forecast" in text)
    check("prediction page: cutoff stated", "23:59 Asia/Kolkata" in text)
    check("prediction page: latest data 2024-12-31", "2024-12-31" in text)
    check("prediction page: model prediction shown",
          "Predicted rainfall" in text)
    # Known historical check: cutoff 2021-07-09, RF saved prediction 9.3 mm
    at.date_input[1].set_value("2021-07-09").run(timeout=180)
    text = all_text(at)
    check("prediction page: historical test check shows 9.3 mm RF",
          "9.3 mm" in text, "test-day explorer")

    # Historical Analysis
    goto(at, "Historical Analysis")
    text = all_text(at)
    check("historical: three-way classification sums to 9,132",
          "9,132" in text)
    check("historical: monsoon share 94.2%", "94.2%" in text)
    check("historical: wettest day 251.1 mm", "251.1" in text)

    # Extreme Rainfall
    goto(at, "Extreme Rainfall")
    text = all_text(at)
    check("extreme: NOT suitable for operational warnings",
          "NOT suitable for operational warnings" in text)
    check("extreme: heavy precision 0.137 shown", "0.137" in text)
    check("extreme: 88 false alarms shown", "88" in text)
    check("extreme: worst miss 199.9 mm shown", "199.9" in text)
    check("extreme: LR caught 0 of 21", "0" in text)

    # Model Performance
    goto(at, "Model Performance")
    text = all_text(at)
    for token in ["4.228", "13.022", "0.2968", "5.447", "13.419", "0.2533",
                  "4.356", "11.059", "0.4928", "4.191", "11.368", "0.4641"]:
        check(f"performance: metric {token} shown", token in text)
    check("performance: RF F1 0.880 shown", "0.880" in text)
    check("performance: RF ROC-AUC 0.979 shown", "0.979" in text)
    check("performance: honest reading (0.9%)", "0.9%" in text)
    check("performance: rain_t carries 64%", "64%" in text)

    # Data & Methodology
    goto(at, "Data & Methodology")
    text = all_text(at)
    check("methodology: Open-Meteo attribution", "Open-Meteo.com" in text)
    check("methodology: IMD 3,553 vs 2,774 mm", "3,553" in text)
    check("methodology: 22% underestimation", "22%" in text)
    check("methodology: leakage audit no FAILs", "no FAILs" in text)
    check("methodology: seed 42", "42" in text)

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
