"""Feature — `run_query`: a safe, sandboxed pandas expression evaluator.

An agent (or the UI) sends a short expression over `df` (the cleaned frame) and gets
a small result table back. The expression is parsed to an AST and every node is
checked against an allow-list before it runs: no imports, no dunders, no arbitrary
callables, only a curated set of pandas/Series/DataFrame methods.
"""
from __future__ import annotations

import ast

import numpy as np
import pandas as pd

MAX_INPUT_ROWS = 300_000
MAX_RESULT_ROWS = 1_000
MAX_AST_NODES = 180

# methods callable on df / Series / GroupBy / result objects
ALLOWED_METHODS = {
    "groupby", "agg", "aggregate", "mean", "sum", "count", "size", "median", "std",
    "var", "min", "max", "describe", "value_counts", "sort_values", "sort_index",
    "head", "tail", "nlargest", "nsmallest", "reset_index", "set_index", "quantile",
    "corr", "cov", "unique", "nunique", "dropna", "fillna", "round", "abs", "rank",
    "cumsum", "cumcount", "clip", "between", "isin", "astype", "rename", "to_frame",
    "reindex", "first", "last", "idxmax", "idxmin", "mode", "diff", "pct_change",
    "add_prefix", "add_suffix", "sample", "query", "eq", "ne", "lt", "le", "gt", "ge",
    "str", "dt", "cat", "notna", "isna", "any", "all", "drop_duplicates",
}
# attribute accessors that don't call (df.columns, s.str.len etc.)
ALLOWED_ATTRS = ALLOWED_METHODS | {
    "columns", "index", "values", "shape", "dtypes", "T", "loc", "iloc", "empty",
    "year", "month", "day", "hour", "weekday", "dayofweek", "quarter", "date",
    "len", "lower", "upper", "strip", "contains", "startswith", "endswith",
}

_ALLOWED_NODES = (
    ast.Expression, ast.Call, ast.Attribute, ast.Name, ast.Load, ast.Constant,
    ast.Subscript, ast.Slice, ast.Index, ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.keyword, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Invert,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
    ast.Lambda, ast.arguments, ast.arg,  # lambdas allowed only for .agg(...)
)


class QueryError(ValueError):
    pass


def load_frame(raw: bytes) -> pd.DataFrame:
    """Parse + lightly type a dataset's CSV the same way the analysis pipeline does,
    so Query-console results match the dashboard (numeric columns are numeric, dates
    are dates). Shared by the REST endpoint and the MCP tool."""
    from app.analytics import profiling
    from app.analytics.engine import _read_csv

    df = _read_csv(raw)
    df.columns = [str(c).strip() for c in df.columns]
    roles = {c: profiling.infer_role(c, df[c]) for c in df.columns}
    return profiling.clean_frame(df, roles)


def _validate(node: ast.AST) -> None:
    count = 0
    for child in ast.walk(node):
        count += 1
        if count > MAX_AST_NODES:
            raise QueryError("expression is too complex")
        if not isinstance(child, _ALLOWED_NODES):
            raise QueryError(f"disallowed syntax: {type(child).__name__}")
        if isinstance(child, ast.Attribute):
            if child.attr.startswith("_"):
                raise QueryError("dunder / private attribute access is not allowed")
            if child.attr not in ALLOWED_ATTRS:
                raise QueryError(f"attribute '{child.attr}' is not allowed")
        if isinstance(child, ast.Name) and child.id not in {"df", "pd", "np"}:
            raise QueryError(f"unknown name '{child.id}' (only df, pd, np)")
        if isinstance(child, ast.Lambda):
            # only bare-arg lambdas, used inside .agg()/.apply-free chains
            if child.args.vararg or child.args.kwarg or child.args.defaults:
                raise QueryError("only simple lambdas are allowed")


_SAFE_PD = type("pd_ns", (), {
    "NamedAgg": pd.NamedAgg, "cut": pd.cut, "qcut": pd.qcut, "concat": pd.concat,
    "to_numeric": pd.to_numeric, "to_datetime": pd.to_datetime,
})()
_SAFE_NP = type("np_ns", (), {
    "mean": np.mean, "median": np.median, "sum": np.sum, "std": np.std,
    "log": np.log, "log1p": np.log1p, "sqrt": np.sqrt, "abs": np.abs,
})()


def run(df: pd.DataFrame, expr: str) -> dict:
    expr = (expr or "").strip()
    if not expr:
        raise QueryError("empty expression")
    if len(expr) > 2000:
        raise QueryError("expression too long")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise QueryError(f"syntax error: {e.msg}") from e
    _validate(tree)

    work = df.head(MAX_INPUT_ROWS) if len(df) > MAX_INPUT_ROWS else df
    try:
        result = eval(  # noqa: S307 — AST allow-list validated above; builtins stripped
            compile(tree, "<query>", "eval"),
            {"__builtins__": {}},
            {"df": work, "pd": _SAFE_PD, "np": _SAFE_NP},
        )
    except QueryError:
        raise
    except Exception as e:  # noqa: BLE001 — surface pandas errors as a clean message
        raise QueryError(f"{type(e).__name__}: {e}") from e

    return _serialize(result, truncated_input=len(df) > MAX_INPUT_ROWS)


def _serialize(result, truncated_input: bool) -> dict:
    meta = {"input_truncated": truncated_input}
    if isinstance(result, pd.DataFrame):
        total = len(result)
        out = result.head(MAX_RESULT_ROWS)
        return {
            "kind": "table",
            "columns": [str(c) for c in out.columns],
            "rows": _json_rows(out),
            "row_count": total,
            "returned": len(out),
            "result_truncated": total > MAX_RESULT_ROWS,
            **meta,
        }
    if isinstance(result, pd.Series):
        total = len(result)
        out = result.head(MAX_RESULT_ROWS)
        return {
            "kind": "series",
            "name": str(result.name) if result.name is not None else None,
            "index": [_scalar(i) for i in out.index],
            "values": [_scalar(v) for v in out.values],
            "row_count": total,
            "result_truncated": total > MAX_RESULT_ROWS,
            **meta,
        }
    if isinstance(result, pd.Index):
        vals = list(result[:MAX_RESULT_ROWS])
        return {"kind": "list", "values": [_scalar(v) for v in vals],
                "row_count": len(result), **meta}
    return {"kind": "scalar", "value": _scalar(result), **meta}


def _json_rows(df: pd.DataFrame) -> list[dict]:
    return [{str(k): _scalar(v) for k, v in rec.items()}
            for rec in df.reset_index().to_dict("records")]


def _scalar(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if (v != v) else round(float(v), 6)  # NaN check
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (pd.Timestamp,)):
        return v.isoformat()
    if v is None or (isinstance(v, float) and v != v):
        return None
    return str(v)
