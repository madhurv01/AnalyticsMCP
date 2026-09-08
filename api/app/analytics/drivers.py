"""Feature 2 — Driver Analysis.

Auto-selects the most "interesting" target column(s), then explains what moves
them: shallow decision-tree feature importances, human-readable split rules, and
categorical segment lift. This is the "which segments drive churn / revenue?"
answer an analyst would produce by hand.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor, _tree

SAMPLE_CAP = 25_000
TARGET_HINTS = (
    "revenue", "sales", "amount", "price", "churn", "target", "score", "profit",
    "margin", "conversion", "rating", "nps", "cost", "value", "spend", "ltv", "arr",
    "retention", "engagement", "usage",
)


def _pick_targets(df: pd.DataFrame, roles: dict[str, str]) -> list[tuple[str, str]]:
    scored: list[tuple[str, str, float]] = []
    for col, role in roles.items():
        hint = 2.0 if any(h in col.lower() for h in TARGET_HINTS) else 0.0
        if role == "numeric":
            d = df[col].dropna().astype(float)
            if d.nunique() < 5 or d.std(ddof=0) == 0:
                continue
            cv = d.std(ddof=0) / (abs(d.mean()) + 1e-9)
            scored.append((col, "numeric", hint + min(cv, 3.0)))
        elif role == "boolean" or (role == "categorical" and 2 <= df[col].nunique(dropna=True) <= 6):
            scored.append((col, "categorical", hint + 0.6))
    scored.sort(key=lambda x: x[2], reverse=True)
    return [(c, k) for c, k, _ in scored[:2]]


def _build_features(df: pd.DataFrame, roles: dict[str, str], target: str) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for col, role in roles.items():
        if col == target:
            continue
        if role == "numeric":
            parts.append(pd.to_numeric(df[col], errors="coerce").rename(col).to_frame())
        elif role in ("categorical", "boolean"):
            s = df[col].astype("string")
            top = s.value_counts().nlargest(8).index
            s = s.where(s.isin(top), other="(other)").fillna("(missing)")
            parts.append(pd.get_dummies(s, prefix=col))
        elif role == "datetime":
            dt = pd.to_datetime(df[col], errors="coerce", format="mixed")
            parts.append(pd.DataFrame({f"{col} (as timestamp)": dt.astype("int64")}))
    if not parts:
        return pd.DataFrame(index=df.index)
    X = pd.concat(parts, axis=1)
    return X.replace([np.inf, -np.inf], np.nan).fillna(X.median(numeric_only=True)).fillna(0.0)


def _extract_rules(model, features: list[str], is_classifier: bool,
                   class_names: list[str] | None, max_rules: int = 3) -> list[dict]:
    t = model.tree_
    rules: list[dict] = []

    def recurse(node: int, conds: list[str]) -> None:
        if t.feature[node] != _tree.TREE_UNDEFINED:
            name = features[t.feature[node]]
            thr = t.threshold[node]
            recurse(t.children_left[node], conds + [f"{name} ≤ {thr:.2f}"])
            recurse(t.children_right[node], conds + [f"{name} > {thr:.2f}"])
            return
        support = int(t.n_node_samples[node])
        val = t.value[node][0]
        if is_classifier:
            idx = int(np.argmax(val))
            conf = float(val[idx] / val.sum()) if val.sum() else 0.0
            rules.append({
                "condition": " AND ".join(conds) or "(all rows)",
                "outcome": (class_names[idx] if class_names else str(idx)),
                "confidence": round(conf, 3), "support": support,
            })
        else:
            rules.append({
                "condition": " AND ".join(conds) or "(all rows)",
                "mean": round(float(val[0]), 3), "support": support,
            })

    recurse(0, [])
    if is_classifier:
        rules.sort(key=lambda r: (r["confidence"], r["support"]), reverse=True)
    else:
        gm = float(np.mean([r["mean"] for r in rules])) if rules else 0.0
        rules.sort(key=lambda r: abs(r["mean"] - gm) * np.log1p(r["support"]), reverse=True)
    return rules[:max_rules]


def _segments(df: pd.DataFrame, roles: dict[str, str], target: str,
              kind: str) -> list[dict]:
    out: list[dict] = []
    min_n = max(20, int(0.01 * len(df)))
    if kind == "numeric":
        y = pd.to_numeric(df[target], errors="coerce")
        overall = float(y.mean())
        for col, role in roles.items():
            if role not in ("categorical", "boolean") or col == target:
                continue
            g = df.assign(_y=y).groupby(col)["_y"].agg(["mean", "count"])
            for val, row in g[g["count"] >= min_n].iterrows():
                out.append({
                    "column": col, "value": str(val),
                    "metric": round(float(row["mean"]), 3),
                    "lift_pct": round(100 * (row["mean"] - overall) / overall, 1) if overall else None,
                    "n": int(row["count"]),
                })
    else:
        pos = df[target].astype("string").fillna("(missing)")
        base_rate = float((pos == pos.mode(dropna=True).iloc[0]).mean()) if not pos.empty else 0.0
        top_class = pos.mode(dropna=True).iloc[0] if not pos.empty else None
        overall = float((pos == top_class).mean()) if top_class is not None else 0.0
        for col, role in roles.items():
            if role not in ("categorical", "boolean") or col == target:
                continue
            g = df.assign(_hit=(pos == top_class)).groupby(col)["_hit"].agg(["mean", "count"])
            for val, row in g[g["count"] >= min_n].iterrows():
                out.append({
                    "column": col, "value": str(val),
                    "metric": round(float(row["mean"]), 3),
                    "lift_pct": round(100 * (row["mean"] - overall) / overall, 1) if overall else None,
                    "n": int(row["count"]),
                })
        _ = base_rate
    out.sort(key=lambda s: abs(s["lift_pct"] or 0), reverse=True)
    return out[:10]


def analyze(df: pd.DataFrame, roles: dict[str, str]) -> dict:
    work = df.sample(SAMPLE_CAP, random_state=0) if len(df) > SAMPLE_CAP else df
    targets = _pick_targets(work, roles)
    if not targets:
        return {"targets": [], "note": "No suitable target: need a numeric column with "
                "variance or a low-cardinality category."}

    results: list[dict] = []
    for target, kind in targets:
        X = _build_features(work, roles, target)
        if X.shape[1] == 0:
            continue
        features = list(X.columns)

        try:
            if kind == "numeric":
                y = pd.to_numeric(work[target], errors="coerce")
                mask = y.notna()
                if mask.sum() < 30:
                    continue
                model = DecisionTreeRegressor(
                    max_depth=3, min_samples_leaf=max(20, int(mask.sum() / 50)), random_state=0)
                model.fit(X[mask.values], y[mask])
                fit_metric = {"name": "R²", "value": round(float(model.score(X[mask.values], y[mask])), 3)}
                class_names = None
                is_clf = False
            else:
                y_raw = work[target].astype("string").fillna("(missing)")
                keep = y_raw.value_counts().nlargest(6).index
                mask = y_raw.isin(keep)
                if mask.sum() < 30 or y_raw[mask].nunique() < 2:
                    continue
                codes, uniques = pd.factorize(y_raw[mask])
                class_names = [str(u) for u in uniques]
                model = DecisionTreeClassifier(
                    max_depth=3, min_samples_leaf=max(20, int(mask.sum() / 50)), random_state=0)
                model.fit(X[mask.values], codes)
                fit_metric = {"name": "accuracy", "value": round(float(model.score(X[mask.values], codes)), 3)}
                is_clf = True
        except Exception:  # noqa: BLE001 — skip a target that won't model, keep the rest
            continue

        imp = sorted(zip(features, model.feature_importances_), key=lambda t: t[1], reverse=True)
        drivers = [{"feature": f, "importance": round(float(v), 4)} for f, v in imp if v > 0][:6]

        results.append({
            "target": target,
            "target_kind": kind,
            "fit_metric": fit_metric,
            "drivers": drivers,
            "rules": _extract_rules(model, features, is_clf, class_names),
            "segments": _segments(work, roles, target, kind),
            "sampled_rows": int(mask.sum()),
        })

    return {"targets": results}
