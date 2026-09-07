"""Deterministic, rule-based insight & recommendation generation.

No LLM. Every finding is derived from computed statistics and carries its evidence.
"""
from __future__ import annotations


def _sev(x: str) -> int:
    return {"critical": 3, "warning": 2, "info": 1}[x]


def generate(profile: dict, summary: list[dict], corr: dict, rels: list[dict],
             iqr: list[dict], mv: dict) -> dict:
    findings: list[dict] = []
    recs: list[dict] = []
    n = profile["row_count"]

    # --- data quality ---
    if profile["missing_cell_pct"] > 0:
        sev = "critical" if profile["missing_cell_pct"] > 20 else (
            "warning" if profile["missing_cell_pct"] > 5 else "info")
        findings.append({
            "category": "data_quality", "severity": sev,
            "title": f"{profile['missing_cell_pct']}% of cells are missing",
            "evidence": f"{profile['rows_with_missing']} of {n} rows have at least one missing value.",
        })
    worst = sorted(profile["columns"], key=lambda c: c["null_pct"], reverse=True)[:3]
    for c in worst:
        if c["null_pct"] >= 30:
            recs.append({
                "title": f"Address missingness in '{c['name']}'",
                "detail": f"{c['null_pct']}% missing — consider imputation, a 'missing' category, or dropping the column.",
                "priority": "high" if c["null_pct"] >= 60 else "medium",
            })

    if profile["duplicate_rows"] > 0:
        findings.append({
            "category": "data_quality",
            "severity": "warning" if profile["duplicate_rows"] / max(n, 1) > 0.01 else "info",
            "title": f"{profile['duplicate_rows']} duplicate rows detected",
            "evidence": "Exact full-row duplicates.",
        })
        recs.append({"title": "De-duplicate the dataset",
                     "detail": "Drop or investigate exact duplicate rows before modelling.",
                     "priority": "medium"})

    # --- distribution shape ---
    for s in summary:
        if s["skew"] is not None and abs(s["skew"]) >= 1.0:
            findings.append({
                "category": "distribution", "severity": "info",
                "title": f"'{s['column']}' is {'right' if s['skew'] > 0 else 'left'}-skewed",
                "evidence": f"skew={s['skew']:.2f}, mean={s['mean']:.3g}, median={s['median']:.3g}.",
            })
            recs.append({"title": f"Consider transforming '{s['column']}'",
                         "detail": "A log or Box-Cox transform may stabilise variance for downstream models.",
                         "priority": "low"})
        if s["cv"] is not None and s["cv"] > 1.5:
            findings.append({
                "category": "distribution", "severity": "info",
                "title": f"'{s['column']}' has very high relative variability",
                "evidence": f"coefficient of variation = {s['cv']:.2f}.",
            })

    # --- relationships ---
    for r in rels:
        if abs(r["strength"]) >= 0.6 and r["label"] in ("strong", "moderate"):
            findings.append({
                "category": "relationship", "severity": "info",
                "title": f"{r['label'].capitalize()} association: '{r['left']}' ↔ '{r['right']}'",
                "evidence": f"{r['method']} = {r['strength']} ({r['kind']}).",
            })
    strong_numeric = [p for p in corr.get("top_pairs", []) if p["abs_r"] >= 0.85]
    for p in strong_numeric:
        recs.append({
            "title": f"Possible redundancy: '{p['a']}' and '{p['b']}'",
            "detail": f"Pearson r = {p['r']:.2f}. Consider dropping one to reduce multicollinearity.",
            "priority": "medium",
        })

    # --- anomalies ---
    heavy = [o for o in iqr if o["outlier_pct"] >= 5]
    for o in heavy:
        findings.append({
            "category": "anomaly", "severity": "warning",
            "title": f"'{o['column']}' has {o['outlier_pct']}% IQR outliers",
            "evidence": f"{o['outlier_count']} values outside [{o['lower_fence']:.3g}, {o['upper_fence']:.3g}].",
        })
    if mv.get("flagged_count", 0) > 0:
        findings.append({
            "category": "anomaly", "severity": "info",
            "title": f"IsolationForest flagged {mv['flagged_count']} multivariate outlier rows",
            "evidence": f"Across columns {', '.join(mv['columns'][:6])}"
                        + ("…" if len(mv["columns"]) > 6 else "") + ".",
        })
        recs.append({"title": "Review flagged anomalous rows",
                     "detail": "Inspect the IsolationForest-flagged rows for data-entry errors or genuine rare events.",
                     "priority": "medium"})

    if not findings:
        findings.append({"category": "data_quality", "severity": "info",
                         "title": "No material data-quality issues detected",
                         "evidence": "Missingness, duplicates, skew and outliers are all within normal ranges."})

    findings.sort(key=lambda f: _sev(f["severity"]), reverse=True)
    order = {"high": 3, "medium": 2, "low": 1}
    recs.sort(key=lambda r: order[r["priority"]], reverse=True)

    headline = _headline(profile, findings)
    return {
        "headline": headline,
        "findings": findings,
        "recommendations": recs,
        "counts": {
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "warning": sum(1 for f in findings if f["severity"] == "warning"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
    }


def _headline(profile: dict, findings: list[dict]) -> str:
    crit = sum(1 for f in findings if f["severity"] == "critical")
    warn = sum(1 for f in findings if f["severity"] == "warning")
    base = (f"{profile['row_count']:,} rows × {profile['col_count']} columns "
            f"({profile['missing_cell_pct']}% missing).")
    if crit:
        return base + f" {crit} critical data-quality issue(s) need attention before analysis."
    if warn:
        return base + f" {warn} data-quality warning(s) to review."
    return base + " Dataset looks healthy and ready for analysis."
