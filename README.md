# Marketplace Fulfillment Quality

An independent operations analytics case study on detecting and diagnosing a sustained fulfillment-quality deterioration in a marketplace.

**[View the live case study](https://felipervm.github.io/marketplace-fulfillment-quality/)**

> **Data transparency:** All order-level data is simulated. The dataset contains 100,000 orders across six retailers and four Canadian provinces. A deterioration is intentionally injected into a subset of Retailer C stores beginning September 1, 2026. No Instacart internal data is used, and this project is not affiliated with Instacart.

## Case in 20 seconds

Retailer C's cancellation rate increased from **3.15% across July-August** to **5.14% in September (95% Wilson CI: 4.63%-5.70%)**. September peers excluding Retailer C were at **2.66% (95% CI: 2.47%-2.86%)**.

Depending on the baseline, the September gap represents approximately **131-163 excess cancellations**. The lower estimate uses Retailer C's own July-August rate; the upper estimate uses September peers. The baselines differ because Retailer C's pre-period rate was 3.15%, above the September peer rate of 2.66%.

The increase is concentrated in retailer-side failure modes and a small set of stores. **Retailer-driven cancellations increased by 13.14 per 1,000 orders**, consistent with roughly **86.5 excess cancellations** versus the pre-period rate. Within that group, **retailer-initiated out-of-stock increased by 12.58 per 1,000**, consistent with roughly **82.8 excess cancellations**.

Eleven Retailer C stores meet the case-study flag of **Poisson z >= 3** after adjusting expected September cancellations for Retailer C's own July-August daypart rates. They represent **27.6% of September Retailer C orders** and **99.7% of net daypart-adjusted excess cancellations**. This is an ex-post diagnostic concentration, not a prospective causal estimate.

## Business questions

1. Did Retailer C experience a sustained level shift?
2. How large is the operational impact under different baselines?
3. Which failure modes grew after the onset?
4. Is the deterioration concentrated by daypart and store?
5. Which monitoring rule detects the shift without creating excessive alerts elsewhere?
6. What should Operations investigate first?

## Trend and impact

| Period / benchmark | Cancellation rate | 95% Wilson CI |
|---|---:|---:|
| Retailer C — Jul 2026 | 3.39% | 2.98%-3.86% |
| Retailer C — Aug 2026 | 2.91% | 2.53%-3.33% |
| Retailer C — Sep 2026 | 5.14% | 4.63%-5.70% |
| Sep peers excluding C | 2.66% | 2.47%-2.86% |

Two descriptive impact baselines are reported rather than selecting only the larger estimate:

- **Retailer C Jul-Aug baseline:** 130.9 excess cancellations.
- **September peers excluding C:** 163.0 excess cancellations.
- **Impact range:** approximately **131-163**.

A two-proportion z-test gives **z = 6.91, p = 4.86e-12** for Retailer C September versus its July-August period and **z = 10.28, p = 8.58e-25** versus September peers. These tests quantify separation in the simulated sample; they do not turn the injected condition into real-world causal evidence.

## What grew after the onset?

September cancellation shares alone can be misleading because a large category may simply have been large before the deterioration. The analysis therefore compares cancellation incidence per 1,000 Retailer C orders in July-August with September.

At the reason-group level:

- **Retailer-driven:** 7.83 -> 20.97 per 1,000; **+13.14 per 1,000**, implying **+86.5** cancellations and accounting for **66.1%** of the net increase.
- **Other:** 4.77 -> 8.36 per 1,000; **+3.59 per 1,000**, implying **+23.6**.
- **Shopper-driven:** 4.25 -> 7.45 per 1,000; **+3.20 per 1,000**, implying **+21.0**.
- Customer-driven and Instacart-driven incidence declined, partially offsetting the increases above.

At the detailed cancellation-type level, the largest increase is **retailer initiated out of stock**, from **2.46 to 15.05 per 1,000 orders**. The **+12.58 per 1,000** change is consistent with approximately **82.8 excess cancellations** and likely contributed materially to the September deterioration. **Item and replacement issues** also increased by **4.27 per 1,000**, consistent with approximately **28.1 excess cancellations**.

These are descriptive decompositions. They identify failure modes that grew with the injected deterioration; they do not establish causal attribution.

## Daypart

Retailer C September:

| Daypart | Orders | Cancellation rate | 95% Wilson CI |
|---|---:|---:|---:|
| Morning | 896 | 3.68% | 2.63%-5.13% |
| Afternoon | 2,685 | 2.42% | 1.90%-3.07% |
| Evening | 2,999 | 8.00% | 7.08%-9.03% |

The evening pattern is the strongest. The Morning cell contains only **896 orders**, so its wider interval should not be over-interpreted.

## Store concentration

Expected September cancellations are calculated separately for each store and daypart using **Retailer C's own July-August daypart cancellation rates**. Store-level excess is observed minus expected. A store is flagged when its Poisson approximation produces **z >= 3**.

- Flagged stores: **11 of 40**
- Share of Retailer C September orders: **27.6%**
- Share of net daypart-adjusted excess: **99.7%**

The store ranking is ex-post. It is useful for investigation prioritization, but it will mechanically emphasize extreme observed performers and should be validated prospectively before operational escalation.

## Cancellation mix

In September, retailer-driven issues are the largest cancellation-reason group at **40.8%**, but they are **not a majority** of all Retailer C cancellations.

Two detailed September facts are retained as descriptive context:

- Retailer-initiated out-of-stock: **99 of 338 cancellations (29.3%)**
- Store early closure: **29 cancellations**, of which **20 occurred in evening windows**

The pre/post incidence analysis above is the primary root-cause diagnostic because it measures what actually grew.

## Monitoring comparison

All rules use a minimum of **100 orders per retailer-day** and are evaluated over September 1-30, 2026.

**Legacy rolling rule:** compare the current daily cancellation rate with the mean and sample standard deviation of the **prior 14 complete retailer-days**. Alert when z >= 2.

**Fixed pre-period rule:** compute each retailer's July-August mean and sample standard deviation of daily cancellation rates. Alert when the current daily rate is at least 2 standard deviations above that fixed baseline.

**Sustained three-day rule:** flag a day when the current day and prior two eligible retailer-days are all above the fixed July-August mean + 1 standard deviation.

| Retailer | Rolling alert days | Fixed alert days | Sustained alert days |
|---|---:|---:|---:|
| A | 1 | 0 | 0 |
| B | 2 | 1 | 0 |
| C | **1** | **12** | **6** |
| D | 0 | 0 | 0 |
| E | 2 | 0 | 0 |
| F | 3 | 4 | 1 |

For Retailer C after the onset, the rules generate **1 / 12 / 6 alert days** respectively. Across the other five retailers, they generate **8 / 5 / 1 alert days**, which are treated as false alerts in this simulated evaluation.

Counting contiguous alert episodes rather than days, Retailer C has **1 rolling, 8 fixed, and 4 sustained episodes**. The other retailers have **8, 5, and 1** respectively.

### Monitoring lesson

A rolling monitor can absorb a sustained deterioration into its own baseline. In this case it produces only one post-onset Retailer C alert even though the September level remains elevated. A fixed baseline is more sensitive to the injected shift but also produces five alert days on other retailers. The sustained rule is more selective here, but the thresholds are illustrative and should be calibrated against operational false-positive costs before production use.

## Recommended operational follow-up

1. Start with the flagged Retailer C stores and verify inventory synchronization during evening windows.
2. Audit store-hour accuracy and the early-closure workflow.
3. Review retailer-initiated out-of-stock events against catalog availability and substitution behaviour.
4. Use fixed or sustained-change monitoring alongside rolling monitoring rather than relying on an adaptive threshold alone.
5. Re-measure cancellation, fill-rate, reschedule and timeliness metrics after any intervention.

## Verify the numbers

From a clean clone:

```bash
python -m pip install -r requirements.txt
python scripts/generate_simulated_data.py
python scripts/build_analysis_outputs.py
python scripts/check_outputs.py
```

The raw 100,000-row CSV is deterministic from **seed 42** and intentionally excluded from Git. The committed lightweight outputs are regenerated by the analysis script. `check_outputs.py` recomputes the headline metrics and fails loudly if they do not match the generated outputs.

## Repository structure

- `index.html` — published editorial case study
- `scripts/generate_simulated_data.py` — deterministic simulation, seed 42
- `scripts/build_analysis_outputs.py` — analytical outputs, uncertainty, root-cause, store and monitoring analysis
- `scripts/check_outputs.py` — headline-number verification
- `sql/analysis_queries.sql` — SQL equivalents for the main diagnostics
- `data/` — lightweight committed analytical outputs
- `tableau_ready/` — tidy exports and Tableau Public build guidance
- `requirements.txt` — pinned Python dependencies

## Limitations

- All data is simulated, and the September Retailer C deterioration is intentionally injected.
- The project is independent and uses no proprietary marketplace data.
- The analysis is descriptive and does not establish real-world causal effects.
- Small cells, especially Morning, have wider uncertainty.
- Store ranking is ex-post and can exaggerate the apparent importance of extreme performers.
- The Poisson store flag is an approximation used for prioritization, not a production control limit.
- Monitoring thresholds are illustrative and were not optimized against a real intervention-cost function.
- Peer and own-history baselines answer different counterfactual questions, so both are reported.

## Skills demonstrated

**SQL · Python · Pandas · Operations Analytics · Data Quality · Anomaly Detection · Root-Cause Analysis · Impact Sizing · Statistical Communication · Reproducibility**

## Author

**Felipe Mattos**  
Computer Programming and Analysis — George Brown Polytechnic  
[LinkedIn](https://www.linkedin.com/in/felipervm)

---

Independent portfolio project · Simulated data · Not affiliated with Instacart.
