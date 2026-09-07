"""Premium multi-sheet Excel report via XlsxWriter."""
from __future__ import annotations

import io

import pandas as pd
import xlsxwriter

BRAND = "#4F46E5"
INK = "#1E293B"
MUTED = "#64748B"
GROUND = "#F8FAFC"
ACCENT = "#0EA5E9"

SHEETS = [
    "Executive Dashboard", "Dataset Profile", "Summary Statistics", "Correlation Matrix",
    "Relationship Analysis", "Outlier Detection", "AI Insights", "Charts", "Raw Data",
]


def _fmts(wb):
    return {
        "title": wb.add_format({"bold": True, "font_size": 20, "font_color": INK, "font_name": "Calibri"}),
        "subtitle": wb.add_format({"font_size": 11, "font_color": MUTED}),
        "h": wb.add_format({"bold": True, "font_size": 12, "font_color": "white", "bg_color": BRAND,
                            "align": "left", "valign": "vcenter", "border": 1, "border_color": BRAND}),
        "kpi_label": wb.add_format({"font_size": 9, "font_color": MUTED, "bg_color": GROUND, "border": 1,
                                    "border_color": "#E2E8F0", "align": "center"}),
        "kpi_value": wb.add_format({"bold": True, "font_size": 18, "font_color": BRAND, "bg_color": GROUND,
                                    "border": 1, "border_color": "#E2E8F0", "align": "center"}),
        "cell": wb.add_format({"font_size": 10, "border": 1, "border_color": "#E2E8F0"}),
        "num": wb.add_format({"font_size": 10, "num_format": "#,##0.000", "border": 1, "border_color": "#E2E8F0"}),
        "pct": wb.add_format({"font_size": 10, "num_format": "0.00%", "border": 1, "border_color": "#E2E8F0"}),
        "sev_crit": wb.add_format({"bold": True, "font_color": "#B91C1C", "font_size": 10}),
        "sev_warn": wb.add_format({"bold": True, "font_color": "#B45309", "font_size": 10}),
        "sev_info": wb.add_format({"font_color": MUTED, "font_size": 10}),
        "wrap": wb.add_format({"font_size": 10, "text_wrap": True, "valign": "top",
                               "border": 1, "border_color": "#E2E8F0"}),
    }


def build_report(df: pd.DataFrame, ctx: dict, raw_rows_cap: int = 5000) -> tuple[bytes, list[str]]:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "nan_inf_to_errors": True})
    f = _fmts(wb)

    _exec_dashboard(wb, f, ctx)
    _profile_sheet(wb, f, ctx)
    _summary_sheet(wb, f, ctx)
    _corr_sheet(wb, f, ctx)
    _rel_sheet(wb, f, ctx)
    _outlier_sheet(wb, f, ctx)
    _insights_sheet(wb, f, ctx)
    _charts_sheet(wb, f, df, ctx)
    _raw_sheet(wb, f, df, raw_rows_cap)

    wb.close()
    return buf.getvalue(), SHEETS


def _header(ws, f, title, subtitle=""):
    ws.hide_gridlines(2)
    ws.set_column("A:A", 2)
    ws.write("B2", title, f["title"])
    if subtitle:
        ws.write("B3", subtitle, f["subtitle"])


def _exec_dashboard(wb, f, ctx):
    ws = wb.add_worksheet("Executive Dashboard")
    p, ins = ctx["profile"], ctx["insights"]
    _header(ws, f, "Executive Dashboard", ctx["dataset_name"])
    ws.set_column("B:G", 18)

    kpis = [
        ("Rows", f"{p['row_count']:,}"), ("Columns", p["col_count"]),
        ("Cells", f"{p['cell_count']:,}"), ("Missing %", f"{p['missing_cell_pct']}%"),
        ("Numeric cols", p["role_counts"].get("numeric", 0)),
        ("Outlier rows", ctx["mv_outliers"].get("flagged_count", 0)),
    ]
    for i, (label, val) in enumerate(kpis):
        col = 1 + i
        ws.write(4, col, label, f["kpi_label"])
        ws.write(5, col, val, f["kpi_value"])

    ws.write("B8", "Headline", f["h"])
    ws.merge_range("B9:G10", ins["headline"], f["wrap"])

    ws.write("B12", "Top findings", f["h"])
    for i, item in enumerate(ins["findings"][:3]):
        ws.merge_range(13 + i, 1, 13 + i, 6,
                       f"[{item['severity'].upper()}] {item['title']} — {item['evidence']}", f["wrap"])

    # column-type mix chart
    rc = p["role_counts"]
    ws.write_column("J20", list(rc.keys()))
    ws.write_column("K20", list(rc.values()))
    chart = wb.add_chart({"type": "column"})
    chart.add_series({
        "categories": ["Executive Dashboard", 19, 9, 19 + len(rc) - 1, 9],
        "values": ["Executive Dashboard", 19, 10, 19 + len(rc) - 1, 10],
        "fill": {"color": BRAND}, "name": "Columns by role",
    })
    chart.set_title({"name": "Column type mix"})
    chart.set_legend({"none": True})
    ws.insert_chart("B18", chart, {"x_scale": 1.3, "y_scale": 1.1})


def _profile_sheet(wb, f, ctx):
    ws = wb.add_worksheet("Dataset Profile")
    _header(ws, f, "Dataset Profile")
    cols = ["name", "role", "dtype", "non_null", "null_pct", "unique", "sample"]
    widths = [26, 14, 12, 12, 12, 12, 44]
    for i, (c, w) in enumerate(zip(cols, widths)):
        ws.set_column(i, i, w)
        ws.write(4, i, c, f["h"])
    for r, entry in enumerate(ctx["profile"]["columns"], start=5):
        ws.write(r, 0, entry["name"], f["cell"])
        ws.write(r, 1, entry["role"], f["cell"])
        ws.write(r, 2, entry["dtype"], f["cell"])
        ws.write_number(r, 3, entry["non_null"], f["cell"])
        ws.write_number(r, 4, entry["null_pct"] / 100, f["pct"])
        ws.write_number(r, 5, entry["unique"], f["cell"])
        ws.write(r, 6, ", ".join(str(x) for x in entry["sample"]), f["cell"])
    last = 4 + len(ctx["profile"]["columns"])
    ws.autofilter(4, 0, last, len(cols) - 1)
    ws.freeze_panes(5, 1)
    ws.conditional_format(5, 4, last, 4, {"type": "data_bar", "bar_color": ACCENT})


def _summary_sheet(wb, f, ctx):
    ws = wb.add_worksheet("Summary Statistics")
    _header(ws, f, "Summary Statistics", "numeric columns")
    cols = ["column", "count", "mean", "std", "min", "p25", "median", "p75", "max",
            "skew", "kurtosis", "cv", "is_normal"]
    for i, c in enumerate(cols):
        ws.set_column(i, i, 13)
        ws.write(4, i, c, f["h"])
    for r, s in enumerate(ctx["summary"], start=5):
        ws.write(r, 0, s["column"], f["cell"])
        for i, key in enumerate(cols[1:], start=1):
            v = s[key]
            if isinstance(v, bool) or v is None:
                ws.write(r, i, "" if v is None else ("yes" if v else "no"), f["cell"])
            else:
                ws.write_number(r, i, v, f["num"])
    ws.freeze_panes(5, 1)


def _corr_sheet(wb, f, ctx):
    ws = wb.add_worksheet("Correlation Matrix")
    _header(ws, f, "Correlation Matrix", "Pearson r")
    corr = ctx["corr"]
    labels = corr["columns"]
    if not corr["pearson"]:
        ws.write("B5", "Need at least 2 numeric columns.", f["subtitle"])
        return
    ws.set_column(1, 1 + len(labels), 13)
    for j, lab in enumerate(labels):
        ws.write(4, 2 + j, lab, f["h"])
        ws.write(5 + j, 1, lab, f["h"])
    for i, row in enumerate(corr["pearson"]):
        for j, val in enumerate(row):
            ws.write_number(5 + i, 2 + j, val, f["num"])
    n = len(labels)
    ws.conditional_format(5, 2, 4 + n, 1 + n, {
        "type": "3_color_scale", "min_color": "#DC2626", "mid_color": "#FFFFFF",
        "max_color": "#2563EB", "min_value": -1, "mid_value": 0, "max_value": 1,
        "min_type": "num", "mid_type": "num", "max_type": "num",
    })
    ws.write(6 + n, 1, "Top correlated pairs", f["h"])
    for k, pr in enumerate(corr["top_pairs"][:10]):
        ws.write(7 + n + k, 1, f"{pr['a']} ~ {pr['b']}", f["cell"])
        ws.write_number(7 + n + k, 2, pr["r"], f["num"])


def _rel_sheet(wb, f, ctx):
    ws = wb.add_worksheet("Relationship Analysis")
    _header(ws, f, "Relationship Analysis", "ranked cross-type associations")
    cols = ["left", "right", "kind", "method", "strength", "label"]
    widths = [24, 24, 22, 24, 12, 14]
    for i, (c, w) in enumerate(zip(cols, widths)):
        ws.set_column(i, i, w)
        ws.write(4, i, c, f["h"])
    for r, rel in enumerate(ctx["relationships"], start=5):
        ws.write(r, 0, rel["left"], f["cell"])
        ws.write(r, 1, rel["right"], f["cell"])
        ws.write(r, 2, rel["kind"], f["cell"])
        ws.write(r, 3, rel["method"], f["cell"])
        ws.write_number(r, 4, rel["strength"], f["num"])
        ws.write(r, 5, rel["label"], f["cell"])
    if ctx["relationships"]:
        ws.autofilter(4, 0, 4 + len(ctx["relationships"]), len(cols) - 1)
        ws.freeze_panes(5, 0)


def _outlier_sheet(wb, f, ctx):
    ws = wb.add_worksheet("Outlier Detection")
    _header(ws, f, "Outlier Detection", "IQR fences + IsolationForest")
    cols = ["column", "lower_fence", "upper_fence", "outlier_count", "outlier_pct", "example_values"]
    for i, c in enumerate(cols):
        ws.set_column(i, i, 18)
        ws.write(4, i, c, f["h"])
    for r, o in enumerate(ctx["iqr_outliers"], start=5):
        ws.write(r, 0, o["column"], f["cell"])
        ws.write_number(r, 1, o["lower_fence"], f["num"])
        ws.write_number(r, 2, o["upper_fence"], f["num"])
        ws.write_number(r, 3, o["outlier_count"], f["cell"])
        ws.write_number(r, 4, o["outlier_pct"] / 100, f["pct"])
        ws.write(r, 5, ", ".join(str(x) for x in o["example_values"]), f["cell"])
    base = 6 + len(ctx["iqr_outliers"])
    mv = ctx["mv_outliers"]
    ws.write(base, 0, "Multivariate (IsolationForest)", f["h"])
    ws.write(base + 1, 0, "flagged rows", f["cell"])
    ws.write_number(base + 1, 1, mv.get("flagged_count", 0), f["cell"])
    ws.write(base + 2, 0, "row indices", f["cell"])
    ws.write(base + 2, 1, ", ".join(str(i) for i in mv.get("flagged_row_indices", [])[:60]), f["cell"])


def _insights_sheet(wb, f, ctx):
    ws = wb.add_worksheet("AI Insights")
    _header(ws, f, "AI Insights", "deterministic rule-based analysis")
    ins = ctx["insights"]
    ws.set_column("B:B", 14)
    ws.set_column("C:C", 40)
    ws.set_column("D:D", 70)
    ws.merge_range("B5:D5", ins["headline"], f["wrap"])
    ws.write("B7", "severity", f["h"])
    ws.write("C7", "finding", f["h"])
    ws.write("D7", "evidence", f["h"])
    sev_fmt = {"critical": f["sev_crit"], "warning": f["sev_warn"], "info": f["sev_info"]}
    r = 7
    for item in ins["findings"]:
        ws.write(r, 1, item["severity"], sev_fmt[item["severity"]])
        ws.write(r, 2, item["title"], f["wrap"])
        ws.write(r, 3, item["evidence"], f["wrap"])
        r += 1
    r += 2
    ws.write(r, 1, "priority", f["h"])
    ws.write(r, 2, "recommendation", f["h"])
    ws.write(r, 3, "detail", f["h"])
    r += 1
    for rec in ins["recommendations"]:
        ws.write(r, 1, rec["priority"], f["cell"])
        ws.write(r, 2, rec["title"], f["wrap"])
        ws.write(r, 3, rec["detail"], f["wrap"])
        r += 1


def _charts_sheet(wb, f, df, ctx):
    ws = wb.add_worksheet("Charts")
    _header(ws, f, "Charts")
    data_ws = wb.add_worksheet("_chartdata")
    data_ws.hide()
    numeric = [c["name"] for c in ctx["profile"]["columns"] if c["role"] == "numeric"][:4]
    anchor_row = 4
    col_cursor = 0
    for idx, col in enumerate(numeric):
        d = pd.to_numeric(df[col], errors="coerce").dropna()
        if d.empty:
            continue
        counts, edges = _hist(d, bins=12)
        centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
        data_ws.write_column(0, col_cursor, [f"{col} bin"] + [round(c, 3) for c in centers])
        data_ws.write_column(0, col_cursor + 1, [f"{col} count"] + counts)
        chart = wb.add_chart({"type": "column"})
        chart.add_series({
            "name": f"{col} distribution",
            "categories": ["_chartdata", 1, col_cursor, len(centers), col_cursor],
            "values": ["_chartdata", 1, col_cursor + 1, len(counts), col_cursor + 1],
            "fill": {"color": BRAND if idx % 2 == 0 else ACCENT},
        })
        chart.set_title({"name": f"Histogram — {col}"})
        chart.set_legend({"none": True})
        ws.insert_chart(anchor_row + (idx // 2) * 16, 1 + (idx % 2) * 9, chart,
                        {"x_scale": 1.15, "y_scale": 1.1})
        col_cursor += 2

    # scatter of top correlated pair
    pairs = ctx["corr"].get("top_pairs", [])
    if pairs:
        a, b = pairs[0]["a"], pairs[0]["b"]
        sub = df[[a, b]].apply(pd.to_numeric, errors="coerce").dropna().head(500)
        data_ws.write_column(0, col_cursor, [a] + sub[a].tolist())
        data_ws.write_column(0, col_cursor + 1, [b] + sub[b].tolist())
        sc = wb.add_chart({"type": "scatter"})
        sc.add_series({
            "name": f"{a} vs {b} (r={pairs[0]['r']:.2f})",
            "categories": ["_chartdata", 1, col_cursor, len(sub), col_cursor],
            "values": ["_chartdata", 1, col_cursor + 1, len(sub), col_cursor + 1],
            "marker": {"type": "circle", "size": 5, "fill": {"color": BRAND}},
        })
        sc.set_title({"name": f"Scatter — {a} vs {b}"})
        sc.set_x_axis({"name": a})
        sc.set_y_axis({"name": b})
        ws.insert_chart(anchor_row + ((len(numeric) + 1) // 2) * 16, 1, sc,
                        {"x_scale": 1.3, "y_scale": 1.2})


def _raw_sheet(wb, f, df, cap):
    ws = wb.add_worksheet("Raw Data")
    sub = df.head(cap)
    for j, col in enumerate(sub.columns):
        ws.write(0, j, str(col), f["h"])
        ws.set_column(j, j, 16)
    for i, (_, row) in enumerate(sub.iterrows(), start=1):
        for j, val in enumerate(row):
            if pd.isna(val):
                ws.write_blank(i, j, None, f["cell"])
            elif isinstance(val, (int, float)):
                ws.write_number(i, j, val, f["cell"])
            else:
                ws.write(i, j, str(val), f["cell"])
    ws.autofilter(0, 0, len(sub), max(len(sub.columns) - 1, 0))
    ws.freeze_panes(1, 0)


def _hist(series, bins=12):
    import numpy as np

    counts, edges = np.histogram(series.to_numpy(), bins=bins)
    return counts.tolist(), edges.tolist()
