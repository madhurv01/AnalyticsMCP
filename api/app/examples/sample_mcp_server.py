"""A tiny standalone MCP server that acts as a mock data warehouse.

Run it so InsightForge (the data-source hub) has something real to connect to:

    python -m app.examples.sample_mcp_server        # serves on :9100

In the InsightForge UI, add a data source with URL http://sample-mcp:9100/mcp
(inside Docker) or http://localhost:9100/mcp (from the host), then import the
`get_sales` tool.
"""
import numpy as np
import pandas as pd
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SampleWarehouse", host="0.0.0.0", port=9100)


def _sales(n: int) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = int(min(max(n, 10), 20_000))
    region = rng.choice(["North America", "Europe", "APAC", "LATAM"], n, p=[0.4, 0.3, 0.2, 0.1])
    _lift = {"North America": 1.3, "Europe": 1.1, "APAC": 1.0, "LATAM": 0.8}
    lift = np.array([_lift[r] for r in region])
    segment = rng.choice(["Enterprise", "Mid-Market", "SMB"], n, p=[0.2, 0.3, 0.5])
    units = rng.poisson(np.where(segment == "Enterprise", 30, np.where(segment == "Mid-Market", 10, 4)))
    price = (rng.gamma(3, 40, n) * lift).round(2)
    revenue = (units * price).round(2)
    return pd.DataFrame({
        "order_id": np.arange(1, n + 1),
        "order_date": pd.date_range("2024-01-01", periods=n, freq="37min").astype(str),
        "region": region,
        "segment": segment,
        "channel": rng.choice(["Direct", "Partner", "Online"], n),
        "units": units,
        "unit_price_usd": price,
        "revenue_usd": revenue,
        "discount_pct": rng.beta(2, 8, n).round(3),
        "is_repeat_customer": rng.random(n) < 0.55,
    })


@mcp.tool()
def get_sales(rows: int = 3000) -> str:
    """Return synthetic sales orders as JSON (a list of row objects). `rows` caps the count."""
    return _sales(rows).to_json(orient="records")


@mcp.tool()
def get_regions_summary() -> str:
    """Return revenue aggregated by region as JSON."""
    df = _sales(5000)
    return (df.groupby("region", as_index=False)
            .agg(orders=("order_id", "count"), revenue=("revenue_usd", "sum"),
                 avg_units=("units", "mean"))
            .round(2)
            .to_json(orient="records"))


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
