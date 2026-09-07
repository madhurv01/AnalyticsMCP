"""Workflow orchestrator: raw CSV bytes -> profile, insights, Excel report."""
from __future__ import annotations

import io
from collections.abc import Callable

import pandas as pd

from app.analytics import WORKFLOW_STEPS, excel, insights, outliers, profiling, relationships, stats

ProgressCb = Callable[[str, int], None]


def _read_csv(raw: bytes) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc, engine="python", sep=None,
                               on_bad_lines="skip")
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    return pd.read_csv(io.BytesIO(raw), encoding="latin-1", engine="python",
                       on_bad_lines="skip")


def run_workflow(raw: bytes, dataset_name: str, progress_cb: ProgressCb,
                 raw_rows_cap: int = 5000) -> dict:
    steps = {name: int((i + 1) / len(WORKFLOW_STEPS) * 100) for i, name in enumerate(WORKFLOW_STEPS)}

    progress_cb("dataset_loading", steps["dataset_loading"])
    df = _read_csv(raw)
    df.columns = [str(c).strip() for c in df.columns]

    progress_cb("schema_detection", steps["schema_detection"])
    roles = {col: profiling.infer_role(col, df[col]) for col in df.columns}

    progress_cb("data_cleaning", steps["data_cleaning"])
    df = profiling.clean_frame(df, roles)

    progress_cb("type_inference", steps["type_inference"])
    roles = {col: profiling.infer_role(col, df[col]) for col in df.columns}
    numeric_cols = [c for c, r in roles.items() if r == "numeric"]

    progress_cb("missing_value_analysis", steps["missing_value_analysis"])
    profile = profiling.build_profile(df, roles)

    progress_cb("relationship_discovery", steps["relationship_discovery"])
    rels = relationships.discover(df, roles)

    progress_cb("statistical_analysis", steps["statistical_analysis"])
    summary = stats.numeric_summary(df, numeric_cols)
    corr = stats.correlation_matrix(df, numeric_cols)

    progress_cb("anomaly_detection", steps["anomaly_detection"])
    iqr = outliers.iqr_outliers(df, numeric_cols)
    mv = outliers.multivariate_outliers(df, numeric_cols)

    progress_cb("chart_generation", steps["chart_generation"])
    chart_specs = _chart_specs(profile, corr)

    progress_cb("insight_extraction", steps["insight_extraction"])
    ins = insights.generate(profile, summary, corr, rels, iqr, mv)

    ctx = {
        "dataset_name": dataset_name,
        "profile": profile,
        "summary": summary,
        "corr": corr,
        "relationships": rels,
        "iqr_outliers": iqr,
        "mv_outliers": mv,
        "insights": ins,
        "chart_specs": chart_specs,
    }

    progress_cb("excel_report_creation", steps["excel_report_creation"])
    xlsx_bytes, sheet_names = excel.build_report(df, ctx, raw_rows_cap=raw_rows_cap)

    progress_cb("final_export", steps["final_export"])
    return {
        "profile": profile,
        "insights": ins,
        "analysis": {
            "summary": summary,
            "correlation": corr,
            "relationships": rels,
            "iqr_outliers": iqr,
            "mv_outliers": mv,
            "chart_specs": chart_specs,
        },
        "xlsx_bytes": xlsx_bytes,
        "sheet_names": sheet_names,
        "row_count": profile["row_count"],
        "col_count": profile["col_count"],
    }


def _chart_specs(profile: dict, corr: dict) -> list[dict]:
    numeric = [c["name"] for c in profile["columns"] if c["role"] == "numeric"]
    categorical = [c["name"] for c in profile["columns"] if c["role"] == "categorical"]
    specs: list[dict] = []
    for c in numeric[:6]:
        specs.append({"type": "histogram", "column": c})
        specs.append({"type": "box", "column": c})
    for c in categorical[:4]:
        specs.append({"type": "bar", "column": c})
    if corr.get("top_pairs"):
        p = corr["top_pairs"][0]
        specs.append({"type": "scatter", "x": p["a"], "y": p["b"], "r": p["r"]})
    if len(numeric) >= 2:
        specs.append({"type": "heatmap", "columns": numeric})
    return specs
