from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
N = 100_000
OUT = Path(__file__).resolve().parents[1] / "data" / "simulated_fulfillment_orders.csv"

rng = np.random.default_rng(SEED)
retailers = np.array(["Retailer A","Retailer B","Retailer C","Retailer D","Retailer E","Retailer F"])
retailer = rng.choice(retailers, size=N, p=[0.19,0.17,0.20,0.16,0.15,0.13])
province = rng.choice(["ON","BC","AB","NS"], size=N, p=[0.55,0.22,0.17,0.06])

start = np.datetime64("2026-07-01")
order_date = start + rng.integers(0, 92, size=N).astype("timedelta64[D]")
hour = rng.choice(np.arange(8,23), size=N, p=np.array([2,3,4,5,6,7,8,9,10,10,9,8,7,6,6])/100)
daypart = np.where(hour < 12, "Morning", np.where(hour < 17, "Afternoon", "Evening"))
store_num = rng.integers(1, 41, size=N)
store_id = np.array([f"{r.split()[-1]}{s:03d}" for r,s in zip(retailer, store_num)])

items_requested = np.clip(rng.poisson(18, N)+1, 1, 80)
fill_rate = np.clip(rng.normal(0.972, 0.025, N), 0.70, 1.0)

# Intentionally injected test condition.
problem_stores = {f"C{s:03d}" for s in [2,5,7,9,11,14,18,21,24,29,33,37]}
issue_mask = (
    (retailer == "Retailer C")
    & np.isin(store_id, list(problem_stores))
    & (daypart == "Evening")
    & (order_date >= np.datetime64("2026-09-01"))
)
fill_rate[issue_mask] -= rng.uniform(0.08, 0.18, issue_mask.sum())
fill_rate = np.clip(fill_rate, 0.60, 1.0)

items_found = np.minimum(items_requested, np.floor(items_requested*fill_rate).astype(int))
items_replaced = np.minimum(items_requested-items_found, rng.binomial(np.maximum(items_requested-items_found,0), 0.45))

base_cancel = np.select(
    [retailer=="Retailer A",retailer=="Retailer B",retailer=="Retailer C",retailer=="Retailer D",retailer=="Retailer E",retailer=="Retailer F"],
    [0.022,0.026,0.029,0.024,0.027,0.025], default=0.025
)
cancel_prob = base_cancel + np.where(fill_rate < 0.90, 0.045, 0) + np.where(daypart=="Evening", 0.004, 0) + np.where(issue_mask, 0.105, 0)
cancelled = rng.random(N) < cancel_prob

reason_choices = np.array(["customer_driven","instacart_driven","retailer_driven","shopper_driven","unbatchable","other"])
cancellation_reason = np.full(N, "", dtype=object)
cancellation_reason[cancelled] = rng.choice(reason_choices, cancelled.sum(), p=[0.28,0.06,0.24,0.16,0.12,0.14])
issue_cancel = issue_mask & cancelled
cancellation_reason[issue_cancel] = rng.choice(["retailer_driven","other","shopper_driven","unbatchable"], issue_cancel.sum(), p=[0.60,0.20,0.10,0.10])

mapping = {
 "customer_driven":["customer requested to cancel","customer requested since order is late","incorrect customer information (phone/address)"],
 "instacart_driven":["manual_fraud","missing charge log for delivery"],
 "retailer_driven":["retailer initiated out of stock","store early closure","cancelled by retailer"],
 "shopper_driven":["shopper unable to complete order","shopper could not find address","unable to access location"],
 "unbatchable":["unbatchable","unable to reschedule unbatchable","unable to reschedule as no option found"],
 "other":["item and replacement issues","too many replacements","store outage","wrong store hours","OnLine Pay Failure","other"]
}
def ctype(reason, issue=False):
    if issue and reason == "retailer_driven":
        return rng.choice(["retailer initiated out of stock","store early closure"], p=[0.82,0.18])
    if issue and reason == "other":
        return rng.choice(["item and replacement issues","store outage","wrong store hours"], p=[0.65,0.20,0.15])
    return rng.choice(mapping[reason])

cancellation_type = np.full(N, "", dtype=object)
for i in np.where(cancelled)[0]:
    cancellation_type[i] = ctype(cancellation_reason[i], bool(issue_mask[i]))

scheduled_duration = rng.normal(62,12,N)
traffic_delay = rng.normal(0,12,N)
late_extra = np.where(daypart=="Evening", rng.normal(5,5,N), 0)
issue_delay = np.where(issue_mask, rng.normal(25,10,N), 0)
delivery_delay_minutes = np.round(np.clip(traffic_delay+late_extra+issue_delay,-25,90),1)
late_delivery = (~cancelled) & (delivery_delay_minutes > 15)
reschedule_prob = 0.018 + np.where(daypart=="Evening",0.007,0) + np.where(issue_mask,0.065,0)
rescheduled = (~cancelled) & (rng.random(N) < reschedule_prob)

df = pd.DataFrame({
 "order_id":[f"ORD{i+1:06d}" for i in range(N)], "order_date":pd.to_datetime(order_date),
 "province":province, "retailer":retailer, "store_id":store_id, "order_hour":hour, "daypart":daypart,
 "items_requested":items_requested, "items_found":items_found, "items_replaced":items_replaced,
 "fill_rate":np.round(items_found/items_requested,4), "cancelled":cancelled.astype(int),
 "cancellation_reason":cancellation_reason, "cancellation_type":cancellation_type,
 "rescheduled":rescheduled.astype(int), "delivery_delay_minutes":delivery_delay_minutes,
 "late_delivery":late_delivery.astype(int)
})
OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)
print(f"Wrote {len(df):,} rows to {OUT}")