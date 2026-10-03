# Tableau Public Build Guide

The repository includes lightweight analysis outputs in `data/`. For a full refresh:

1. Run `python scripts/generate_simulated_data.py`
2. Run `python scripts/build_analysis_outputs.py`

Recommended views:

1. **Monthly cancellation trend** — `data/monthly_retailer_metrics.csv`
2. **September retailer comparison** — `data/september_retailer_scorecard.csv`
3. **Daypart rate + 95% CI** — `data/retailer_c_daypart_with_ci.csv`
4. **Store impact** — `data/retailer_c_store_metrics.csv`
5. **Root-cause mix** — `data/retailer_c_root_cause_share.csv`
6. **Monitoring-method comparison** — `data/alert_counts_by_retailer.csv`
7. **Province quality cut** — `data/september_province_scorecard.csv`

Required transparency note: all data is simulated, and the September Retailer C issue is intentionally injected to test detection and diagnosis.

Suggested dashboard title: **Marketplace Fulfillment Quality Diagnostic**.
