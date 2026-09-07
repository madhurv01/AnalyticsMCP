from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def iqr_outliers(df: pd.DataFrame, numeric_cols: list[str]) -> list[dict]:
    rows = []
    for col in numeric_cols:
        d = df[col].dropna().astype(float)
        if len(d) < 8:
            continue
        q1, q3 = d.quantile(0.25), d.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (d < lo) | (d > hi)
        rows.append(
            {
                "column": col,
                "lower_fence": float(lo),
                "upper_fence": float(hi),
                "outlier_count": int(mask.sum()),
                "outlier_pct": round(100 * mask.mean(), 2),
                "example_values": [float(x) for x in d[mask].head(5)],
            }
        )
    return rows


def multivariate_outliers(df: pd.DataFrame, numeric_cols: list[str], contamination: float = 0.02) -> dict:
    usable = [c for c in numeric_cols if df[c].notna().sum() > 20]
    if len(usable) < 2:
        return {"columns": usable, "flagged_row_indices": [], "flagged_count": 0}
    sub = df[usable].apply(pd.to_numeric, errors="coerce")
    sub = sub.fillna(sub.median())
    model = IsolationForest(contamination=contamination, random_state=0, n_estimators=200)
    pred = model.fit_predict(sub.values)
    idx = np.where(pred == -1)[0]
    return {
        "columns": usable,
        "flagged_row_indices": [int(i) for i in idx[:200]],
        "flagged_count": int(len(idx)),
        "contamination": contamination,
    }
