"""Generate a feature-exercising test CSV for InsightForge.

Covers: id / numeric / categorical / boolean / datetime / text columns, missing values,
duplicate rows, univariate + multivariate outliers, strong & weak correlations,
categorical->numeric effects, skewed distributions, a time series, and a dirty column.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
N = 50_000

regions = ["North America", "Europe", "APAC", "LATAM", "MEA"]
region = rng.choice(regions, N, p=[0.34, 0.28, 0.22, 0.10, 0.06])
region_lift = {"North America": 1.35, "Europe": 1.15, "APAC": 1.0, "LATAM": 0.8, "MEA": 0.7}

segment = rng.choice(["Enterprise", "Mid-Market", "SMB", "Startup"], N, p=[0.15, 0.25, 0.4, 0.2])
seg_units = {"Enterprise": 40, "Mid-Market": 14, "SMB": 5, "Startup": 3}

channel = rng.choice(["Direct", "Partner", "Online", "Reseller"], N)
plan = rng.choice(["Free", "Pro", "Business", "Enterprise"], N, p=[0.3, 0.35, 0.25, 0.1])

start = pd.Timestamp("2023-01-01")
order_date = pd.Series(
    start + pd.to_timedelta(rng.integers(0, 730, N), unit="D")
    + pd.to_timedelta(rng.integers(0, 86400, N), unit="s")
)

# seasonal + trending signup volume feel via day index
day_idx = (order_date - start).dt.days
seasonal = 1 + 0.3 * np.sin(2 * np.pi * day_idx / 365.25)
trend = 1 + day_idx / 2000.0

base_units = np.array([seg_units[s] for s in segment])
units = rng.poisson(np.clip(base_units * seasonal, 1, None)).astype(float)

lift = np.array([region_lift[r] for r in region])
unit_price = rng.gamma(3.0, 40.0, N) * lift * trend            # right-skewed
revenue = (units * unit_price).round(2)                        # ~ correlated with units & price
cost = (revenue * rng.uniform(0.45, 0.72, N)).round(2)         # strong corr with revenue
margin = (revenue - cost).round(2)
discount_pct = rng.beta(2, 8, N).round(4)                      # skewed 0..1
nps = np.clip(rng.normal(32, 22, N), -100, 100).round(0)       # roughly normal
support_tickets = rng.poisson(1.2 + (segment == "Enterprise") * 3, N)
is_active = rng.random(N) < 0.78
churned = (~is_active) & (rng.random(N) < 0.6)

customer_id = rng.integers(100000, 130000, N)                  # many repeats -> not an id
order_id = np.arange(1, N + 1)                                 # true id

notes_pool = [
    "renewal upsell", "downgraded plan", "late payment", "expansion seat add",
    "trial converted", "logo churn risk", "positive QBR", "integration issue",
    "", "", "",  # some blanks
]
notes = rng.choice(notes_pool, N)

df = pd.DataFrame({
    "order_id": order_id,
    "customer_id": customer_id,
    "order_date": order_date.dt.strftime("%Y-%m-%d %H:%M:%S"),
    "region": region,
    "customer_segment": segment,
    "acquisition_channel": channel,
    "plan_tier": plan,
    "units": units.astype(int),
    "unit_price_usd": unit_price.round(2),
    "revenue_usd": revenue,
    "cost_usd": cost,
    "margin_usd": margin,
    "discount_pct": discount_pct,
    "nps_score": nps,
    "support_tickets": support_tickets,
    "is_active": is_active,
    "churned": churned,
    "account_notes": notes,
})

# --- inject data-quality issues ---
# missing values, varying severity
for col, frac in [("nps_score", 0.12), ("unit_price_usd", 0.03), ("account_notes", 0.0),
                   ("cost_usd", 0.02), ("acquisition_channel", 0.05)]:
    idx = rng.choice(N, int(N * frac), replace=False)
    df.loc[idx, col] = np.nan

# a mostly-empty column (should be flagged hard)
df["legacy_score"] = np.nan
df.loc[rng.choice(N, int(N * 0.08), replace=False), "legacy_score"] = rng.normal(50, 10, int(N * 0.08)).round(1)

# extreme univariate outliers
df.loc[rng.choice(N, 60, replace=False), "revenue_usd"] = rng.uniform(2_000_000, 5_000_000, 60).round(2)
df.loc[rng.choice(N, 40, replace=False), "units"] = rng.integers(5000, 20000, 40)

# dirty numeric-looking column with junk strings (tests coercion / cleaning)
weight = rng.normal(3.5, 0.8, N).round(2).astype(object)
bad = rng.choice(N, 300, replace=False)
weight[bad] = rng.choice(["n/a", "unknown", "-", "TBD"], 300)
df["package_weight_kg"] = weight

# exact duplicate rows
dupes = df.sample(400, random_state=1)
df = pd.concat([df, dupes], ignore_index=True)
df = df.sample(frac=1, random_state=2).reset_index(drop=True)

out = "insightforge_test_50k.csv"
df.to_csv(out, index=False)
print(f"wrote {out}: {len(df):,} rows x {df.shape[1]} cols")
