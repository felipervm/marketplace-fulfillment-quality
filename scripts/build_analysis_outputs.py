from pathlib import Path
import math
import shutil
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TABLEAU = ROOT / "tableau_ready"
RAW = DATA / "simulated_fulfillment_orders.csv"
ONSET = pd.Timestamp("2026-09-01")
MIN_DAILY_ORDERS = 100

if not RAW.exists():
    raise FileNotFoundError(
        "Raw simulated dataset not found. Run scripts/generate_simulated_data.py first."
    )

df = pd.read_csv(RAW, parse_dates=["order_date"])
df["month"] = df["order_date"].dt.to_period("M").astype(str)

pre_c = df[(df["retailer"] == "Retailer C") & (df["order_date"] < ONSET)].copy()
sept = df[df["order_date"] >= ONSET].copy()
c_sept = sept[sept["retailer"] == "Retailer C"].copy()
peers_sept = sept[sept["retailer"] != "Retailer C"].copy()


def wilson_ci(successes, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) / n) + z * z / (4 * n * n)) / denom
    return center - half, center + half


def two_prop_ztest(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se
    p_value = math.erfc(abs(z) / math.sqrt(2))
    return z, p_value


def add_ci(frame, successes_col="cancellations", n_col="orders"):
    lows, highs = [], []
    for _, row in frame.iterrows():
        lo, hi = wilson_ci(int(row[successes_col]), int(row[n_col]))
        lows.append(lo * 100)
        highs.append(hi * 100)
    frame["ci_low_pct"] = lows
    frame["ci_high_pct"] = highs
    return frame


def contiguous_episodes(flags):
    s = flags.astype(int)
    return int(((s == 1) & (s.shift(1, fill_value=0) == 0)).sum())


# 1) Monthly Retailer C metrics with 95% Wilson intervals.
monthly = (
    df[df["retailer"] == "Retailer C"]
    .groupby("month")
    .agg(
        orders=("order_id", "count"),
        cancellations=("cancelled", "sum"),
        cancellation_rate=("cancelled", "mean"),
    )
    .reset_index()
)
monthly.insert(1, "retailer", "Retailer C")
monthly["cancellation_rate_pct"] = monthly["cancellation_rate"] * 100
monthly = add_ci(monthly)
monthly.to_csv(DATA / "monthly_retailer_metrics.csv", index=False)


# 2) September retailer scorecard with Wilson intervals.
scorecard = (
    sept.groupby("retailer")
    .agg(
        orders=("order_id", "count"),
        cancellations=("cancelled", "sum"),
        cancellation_rate=("cancelled", "mean"),
    )
    .reset_index()
)
scorecard["cancellation_rate_pct"] = scorecard["cancellation_rate"] * 100
scorecard = add_ci(scorecard)
scorecard.to_csv(DATA / "september_retailer_scorecard.csv", index=False)


# 3) Retailer C September daypart rates with Wilson intervals.
daypart = (
    c_sept.groupby("daypart")
    .agg(
        orders=("order_id", "count"),
        cancellations=("cancelled", "sum"),
        cancellation_rate=("cancelled", "mean"),
    )
    .reset_index()
)
daypart["rate_pct"] = daypart["cancellation_rate"] * 100
daypart = add_ci(daypart)
daypart = daypart.drop(columns=["cancellation_rate"])
order = pd.Categorical(
    daypart["daypart"],
    categories=["Morning", "Afternoon", "Evening"],
    ordered=True,
)
daypart = daypart.assign(_order=order).sort_values("_order").drop(columns="_order")
daypart.to_csv(DATA / "retailer_c_daypart_with_ci.csv", index=False)


# 4) September cancellation mix, retained for descriptive context.
root_share = (
    c_sept[c_sept["cancelled"] == 1]
    .groupby("cancellation_reason")
    .size()
    .reset_index(name="cancellations")
)
root_share["share_pct"] = root_share["cancellations"] / root_share["cancellations"].sum() * 100
root_share = root_share.sort_values("cancellations", ascending=False)
root_share.to_csv(DATA / "retailer_c_root_cause_share.csv", index=False)

type_share = (
    c_sept[c_sept["cancelled"] == 1]
    .groupby(["cancellation_reason", "cancellation_type"])
    .size()
    .reset_index(name="cancellations")
)
type_share["share_pct"] = type_share["cancellations"] / len(c_sept[c_sept["cancelled"] == 1]) * 100
type_share = type_share.sort_values("cancellations", ascending=False)
type_share.to_csv(DATA / "retailer_c_cancellation_type_share.csv", index=False)


# 5) Root-cause change: Jul-Aug vs September per 1,000 orders.
def driver_change(column):
    pre_counts = pre_c[pre_c["cancelled"] == 1].groupby(column).size()
    post_counts = c_sept[c_sept["cancelled"] == 1].groupby(column).size()
    labels = sorted(set(pre_counts.index).union(post_counts.index))
    rows = []
    total_excess = (
        int(c_sept["cancelled"].sum())
        - len(c_sept) * (pre_c["cancelled"].sum() / len(pre_c))
    )
    for label in labels:
        pre_count = int(pre_counts.get(label, 0))
        sep_count = int(post_counts.get(label, 0))
        pre_per_1000 = pre_count / len(pre_c) * 1000
        sep_per_1000 = sep_count / len(c_sept) * 1000
        change_per_1000 = sep_per_1000 - pre_per_1000
        implied_excess = change_per_1000 / 1000 * len(c_sept)
        rows.append({
            column: label,
            "jul_aug_cancellations": pre_count,
            "sep_cancellations": sep_count,
            "jul_aug_per_1000": pre_per_1000,
            "sep_per_1000": sep_per_1000,
            "change_per_1000": change_per_1000,
            "implied_excess_cancellations": implied_excess,
            "share_of_total_increase_pct": implied_excess / total_excess * 100,
        })
    return pd.DataFrame(rows).sort_values("implied_excess_cancellations", ascending=False)


driver_type = driver_change("cancellation_type")
driver_reason = driver_change("cancellation_reason")
driver_type.to_csv(DATA / "root_cause_change_by_type.csv", index=False)
driver_reason.to_csv(DATA / "root_cause_change_by_reason.csv", index=False)


# 6) Impact sizing using two defensible descriptive baselines.
peer_rate = peers_sept["cancelled"].mean()
own_pre_rate = pre_c["cancelled"].mean()
observed_cancels = int(c_sept["cancelled"].sum())
impact = pd.DataFrame([
    {
        "baseline": "Retailer C Jul-Aug",
        "baseline_rate_pct": own_pre_rate * 100,
        "expected_cancellations": len(c_sept) * own_pre_rate,
        "observed_cancellations": observed_cancels,
        "excess_cancellations": observed_cancels - len(c_sept) * own_pre_rate,
    },
    {
        "baseline": "September peers excluding Retailer C",
        "baseline_rate_pct": peer_rate * 100,
        "expected_cancellations": len(c_sept) * peer_rate,
        "observed_cancellations": observed_cancels,
        "excess_cancellations": observed_cancels - len(c_sept) * peer_rate,
    },
])
impact.to_csv(DATA / "impact_baselines.csv", index=False)


# 7) Two-proportion z-tests.
z_pre, p_pre = two_prop_ztest(
    int(c_sept["cancelled"].sum()), len(c_sept),
    int(pre_c["cancelled"].sum()), len(pre_c),
)
z_peer, p_peer = two_prop_ztest(
    int(c_sept["cancelled"].sum()), len(c_sept),
    int(peers_sept["cancelled"].sum()), len(peers_sept),
)
tests = pd.DataFrame([
    {
        "comparison": "Retailer C Sep vs Retailer C Jul-Aug",
        "rate_1_pct": c_sept["cancelled"].mean() * 100,
        "rate_2_pct": pre_c["cancelled"].mean() * 100,
        "z_stat": z_pre,
        "p_value_two_sided": p_pre,
    },
    {
        "comparison": "Retailer C Sep vs Sep peers excluding C",
        "rate_1_pct": c_sept["cancelled"].mean() * 100,
        "rate_2_pct": peers_sept["cancelled"].mean() * 100,
        "z_stat": z_peer,
        "p_value_two_sided": p_peer,
    },
])
tests.to_csv(DATA / "statistical_tests.csv", index=False)


# 8) Daypart-adjusted store excess using Retailer C Jul-Aug daypart rates.
pre_daypart_rates = pre_c.groupby("daypart")["cancelled"].mean().to_dict()
store_daypart = (
    c_sept.groupby(["store_id", "daypart"])
    .agg(orders=("order_id", "count"), cancellations=("cancelled", "sum"))
    .reset_index()
)
store_daypart["baseline_rate"] = store_daypart["daypart"].map(pre_daypart_rates)
store_daypart["expected_cancellations"] = store_daypart["orders"] * store_daypart["baseline_rate"]
stores = (
    store_daypart.groupby("store_id")
    .agg(
        orders=("orders", "sum"),
        cancellations=("cancellations", "sum"),
        expected_cancellations=("expected_cancellations", "sum"),
    )
    .reset_index()
)
stores["adjusted_excess_cancellations"] = stores["cancellations"] - stores["expected_cancellations"]
stores["poisson_z"] = (
    stores["adjusted_excess_cancellations"]
    / np.sqrt(stores["expected_cancellations"].replace(0, np.nan))
)
stores["flagged_z_ge_3"] = (stores["poisson_z"] >= 3).astype(int)
stores = stores.sort_values("adjusted_excess_cancellations", ascending=False)
stores.to_csv(DATA / "retailer_c_store_adjusted_excess.csv", index=False)

flagged = stores[stores["flagged_z_ge_3"] == 1]
net_excess = stores["adjusted_excess_cancellations"].sum()
store_summary = pd.DataFrame([{
    "flagged_stores": len(flagged),
    "total_stores": len(stores),
    "flagged_order_share_pct": flagged["orders"].sum() / stores["orders"].sum() * 100,
    "flagged_excess_cancellations": flagged["adjusted_excess_cancellations"].sum(),
    "net_adjusted_excess_cancellations": net_excess,
    "flagged_share_of_net_excess_pct": flagged["adjusted_excess_cancellations"].sum() / net_excess * 100,
}])
store_summary.to_csv(DATA / "store_concentration_summary.csv", index=False)


# 9) Province-level quality summary.
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


# 10) Monitoring comparison: alert days and contiguous alert episodes.
daily = (
    df.groupby(["order_date", "retailer"])
    .agg(
        orders=("order_id", "count"),
        cancellations=("cancelled", "sum"),
        cancellation_rate=("cancelled", "mean"),
    )
    .reset_index()
    .sort_values(["retailer", "order_date"])
)
pre_daily = (
    daily[daily["order_date"] < ONSET]
    .groupby("retailer")
    .agg(
        baseline_rate=("cancellation_rate", "mean"),
        baseline_sd=("cancellation_rate", "std"),
    )
    .reset_index()
)
monitor = daily.merge(pre_daily, on="retailer", how="left")
monitor["rolling14_mean"] = (
    monitor.groupby("retailer")["cancellation_rate"]
    .transform(lambda s: s.shift(1).rolling(14, min_periods=14).mean())
)
monitor["rolling14_sd"] = (
    monitor.groupby("retailer")["cancellation_rate"]
    .transform(lambda s: s.shift(1).rolling(14, min_periods=14).std())
)
monitor["rolling14_z"] = (
    (monitor["cancellation_rate"] - monitor["rolling14_mean"])
    / monitor["rolling14_sd"].replace(0, np.nan)
)
monitor["rolling14_alert"] = (
    (monitor["orders"] >= MIN_DAILY_ORDERS) & (monitor["rolling14_z"] >= 2)
).astype(int)
monitor["fixed_z"] = (
    (monitor["cancellation_rate"] - monitor["baseline_rate"])
    / monitor["baseline_sd"].replace(0, np.nan)
)
monitor["fixed_baseline_alert"] = (
    (monitor["orders"] >= MIN_DAILY_ORDERS) & (monitor["fixed_z"] >= 2)
).astype(int)
monitor["above_1sd"] = (
    (monitor["orders"] >= MIN_DAILY_ORDERS)
    & (monitor["cancellation_rate"] > monitor["baseline_rate"] + monitor["baseline_sd"])
).astype(int)
monitor["sustained_3day_alert"] = (
    monitor.groupby("retailer")["above_1sd"]
    .transform(lambda s: s.rolling(3, min_periods=3).sum().eq(3).astype(int))
)

eval_monitor = monitor[monitor["order_date"] >= ONSET].copy()
summary_rows = []
for retailer, g in eval_monitor.groupby("retailer"):
    row = {"retailer": retailer}
    for label, col in [
        ("rolling14", "rolling14_alert"),
        ("fixed_baseline", "fixed_baseline_alert"),
        ("sustained_3day", "sustained_3day_alert"),
    ]:
        row[f"{label}_alert_days"] = int(g[col].sum())
        row[f"{label}_episodes"] = contiguous_episodes(g[col])
    summary_rows.append(row)
monitor_summary = pd.DataFrame(summary_rows)
monitor_summary.to_csv(DATA / "monitor_alert_summary.csv", index=False)

# Backward-compatible alert-day file.
alert_counts = monitor_summary[[
    "retailer",
    "rolling14_alert_days",
    "fixed_baseline_alert_days",
    "sustained_3day_alert_days",
]].rename(columns={
    "rolling14_alert_days": "rolling14_alerts",
    "fixed_baseline_alert_days": "fixed_baseline_alerts",
    "sustained_3day_alert_days": "sustained_alerts",
})
alert_counts.to_csv(DATA / "alert_counts_by_retailer.csv", index=False)

monitor_detail = eval_monitor[[
    "order_date", "retailer", "orders", "cancellations", "cancellation_rate",
    "rolling14_mean", "rolling14_sd", "rolling14_z", "rolling14_alert",
    "baseline_rate", "baseline_sd", "fixed_z", "fixed_baseline_alert",
    "above_1sd", "sustained_3day_alert",
]].copy()
monitor_detail.to_csv(DATA / "monitor_alert_detail.csv", index=False)


# 11) Headline metrics used by automated verification and documentation.
oos_count = int(
    ((c_sept["cancelled"] == 1) & (c_sept["cancellation_type"] == "retailer initiated out of stock")).sum()
)
closures = c_sept[
    (c_sept["cancelled"] == 1) & (c_sept["cancellation_type"] == "store early closure")
]
c_alerts = monitor_summary[monitor_summary["retailer"] == "Retailer C"].iloc[0]
headline = pd.DataFrame([
    ["retailer_c_jul_rate_pct", monthly.loc[monthly["month"] == "2026-07", "cancellation_rate_pct"].iloc[0]],
    ["retailer_c_aug_rate_pct", monthly.loc[monthly["month"] == "2026-08", "cancellation_rate_pct"].iloc[0]],
    ["retailer_c_sep_rate_pct", monthly.loc[monthly["month"] == "2026-09", "cancellation_rate_pct"].iloc[0]],
    ["sep_peers_excl_c_rate_pct", peer_rate * 100],
    ["sep_gap_vs_peers_pp", (c_sept["cancelled"].mean() - peer_rate) * 100],
    ["excess_vs_peers", observed_cancels - len(c_sept) * peer_rate],
    ["excess_vs_own_jul_aug", observed_cancels - len(c_sept) * own_pre_rate],
    ["retailer_c_evening_rate_pct", daypart.loc[daypart["daypart"] == "Evening", "rate_pct"].iloc[0]],
    ["retailer_c_morning_orders", daypart.loc[daypart["daypart"] == "Morning", "orders"].iloc[0]],
    ["retailer_driven_share_pct", root_share.loc[root_share["cancellation_reason"] == "retailer_driven", "share_pct"].iloc[0]],
    ["retailer_initiated_oos_share_pct", oos_count / observed_cancels * 100],
    ["early_closures_evening", int((closures["daypart"] == "Evening").sum())],
    ["early_closures_total", len(closures)],
    ["rolling14_c_alert_days", int(c_alerts["rolling14_alert_days"])],
    ["fixed_c_alert_days", int(c_alerts["fixed_baseline_alert_days"])],
    ["sustained_c_alert_days", int(c_alerts["sustained_3day_alert_days"])],
    ["flagged_stores_z_ge_3", int(store_summary["flagged_stores"].iloc[0])],
    ["flagged_store_order_share_pct", store_summary["flagged_order_share_pct"].iloc[0]],
    ["flagged_store_share_net_excess_pct", store_summary["flagged_share_of_net_excess_pct"].iloc[0]],
], columns=["metric", "value"])
headline.to_csv(DATA / "headline_metrics.csv", index=False)


# 12) Tableau-ready tidy outputs.
TABLEAU.mkdir(parents=True, exist_ok=True)
for filename in [
    "monthly_retailer_metrics.csv",
    "september_retailer_scorecard.csv",
    "retailer_c_daypart_with_ci.csv",
    "root_cause_change_by_type.csv",
    "root_cause_change_by_reason.csv",
    "retailer_c_store_adjusted_excess.csv",
    "monitor_alert_summary.csv",
    "monitor_alert_detail.csv",
    "impact_baselines.csv",
]:
    shutil.copyfile(DATA / filename, TABLEAU / filename)

print("Analysis outputs refreshed successfully.")
