"""Feature 1 — Data Quality Scorecard.

Turns the profile into a single 0-100 score with a letter grade and explainable
sub-scores, so a non-analyst can judge "can I trust this file?" at a glance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WEIGHTS = {
    "completeness": 0.28,
    "duplication": 0.14,
    "validity": 0.22,
    "consistency": 0.14,
    "outliers": 0.10,
    "type_confidence": 0.12,
}

LABELS = {
    "completeness": "Completeness",
    "duplication": "Uniqueness",
    "validity": "Validity",
    "consistency": "Consistency",
    "outliers": "Outlier cleanliness",
    "type_confidence": "Type confidence",
}


def _grade(score: float) -> str:
    return ("A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70
            else "D" if score >= 60 else "E" if score >= 50 else "F")


def _clip(x: float) -> float:
    return float(max(0.0, min(100.0, x)))


def _validity(raw: pd.DataFrame, roles: dict[str, str]) -> tuple[float, list[dict]]:
    ratios, offenders = [], []
    for col, role in roles.items():
        if col not in raw.columns:
            continue
        non_null = raw[col].notna().sum()
        if non_null == 0:
            continue
        if role == "numeric":
            ok = pd.to_numeric(raw[col], errors="coerce").notna().sum()
        elif role == "datetime":
            ok = pd.to_datetime(raw[col], errors="coerce", format="mixed").notna().sum()
        else:
            continue
        ratio = ok / non_null
        ratios.append(ratio)
        if ratio < 0.98:
            offenders.append({"column": col, "role": role,
                              "unparseable_pct": round(100 * (1 - ratio), 2)})
    score = 100.0 if not ratios else 100 * float(np.mean(ratios))
    offenders.sort(key=lambda o: o["unparseable_pct"], reverse=True)
    return score, offenders[:5]


def _consistency(raw: pd.DataFrame, roles: dict[str, str]) -> tuple[float, list[dict]]:
    ratios, offenders = [], []
    for col, role in roles.items():
        if role not in ("categorical", "text") or col not in raw.columns:
            continue
        s = raw[col].dropna().astype(str)
        if s.empty:
            continue
        raw_u = s.nunique()
        norm_u = s.str.strip().str.lower().nunique()
        if raw_u == 0:
            continue
        ratio = norm_u / raw_u
        ratios.append(ratio)
        if ratio < 0.95:
            offenders.append({"column": col, "raw_values": int(raw_u),
                              "after_normalisation": int(norm_u)})
    score = 100.0 if not ratios else 100 * float(np.mean(ratios))
    offenders.sort(key=lambda o: o["raw_values"] - o["after_normalisation"], reverse=True)
    return score, offenders[:5]


def _type_confidence(raw: pd.DataFrame, roles: dict[str, str]) -> tuple[float, list[dict]]:
    scores, weak = [], []
    n = max(len(raw), 1)
    for col, role in roles.items():
        if col not in raw.columns:
            continue
        s = raw[col].dropna().astype(str).str.strip()
        if s.empty:
            scores.append(0.4)
            continue
        if role == "numeric":
            c = pd.to_numeric(s, errors="coerce").notna().mean()
        elif role == "datetime":
            c = pd.to_datetime(s, errors="coerce", format="mixed").notna().mean()
        elif role == "boolean":
            c = 1.0
        elif role == "id":
            c = s.nunique() / len(s)
        elif role == "categorical":
            c = 1 - min(1.0, s.nunique() / (0.5 * n))
        else:  # text
            c = 0.7
        c = float(max(0.0, min(1.0, c)))
        scores.append(c)
        if c < 0.85:
            weak.append({"column": col, "inferred_role": role, "confidence": round(c, 2)})
    score = 100.0 if not scores else 100 * float(np.mean(scores))
    weak.sort(key=lambda w: w["confidence"])
    return score, weak[:5]


def score(raw: pd.DataFrame, roles: dict[str, str], profile: dict,
          iqr_outliers: list[dict]) -> dict:
    n = max(profile["row_count"], 1)

    completeness = _clip(100 - profile["missing_cell_pct"])
    duplication = _clip(100 * (1 - profile["duplicate_rows"] / n))

    validity, bad_values = _validity(raw, roles)
    consistency, inconsistent = _consistency(raw, roles)
    type_conf, weak_types = _type_confidence(raw, roles)

    if iqr_outliers:
        mean_outlier_pct = float(np.mean([o["outlier_pct"] for o in iqr_outliers]))
        outlier_score = _clip(100 - mean_outlier_pct * 3)
    else:
        mean_outlier_pct, outlier_score = 0.0, 100.0

    subscores = {
        "completeness": _clip(completeness),
        "duplication": _clip(duplication),
        "validity": _clip(validity),
        "consistency": _clip(consistency),
        "outliers": _clip(outlier_score),
        "type_confidence": _clip(type_conf),
    }
    overall = sum(subscores[k] * w for k, w in WEIGHTS.items())

    drags = sorted(subscores.items(), key=lambda kv: kv[1])[:3]
    issues: list[dict] = []
    for key, val in drags:
        if val >= 90:
            continue
        detail = {
            "completeness": f"{profile['missing_cell_pct']}% of cells are empty "
                            f"({profile['rows_with_missing']}/{profile['row_count']} rows affected).",
            "duplication": f"{profile['duplicate_rows']} exact duplicate rows.",
            "validity": (f"{bad_values[0]['column']}: {bad_values[0]['unparseable_pct']}% "
                         f"of values don't parse as {bad_values[0]['role']}."
                         if bad_values else "Some typed columns contain unparseable values."),
            "consistency": (f"{inconsistent[0]['column']}: {inconsistent[0]['raw_values']} raw values "
                            f"collapse to {inconsistent[0]['after_normalisation']} after trimming/casing."
                            if inconsistent else "Categorical columns have case/whitespace variants."),
            "outliers": f"Numeric columns average {mean_outlier_pct:.1f}% IQR outliers.",
            "type_confidence": (f"{weak_types[0]['column']} inferred as {weak_types[0]['inferred_role']} "
                                f"with only {weak_types[0]['confidence']} confidence."
                                if weak_types else "Some column types were inferred with low confidence."),
        }[key]
        issues.append({"dimension": LABELS[key], "score": round(val, 1), "detail": detail})

    return {
        "overall": round(_clip(overall), 1),
        "grade": _grade(overall),
        "subscores": [
            {"key": k, "label": LABELS[k], "score": round(v, 1), "weight": WEIGHTS[k]}
            for k, v in subscores.items()
        ],
        "issues": issues,
        "details": {
            "unparseable_values": bad_values,
            "inconsistent_categories": inconsistent,
            "low_confidence_types": weak_types,
        },
    }
