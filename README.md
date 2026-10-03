# Marketplace Fulfillment Quality

An independent operations analytics case study exploring how to detect, diagnose, and prioritize fulfillment-quality deterioration in a marketplace environment.

> **Data transparency:** All order-level data in this project is simulated. A deterioration is intentionally injected into a subset of Retailer C stores beginning September 1, 2026 to test the monitoring and diagnostic workflow. No Instacart internal data is used.

## Live case study

**[View the interactive case study](https://felipervm.github.io/marketplace-fulfillment-quality/)**

The site is designed as an editorial analytics case rather than a traditional BI dashboard: the investigation unfolds through the story while interactive charts support the evidence.

## Case summary

Retailer C's cancellation rate moves from **3.39% in July** and **2.91% in August** to **5.14% in September**.

Against September peer retailers excluding Retailer C (**2.66%**), the gap represents approximately **163 excess cancellations** at Retailer C's order volume.

The investigation asks:

1. **What changed?** — identify the sustained level shift.
2. **Where is it happening?** — isolate daypart and store concentration.
3. **What likely contributed?** — decompose cancellation reasons.
4. **Did monitoring catch it?** — stress-test anomaly detection.
5. **What should Operations do next?** — prioritize action by impact.

## Key analytical findings

- Retailer C September cancellation rate: **5.14%**
- September peers excluding Retailer C: **2.66%**
- Estimated excess cancellations vs peers: **~163**
- Evening cancellation rate: **8.00%**
- Retailer-driven failures: **40.8%** of Retailer C September cancellations
- Retailer-initiated out-of-stock: **29.3%**
- Early store closures: **20 of 29** occur in evening windows
- Rolling 14-day + 2σ: **1** Retailer C September alert
- Fixed pre-period baseline: **12** alerts
- Sustained three-day rule: **6** alerts

## Reproduce the analysis

1. Install dependencies with `pip install -r requirements.txt`.
2. Run `python scripts/generate_simulated_data.py`.
3. Run `python scripts/build_analysis_outputs.py`.

The generated 100k-row raw dataset is intentionally excluded from Git. Lightweight analytical outputs used for validation and BI work are committed in `data/`.

## Repository structure

- `index.html` — published interactive case study
- `scripts/generate_simulated_data.py` — deterministic simulation with seed 42 and explicit injected issue
- `scripts/build_analysis_outputs.py` — regenerates analytical outputs and monitoring comparisons
- `sql/analysis_queries.sql` — SQL for trend, peer baseline, fixed-baseline monitoring, root-cause, and province analysis
- `data/` — lightweight analytical outputs
- `tableau_ready/` — Tableau Public build guidance
- `requirements.txt` — Python dependencies

## Monitoring lesson

A simple rolling threshold can fail on sustained deterioration because its baseline eventually absorbs the new level. This case explicitly treats that weakness as an analytical finding instead of hiding it.

In production, I would additionally validate day-of-week seasonality, false-positive cost, CUSUM/change-point methods, and intervention measurement.

## Skills demonstrated

**SQL · Python · Pandas · Operations Analytics · Data Quality · Anomaly Detection · Root-Cause Analysis · Impact Sizing · Statistical Communication · Reproducibility**

## Author

**Felipe Mattos**  
Computer Programming and Analysis — George Brown Polytechnic  
[LinkedIn](https://www.linkedin.com/in/felipervm)

---

Independent portfolio project · Simulated data · Not affiliated with Instacart.
