from pathlib import Path
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "simulated_fulfillment_orders.csv"
HEADLINE = DATA / "headline_metrics.csv"

if not RAW.exists():
    raise FileNotFoundError("Run scripts/generate_simulated_data.py first.")
if not HEADLINE.exists():
    raise FileNotFoundError("Run scripts/build_analysis_outputs.py first.")

df = pd.read_csv(RAW, parse_dates=["order_date"])
published = pd.read_csv(HEADLINE).set_index("metric")["value"].to_dict()

pre_c = df[(df["retailer"] == "Retailer C") & (df["order_date"] < "2026-09-01")]
sept = df[df["order_date"] >= "2026-09-01"]
c = sept[sept["retailer"] == "Retailer C"]
peers = sept[sept["retailer"] != "Retailer C"]

months = (
    df[df["retailer"] == "Retailer C"]
    .assign(month=lambda x: x["order_date"].dt.to_period("M").astype(str))
    .groupby("month")["cancelled"].mean()
)

canc = c[c["cancelled"] == 1]
closures = canc[canc["cancellation_type"] == "store early closure"]
alerts = pd.read_csv(DATA / "monitor_alert_summary.csv").set_index("retailer")
store_summary = pd.read_csv(DATA / "store_concentration_summary.csv").iloc[0]

computed = {
    "retailer_c_jul_rate_pct": months.loc["2026-07"] * 100,
    "retailer_c_aug_rate_pct": months.loc["2026-08"] * 100,
    "retailer_c_sep_rate_pct": months.loc["2026-09"] * 100,
    "sep_peers_excl_c_rate_pct": peers["cancelled"].mean() * 100,
    "sep_gap_vs_peers_pp": (c["cancelled"].mean() - peers["cancelled"].mean()) * 100,
    "excess_vs_peers": c["cancelled"].sum() - len(c) * peers["cancelled"].mean(),
    "excess_vs_own_jul_aug": c["cancelled"].sum() - len(c) * pre_c["cancelled"].mean(),
    "retailer_c_evening_rate_pct": c.loc[c["daypart"] == "Evening", "cancelled"].mean() * 100,
    "retailer_c_morning_orders": float((c["daypart"] == "Morning").sum()),
    "retailer_driven_share_pct": (canc["cancellation_reason"] == "retailer_driven").mean() * 100,
    "retailer_initiated_oos_share_pct": (canc["cancellation_type"] == "retailer initiated out of stock").mean() * 100,
    "early_closures_evening": float((closures["daypart"] == "Evening").sum()),
    "early_closures_total": float(len(closures)),
    "rolling14_c_alert_days": float(alerts.loc["Retailer C", "rolling14_alert_days"]),
    "fixed_c_alert_days": float(alerts.loc["Retailer C", "fixed_baseline_alert_days"]),
    "sustained_c_alert_days": float(alerts.loc["Retailer C", "sustained_3day_alert_days"]),
    "flagged_stores_z_ge_3": float(store_summary["flagged_stores"]),
    "flagged_store_order_share_pct": float(store_summary["flagged_order_share_pct"]),
    "flagged_store_share_net_excess_pct": float(store_summary["flagged_share_of_net_excess_pct"]),
}

missing = sorted(set(computed) - set(published))
if missing:
    raise AssertionError(f"Missing headline metrics: {missing}")

failures = []
for metric, actual in computed.items():
    expected = float(published[metric])
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10):
        failures.append((metric, expected, actual))

if failures:
    details = "\n".join(
        f"{metric}: output={expected!r}, recomputed={actual!r}"
        for metric, expected, actual in failures
    )
    raise AssertionError("Headline output verification failed:\n" + details)

print(f"Verified {len(computed)} headline metrics against regenerated data.")
