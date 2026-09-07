"""Smoke test for the analytics engine — no DB / storage / network needed.

    cd api && pip install . && python -m pytest tests/ -q
"""
import io

import numpy as np
import pandas as pd

from app.analytics.engine import run_workflow


def _sample_csv() -> bytes:
    rng = np.random.default_rng(42)
    n = 500
    df = pd.DataFrame(
        {
            "order_id": range(1, n + 1),
            "region": rng.choice(["North", "South", "East", "West"], n),
            "channel": rng.choice(["online", "retail"], n),
            "order_date": pd.date_range("2024-01-01", periods=n, freq="6h").astype(str),
            "units": rng.poisson(4, n),
            "revenue": rng.gamma(2.0, 50, n).round(2),
            "discount_pct": rng.beta(2, 8, n).round(3),
        }
    )
    df.loc[rng.choice(n, 25, replace=False), "revenue"] = np.nan
    df.loc[rng.choice(n, 5, replace=False), "revenue"] = 99999  # injected outliers
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def test_run_workflow_end_to_end():
    steps_seen = []
    result = run_workflow(_sample_csv(), "orders.csv", lambda s, p: steps_seen.append(s))

    assert len(steps_seen) == 12
    assert result["row_count"] == 500
    assert result["profile"]["role_counts"].get("numeric", 0) >= 3

    roles = {c["name"]: c["role"] for c in result["profile"]["columns"]}
    assert roles["region"] == "categorical"
    assert roles["order_date"] == "datetime"
    assert roles["revenue"] == "numeric"

    assert result["insights"]["findings"]
    assert any("outlier" in f["title"].lower() for f in result["insights"]["findings"])

    assert result["xlsx_bytes"][:2] == b"PK"  # valid xlsx (zip) header
    assert len(result["sheet_names"]) == 9
