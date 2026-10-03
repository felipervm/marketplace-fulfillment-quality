# Marketplace Fulfillment Quality

An independent operations analytics case study exploring how to detect, diagnose, and prioritize fulfillment-quality deterioration in a marketplace environment.

> **Data transparency:** All order-level data in this project is simulated. A deterioration is intentionally injected into a subset of Retailer C stores beginning September 1, 2026 to test the monitoring and diagnostic workflow. No Instacart internal data is used.

## Case summary

Retailer C's cancellation rate moves from **3.39% in July** and **2.91% in August** to **5.14% in September**.

Against September peer retailers excluding Retailer C (**2.66%**), the gap represents approximately **163 excess cancellations** at Retailer C's order volume.

The investigation then asks:

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

The original rolling 14-day + 2σ monitor produces only **1** September alert for Retailer C because the rolling baseline adapts upward. A fixed pre-period baseline and a sustained three-day deterioration rule make the level shift substantially more visible.

## Interactive case study

Open **[index.html](./index.html)** locally, or publish the repository with GitHub Pages for the full scroll-based analytical story.

The page is designed as an editorial case study rather than a traditional BI dashboard: the analysis unfolds through the investigation, while interactive charts support the narrative.

## Repository structure

- `index.html` — interactive portfolio case study
- `scripts/generate_simulated_data.py` — reproducible simulation with fixed seed and explicit injected issue
- `sql/analysis_queries.sql` — SQL for trend, peer baseline, monitoring, root-cause, and province analysis
- `data/` — lightweight analytical outputs
- `tableau_ready/` — aggregated files and Tableau Public build guidance
- `notebooks/` — reproducible Python analysis

## Monitoring lesson

A simple rolling threshold can fail on sustained deterioration because its baseline eventually absorbs the new level. This case explicitly treats that weakness as an analytical finding instead of hiding it.

The corrected workflow evaluates:

- **Fixed pre-period baseline**
- **Three-day sustained deterioration rule**
- Minimum-volume requirements

In production, I would additionally validate day-of-week seasonality, false-positive cost, CUSUM/change-point methods, and intervention measurement.

## Skills demonstrated

**SQL · Python · Pandas · Operations Analytics · Data Quality · Anomaly Detection · Root-Cause Analysis · Impact Sizing · Statistical Communication · Reproducibility**

## Author

**Felipe Mattos**  
Computer Programming and Analysis — George Brown Polytechnic  
[LinkedIn](https://www.linkedin.com/in/felipervm)

---

Independent portfolio project · Simulated data · Not affiliated with Instacart.
