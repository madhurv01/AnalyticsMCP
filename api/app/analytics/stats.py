from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def numeric_summary(df: pd.DataFrame, numeric_cols: list[str]) -> list[dict]:
    rows = []
    for col in numeric_cols:
        d = df[col].dropna().astype(float)
        if len(d) < 3:
            continue
        skew = float(stats.skew(d, bias=False))
        kurt = float(stats.kurtosis(d, bias=False))
        # Shapiro on a capped sample
        sample = d.sample(min(len(d), 5000), random_state=0)
        try:
            _, p_normal = stats.shapiro(sample)
        except Exception:
            p_normal = np.nan
        mean = float(d.mean())
        rows.append(
            {
                "column": col,
                "count": int(d.count()),
                "mean": mean,
                "std": float(d.std(ddof=1)),
                "min": float(d.min()),
                "p25": float(d.quantile(0.25)),
                "median": float(d.median()),
                "p75": float(d.quantile(0.75)),
                "max": float(d.max()),
                "skew": skew,
                "kurtosis": kurt,
                "cv": float(d.std(ddof=1) / mean) if mean else None,
                "is_normal": bool(p_normal > 0.05) if not np.isnan(p_normal) else None,
            }
        )
    return rows


def correlation_matrix(df: pd.DataFrame, numeric_cols: list[str]) -> dict:
    if len(numeric_cols) < 2:
        return {"columns": numeric_cols, "pearson": [], "top_pairs": []}
    sub = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    pearson = sub.corr(method="pearson")
    pairs = []
    for i, a in enumerate(numeric_cols):
        for b in numeric_cols[i + 1 :]:
            r = pearson.loc[a, b]
            if pd.notna(r):
                pairs.append({"a": a, "b": b, "r": float(r), "abs_r": abs(float(r))})
    pairs.sort(key=lambda p: p["abs_r"], reverse=True)
    return {
        "columns": numeric_cols,
        "pearson": pearson.round(4).fillna(0).values.tolist(),
        "top_pairs": pairs[:15],
    }
