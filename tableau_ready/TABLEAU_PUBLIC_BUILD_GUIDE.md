# Tableau Public Build Guide

The repository exports tidy, lightweight CSVs for an optional Tableau Public build. The dashboard is intentionally not included here.

## Refresh

```bash
python scripts/generate_simulated_data.py
python scripts/build_analysis_outputs.py
python scripts/check_outputs.py
```

## Recommended views

1. **Monthly Retailer C cancellation rate + 95% Wilson CI**  
   `tableau_ready/monthly_retailer_metrics.csv`

2. **September retailer comparison + 95% Wilson CI**  
   `tableau_ready/september_retailer_scorecard.csv`

3. **Retailer C September daypart + 95% Wilson CI**  
   `tableau_ready/retailer_c_daypart_with_ci.csv`

4. **Impact sizing with two baselines**  
   `tableau_ready/impact_baselines.csv`

5. **Root-cause change by reason**  
   `tableau_ready/root_cause_change_by_reason.csv`

6. **Root-cause change by cancellation type**  
   `tableau_ready/root_cause_change_by_type.csv`

7. **Daypart-adjusted store excess**  
   `tableau_ready/retailer_c_store_adjusted_excess.csv`

8. **Monitoring alert days and episodes**  
   `tableau_ready/monitor_alert_summary.csv`

9. **Monitoring daily detail**  
   `tableau_ready/monitor_alert_detail.csv`

## Suggested dashboard structure

- Executive trend and impact range
- Driver change per 1,000 orders
- Daypart rate with confidence intervals
- Store concentration and Poisson flag
- Monitoring rule comparison
- Methodology and limitations

## Required transparency note

All data is simulated. A September Retailer C deterioration is intentionally injected to test detection and diagnosis. No proprietary marketplace data is used, and the analysis does not establish real-world causal effects.

Suggested dashboard title: **Marketplace Fulfillment Quality Diagnostic**.
