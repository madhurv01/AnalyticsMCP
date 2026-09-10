"""Tests for run_query (sandbox) and the MCP data-source hub's parsing."""
import numpy as np
import pandas as pd
import pytest

from app.analytics.query import QueryError, run
from app.mcpclient import to_dataframe


@pytest.fixture
def df():
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "region": rng.choice(["N", "S", "E"], 300),
        "revenue": rng.gamma(2, 50, 300).round(2),
        "units": rng.poisson(4, 300),
    })


def test_query_allows_analytical_chains(df):
    r = run(df, "df.groupby('region')['revenue'].mean().round(2).sort_values()")
    assert r["kind"] == "series" and r["row_count"] == 3

    r = run(df, "df[['revenue','units']].corr()")
    assert r["kind"] == "table"

    r = run(df, "df[df['units'] > 5]['region'].value_counts()")
    assert r["kind"] == "series"

    r = run(df, "df['revenue'].sum()")
    assert r["kind"] == "scalar"


@pytest.mark.parametrize("bad", [
    '__import__("os").system("ls")',
    'df.to_csv("/tmp/pwn")',
    'open("/etc/passwd").read()',
    'df.apply(lambda r: __import__("os"), axis=1)',
    'df.__class__.__mro__',
    'eval("1+1")',
    "df['x'].values.__setitem__(0, 9)",
])
def test_query_blocks_dangerous_input(df, bad):
    with pytest.raises(QueryError):
        run(df, bad)


def test_hub_parses_json_rows():
    df = to_dataframe('[{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]')
    assert list(df.columns) == ["a", "b"] and len(df) == 2


def test_hub_parses_columns_rows_shape():
    df = to_dataframe('{"columns": ["a", "b"], "rows": [[1, 2], [3, 4]]}')
    assert df.shape == (2, 2)


def test_hub_parses_csv_text():
    df = to_dataframe("a,b,c\n1,2,3\n4,5,6\n")
    assert df.shape == (2, 3)


def test_hub_parses_github_style_items():
    df = to_dataframe('{"total_count": 2, "items": [{"name": "a", "owner": {"login": "x"}}, '
                      '{"name": "b", "owner": {"login": "y"}}]}')
    assert df.shape == (2, 2) and "owner.login" in df.columns


def test_hub_parses_markdown_table():
    md = "Results:\n\n| repo | stars |\n|------|-------|\n| a | 12 |\n| b | 7 |\n\ndone"
    df = to_dataframe(md)
    assert list(df.columns) == ["repo", "stars"] and len(df) == 2


def test_hub_strips_json_fence():
    df = to_dataframe('```json\n[{"a": 1}, {"a": 2}]\n```')
    assert len(df) == 2


def test_hub_rejects_garbage():
    with pytest.raises(ValueError):
        to_dataframe("not a table at all, just prose about something")
