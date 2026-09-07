"""Cross-type association discovery."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _cramers_v(a: pd.Series, b: pd.Series) -> float:
    ct = pd.crosstab(a, b)
    if ct.size == 0 or ct.shape[0] < 2 or ct.shape[1] < 2:
        return 0.0
    chi2 = stats.chi2_contingency(ct, correction=False)[0]
    n = ct.to_numpy().sum()
    phi2 = chi2 / n
    r, k = ct.shape
    denom = min(r - 1, k - 1)
    return float(np.sqrt(phi2 / denom)) if denom else 0.0


def _correlation_ratio(categories: pd.Series, values: pd.Series) -> float:
    df = pd.DataFrame({"c": categories, "v": pd.to_numeric(values, errors="coerce")}).dropna()
    if df["c"].nunique() < 2 or len(df) < 3:
        return 0.0
    grand = df["v"].mean()
    ss_between = sum(len(g) * (g["v"].mean() - grand) ** 2 for _, g in df.groupby("c"))
    ss_total = ((df["v"] - grand) ** 2).sum()
    return float(np.sqrt(ss_between / ss_total)) if ss_total else 0.0


def _label(strength: float) -> str:
    a = abs(strength)
    if a >= 0.7:
        return "strong"
    if a >= 0.4:
        return "moderate"
    if a >= 0.2:
        return "weak"
    return "negligible"


def discover(df: pd.DataFrame, roles: dict[str, str]) -> list[dict]:
    numeric = [c for c, r in roles.items() if r == "numeric"]
    categorical = [c for c, r in roles.items() if r in ("categorical", "boolean")]
    found: list[dict] = []

    for i, a in enumerate(numeric):
        for b in numeric[i + 1 :]:
            sub = df[[a, b]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(sub) < 5:
                continue
            pear = sub[a].corr(sub[b])
            spear = sub[a].corr(sub[b], method="spearman")
            if pd.isna(pear):
                continue
            found.append({
                "left": a, "right": b, "kind": "numeric-numeric",
                "method": "pearson/spearman",
                "strength": round(float(pear), 4),
                "secondary": round(float(spear), 4) if pd.notna(spear) else None,
                "label": _label(pear),
            })

    for c in categorical:
        for nvar in numeric:
            eta = _correlation_ratio(df[c], df[nvar])
            if eta > 0:
                found.append({
                    "left": c, "right": nvar, "kind": "categorical-numeric",
                    "method": "correlation ratio (eta)",
                    "strength": round(eta, 4), "secondary": None, "label": _label(eta),
                })

    for i, a in enumerate(categorical):
        for b in categorical[i + 1 :]:
            v = _cramers_v(df[a].astype("string"), df[b].astype("string"))
            if v > 0:
                found.append({
                    "left": a, "right": b, "kind": "categorical-categorical",
                    "method": "cramers_v", "strength": round(v, 4),
                    "secondary": None, "label": _label(v),
                })

    found.sort(key=lambda x: abs(x["strength"]), reverse=True)
    return found[:40]
