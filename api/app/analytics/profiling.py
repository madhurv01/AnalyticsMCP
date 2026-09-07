"""Column role inference and dataset profiling."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

ID_NAME_RE = re.compile(r"(^|_)(id|uuid|guid|key|code)s?$", re.I)
BOOL_SETS = [
    {"true", "false"},
    {"yes", "no"},
    {"y", "n"},
    {"t", "f"},
    {"0", "1"},
    {"0.0", "1.0"},
]


def _ratio_parseable(s: pd.Series, parser) -> float:
    non_null = s.dropna().astype(str).str.strip()
    if non_null.empty:
        return 0.0
    ok = parser(non_null)
    return float(ok.notna().mean())


def _num_ok(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _date_ok(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", format="mixed", utc=False)


def infer_role(name: str, s: pd.Series) -> str:
    n = len(s)
    non_null = s.dropna()
    if non_null.empty:
        return "empty"

    nunique = non_null.nunique()
    uniq_ratio = nunique / n if n else 0.0

    lowered = set(non_null.astype(str).str.strip().str.lower().unique())
    if nunique <= 2 and any(lowered <= bs for bs in BOOL_SETS):
        return "boolean"

    if pd.api.types.is_numeric_dtype(s) or _ratio_parseable(s, _num_ok) >= 0.8:
        if ID_NAME_RE.search(name) and uniq_ratio >= 0.98:
            return "id"
        return "numeric"

    if _ratio_parseable(s, _date_ok) >= 0.8:
        return "datetime"

    if ID_NAME_RE.search(name) and uniq_ratio >= 0.98:
        return "id"

    if nunique <= max(20, 0.05 * n):
        return "categorical"

    return "text"


def clean_frame(df: pd.DataFrame, roles: dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    for col, role in roles.items():
        if role in ("categorical", "text", "boolean", "id"):
            out[col] = out[col].astype("string").str.strip()
        if role == "numeric":
            out[col] = pd.to_numeric(out[col], errors="coerce")
        if role == "datetime":
            out[col] = pd.to_datetime(out[col], errors="coerce", format="mixed")
        if role == "boolean":
            out[col] = (
                out[col].astype("string").str.strip().str.lower().map(
                    {"true": True, "yes": True, "y": True, "t": True, "1": True, "1.0": True,
                     "false": False, "no": False, "n": False, "f": False, "0": False, "0.0": False}
                )
            )
    out = out.dropna(how="all")
    return out


def build_profile(df: pd.DataFrame, roles: dict[str, str]) -> dict:
    n = len(df)
    columns = []
    for col in df.columns:
        s = df[col]
        non_null = int(s.notna().sum())
        null_pct = round(100 * (1 - non_null / n), 2) if n else 0.0
        entry = {
            "name": col,
            "role": roles[col],
            "dtype": str(s.dtype),
            "non_null": non_null,
            "null_pct": null_pct,
            "unique": int(s.nunique(dropna=True)),
            "sample": [_json_safe(v) for v in s.dropna().unique()[:5]],
        }
        if roles[col] == "numeric":
            d = s.dropna().astype(float)
            if not d.empty:
                entry["min"], entry["max"] = float(d.min()), float(d.max())
                entry["mean"], entry["std"] = float(d.mean()), float(d.std(ddof=1) if len(d) > 1 else 0.0)
        columns.append(entry)

    rows_any_null = int(df.isna().any(axis=1).sum())
    return {
        "row_count": n,
        "col_count": df.shape[1],
        "cell_count": int(n * df.shape[1]),
        "rows_with_missing": rows_any_null,
        "missing_cell_pct": round(100 * df.isna().sum().sum() / (n * df.shape[1]), 2) if n else 0.0,
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
        "role_counts": {r: sum(1 for v in roles.values() if v == r) for r in set(roles.values())},
        "columns": columns,
    }


def _json_safe(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (pd.Timestamp,)):
        return v.isoformat()
    return str(v)
