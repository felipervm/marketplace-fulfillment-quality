from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "simulated_fulfillment_orders.csv"

if not RAW.exists():
    raise FileNotFoundError(
        "Raw simulated dataset not found. Run scripts/generate_simulated_data.py first."
    )

df = pd.read_csv(RAW, parse_dates=["order_date"])
df["month"] = df["order_date"].dt.to_period("M").astype(str)

sept = df[df["order_date"] >= "2026-09-01"].copy()
c_sept = sept[sept["retailer"] == "Retailer C"].copy()
peers_sept = sept[sept["retailer"] != "Retailer C"].copy()


def wilson_ci(successes, n, z=1.96):
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) / n) + z * z / (4 * n * n)) / denom
    return center - half, center + half


# 1) Monthly retailer metrics
monthly = (
    df.groupby(["month", "retailer"])
      .agg(
          orders=("order_id", "count"),
          cancellations=("cancelled", "sum"),
          cancellation_rate=("cancelled", "mean"),
      )
      .reset_index()
)
monthly["cancellation_rate_pct"] = monthly["cancellation_rate"] * 100
monthly.to_csv(DATA / "monthly_retailer_metrics.csv", index=False)


# 2) September retailer scorecard
peer_rate = peers_sept["cancelled"].mean()

scorecard = (
    sept.groupby("retailer")
        .agg(
            orders=("order_id", "count"),
            cancellations=("cancelled", "sum"),
            cancellation_rate=("cancelled", "mean"),
            late_rate=("late_delivery", "mean"),
            reschedule_rate=("rescheduled", "mean"),
            avg_fill_rate=("fill_rate", "mean"),
        )
        .reset_index()
)

for col in ["cancellation_rate", "late_rate", "reschedule_rate", "avg_fill_rate"]:
    scorecard[col + "_pct"] = scorecard[col] * 100

scorecard["peer_rate_excl_c_pct"] = peer_rate * 100
scorecard["expected_cancellations_at_peer_rate"] = scorecard["orders"] * peer_rate
scorecard["excess_cancellations_vs_peers"] = (
    scorecard["cancellations"] - scorecard["expected_cancellations_at_peer_rate"]
)
scorecard.to_csv(DATA / "september_retailer_scorecard.csv", index=False)


# 3) Daypart rates + 95% Wilson intervals for Retailer C
daypart_rows = []
for daypart, g in c_sept.groupby("daypart"):
    successes = int(g["cancelled"].sum())
    n = len(g)
    lo, hi = wilson_ci(successes, n)
    daypart_rows.append({
        "daypart": daypart,
        "orders": n,
        "cancellations": successes,
        "rate_pct": successes / n * 100,
        "ci_low_pct": lo * 100,
        "ci_high_pct": hi * 100,
    })

daypart = pd.DataFrame(daypart_rows)
order = pd.Categorical(
    daypart["daypart"],
    categories=["Morning", "Afternoon", "Evening"],
    ordered=True,
)
daypart = daypart.assign(_order=order).sort_values("_order").drop(columns="_order")
daypart.to_csv(DATA / "retailer_c_daypart_with_ci.csv", index=False)


# 4) Root-cause share for Retailer C
root = (
    c_sept[c_sept["cancelled"] == 1]
    .groupby("cancellation_reason")
    .size()
    .reset_index(name="cancellations")
)
root["share_pct"] = root["cancellations"] / root["cancellations"].sum() * 100
root = root.sort_values("cancellations", ascending=False)
root.to_csv(DATA / "retailer_c_root_cause_share.csv", index=False)


# 5) Store-level impact sizing
stores = (
    c_sept.groupby("store_id")
    .agg(
        orders=("order_id", "count"),
        cancellations=("cancelled", "sum"),
        cancellation_rate=("cancelled", "mean"),
        late_rate=("late_delivery", "mean"),
        reschedule_rate=("rescheduled", "mean"),
        avg_fill_rate=("fill_rate", "mean"),
    )
    .reset_index()
)

for col in ["cancellation_rate", "late_rate", "reschedule_rate", "avg_fill_rate"]:
    stores[col + "_pct"] = stores[col] * 100

c_baseline = c_sept["cancelled"].mean()
stores["expected_cancellations_at_c_baseline"] = stores["orders"] * c_baseline
stores["excess_cancellations_vs_c_baseline"] = (
    stores["cancellations"] - stores["expected_cancellations_at_c_baseline"]
)
stores.to_csv(DATA / "retailer_c_store_metrics.csv", index=False)


# 6) Province-level quality summary
province = (
    sept.groupby("province")
    .agg(
        orders=("order_id", "count"),
        cancellations=("cancelled", "sum"),
        cancellation_rate=("cancelled", "mean"),
        late_rate=("late_delivery", "mean"),
        reschedule_rate=("rescheduled", "mean"),
        avg_fill_rate=("fill_rate", "mean"),
    )
    .reset_index()
)

for col in ["cancellation_rate", "late_rate", "reschedule_rate", "avg_fill_rate"]:
    province[col + "_pct"] = province[col] * 100

province.to_csv(DATA / "september_province_scorecard.csv", index=False)


# 7) Monitoring comparison
daily = (
    df.groupby(["order_date", "retailer"])
    .agg(
        orders=("order_id", "count"),
        cancellation_rate=("cancelled", "mean"),
    )
    .reset_index()
    .sort_values(["retailer", "order_date"])
)

pre = (
    daily[daily["order_date"] < "2026-09-01"]
    .groupby("retailer")
    .agg(
        baseline_rate=("cancellation_rate", "mean"),
        baseline_sd=("cancellation_rate", "std"),
    )
    .reset_index()
)

monitor = daily.merge(pre, on="retailer", how="left")

monitor["rolling14_mean"] = (
    monitor.groupby("retailer")["cancellation_rate"]
    .transform(lambda s: s.shift(1).rolling(14, min_periods=7).mean())
)
monitor["rolling14_sd"] = (
    monitor.groupby("retailer")["cancellation_rate"]
    .transform(lambda s: s.shift(1).rolling(14, min_periods=7).std())
)
monitor["rolling14_z"] = (
    (monitor["cancellation_rate"] - monitor["rolling14_mean"])
    / monitor["rolling14_sd"].replace(0, np.nan)
)
monitor["rolling14_alert"] = (
    (monitor["orders"] >= 100) & (monitor["rolling14_z"] >= 2)
).astype(int)

monitor["fixed_z"] = (
    (monitor["cancellation_rate"] - monitor["baseline_rate"])
    / monitor["baseline_sd"].replace(0, np.nan)
)
monitor["fixed_baseline_alert"] = (
    (monitor["orders"] >= 100) & (monitor["fixed_z"] >= 2)
).astype(int)

monitor["above_1sd"] = (
    (monitor["orders"] >= 100)
    & (
        monitor["cancellation_rate"]
        > monitor["baseline_rate"] + monitor["baseline_sd"]
    )
).astype(int)

monitor["sustained_3day_alert"] = (
    monitor.groupby("retailer")["above_1sd"]
    .transform(lambda s: s.rolling(3, min_periods=3).sum().eq(3).astype(int))
)

alert_counts = (
    monitor[monitor["order_date"] >= "2026-09-01"]
    .groupby("retailer")
    .agg(
        rolling14_alerts=("rolling14_alert", "sum"),
        fixed_baseline_alerts=("fixed_baseline_alert", "sum"),
        sustained_alerts=("sustained_3day_alert", "sum"),
    )
    .reset_index()
)
alert_counts.to_csv(DATA / "alert_counts_by_retailer.csv", index=False)

print("Analysis outputs refreshed successfully.")
