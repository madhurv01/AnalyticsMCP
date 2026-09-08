"""Feature 3 — Schema Drift Detection.

Fingerprints the (cleaned) schema of every analysed file. When a user re-analyses
a file with the same name, the new run is diffed against the previous one:
added / removed columns, role changes, null-rate spikes, row-count deltas.
Turns a one-off tool into a monitoring tool for recurring datasets.
"""
from __future__ import annotations

NULL_SPIKE_PP = 15.0  # percentage-point jump that counts as a spike


def fingerprint(profile: dict) -> dict:
    return {
        "row_count": profile["row_count"],
        "col_count": profile["col_count"],
        "missing_cell_pct": profile["missing_cell_pct"],
        "columns": {
            c["name"]: {"role": c["role"], "dtype": c["dtype"], "null_pct": c["null_pct"]}
            for c in profile["columns"]
        },
    }


def compare(prev: dict | None, curr: dict) -> dict:
    if not prev or "columns" not in prev:
        return {
            "status": "baseline",
            "severity": "info",
            "summary": "First analysis of a file with this name — baseline saved. "
                       "Re-upload later to see what changed.",
            "added": [], "removed": [], "role_changes": [], "null_spikes": [],
            "row_delta": None, "row_delta_pct": None,
        }

    prev_cols, curr_cols = set(prev["columns"]), set(curr["columns"])
    added = sorted(curr_cols - prev_cols)
    removed = sorted(prev_cols - curr_cols)

    role_changes, null_spikes = [], []
    for col in sorted(prev_cols & curr_cols):
        p, c = prev["columns"][col], curr["columns"][col]
        if p["role"] != c["role"]:
            role_changes.append({"column": col, "from": p["role"], "to": c["role"]})
        jump = c["null_pct"] - p["null_pct"]
        if jump >= NULL_SPIKE_PP:
            null_spikes.append({"column": col, "from": p["null_pct"], "to": c["null_pct"],
                                "jump_pp": round(jump, 1)})

    row_delta = curr["row_count"] - prev["row_count"]
    row_delta_pct = (round(100 * row_delta / prev["row_count"], 1)
                     if prev["row_count"] else None)

    if removed or role_changes:
        severity = "critical"
    elif added or null_spikes or (row_delta_pct is not None and abs(row_delta_pct) >= 40):
        severity = "warning"
    else:
        severity = "info"

    bits = []
    if added:
        bits.append(f"{len(added)} new column(s)")
    if removed:
        bits.append(f"{len(removed)} column(s) removed")
    if role_changes:
        bits.append(f"{len(role_changes)} type change(s)")
    if null_spikes:
        bits.append(f"{len(null_spikes)} null-rate spike(s)")
    if row_delta_pct is not None and abs(row_delta_pct) >= 5:
        bits.append(f"{row_delta_pct:+.0f}% rows")
    summary = ("Schema unchanged since the last run." if not bits
               else "Since the last run: " + ", ".join(bits) + ".")

    return {
        "status": "compared",
        "severity": severity,
        "summary": summary,
        "added": added,
        "removed": removed,
        "role_changes": role_changes,
        "null_spikes": null_spikes,
        "row_delta": row_delta,
        "row_delta_pct": row_delta_pct,
    }
