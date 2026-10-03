-- Marketplace Fulfillment Quality Diagnostic
-- All order-level data is simulated. A Retailer C deterioration is intentionally injected.
-- PostgreSQL-style SQL. Rates are descriptive; the simulation is not evidence about any real company.

-- 1. Retailer C monthly cancellation rate with 95% Wilson interval.
WITH monthly AS (
  SELECT
    DATE_TRUNC('month', order_date) AS month,
    COUNT(*)::numeric AS orders,
    SUM(cancelled)::numeric AS cancellations
  FROM simulated_fulfillment_orders
  WHERE retailer = 'Retailer C'
  GROUP BY 1
),
p AS (
  SELECT *, cancellations / orders AS rate
  FROM monthly
)
SELECT
  month, orders, cancellations, rate * 100 AS rate_pct,
  (
    (rate + 1.96^2/(2*orders)) / (1 + 1.96^2/orders)
    - 1.96 * SQRT(rate*(1-rate)/orders + 1.96^2/(4*orders^2))
      / (1 + 1.96^2/orders)
  ) * 100 AS ci_low_pct,
  (
    (rate + 1.96^2/(2*orders)) / (1 + 1.96^2/orders)
    + 1.96 * SQRT(rate*(1-rate)/orders + 1.96^2/(4*orders^2))
      / (1 + 1.96^2/orders)
  ) * 100 AS ci_high_pct
FROM p
ORDER BY month;


-- 2. September impact sizing using two baselines.
WITH target AS (
  SELECT COUNT(*)::numeric AS orders,
         SUM(cancelled)::numeric AS cancellations,
         AVG(cancelled::numeric) AS rate
  FROM simulated_fulfillment_orders
  WHERE retailer = 'Retailer C' AND order_date >= DATE '2026-09-01'
),
own_pre AS (
  SELECT AVG(cancelled::numeric) AS rate
  FROM simulated_fulfillment_orders
  WHERE retailer = 'Retailer C' AND order_date < DATE '2026-09-01'
),
peers AS (
  SELECT AVG(cancelled::numeric) AS rate
  FROM simulated_fulfillment_orders
  WHERE retailer <> 'Retailer C' AND order_date >= DATE '2026-09-01'
)
SELECT 'Retailer C Jul-Aug' AS baseline,
       own_pre.rate * 100 AS baseline_rate_pct,
       target.orders * own_pre.rate AS expected_cancellations,
       target.cancellations,
       target.cancellations - target.orders * own_pre.rate AS excess_cancellations
FROM target CROSS JOIN own_pre
UNION ALL
SELECT 'September peers excluding Retailer C',
       peers.rate * 100,
       target.orders * peers.rate,
       target.cancellations,
       target.cancellations - target.orders * peers.rate
FROM target CROSS JOIN peers;


-- 3. Root-cause change by reason: Jul-Aug vs September.
WITH periods AS (
  SELECT
    CASE WHEN order_date < DATE '2026-09-01' THEN 'jul_aug' ELSE 'sep' END AS period,
    cancellation_reason,
    COUNT(*) FILTER (WHERE cancelled = 1)::numeric AS cancellations
  FROM simulated_fulfillment_orders
  WHERE retailer = 'Retailer C'
  GROUP BY 1,2
),
orders AS (
  SELECT
    COUNT(*) FILTER (WHERE retailer='Retailer C' AND order_date < DATE '2026-09-01')::numeric AS pre_orders,
    COUNT(*) FILTER (WHERE retailer='Retailer C' AND order_date >= DATE '2026-09-01')::numeric AS sep_orders
  FROM simulated_fulfillment_orders
),
wide AS (
  SELECT cancellation_reason,
         COALESCE(MAX(cancellations) FILTER (WHERE period='jul_aug'),0) AS pre_cancels,
         COALESCE(MAX(cancellations) FILTER (WHERE period='sep'),0) AS sep_cancels
  FROM periods
  GROUP BY 1
),
calc AS (
  SELECT w.*, o.*,
         pre_cancels/pre_orders*1000 AS pre_per_1000,
         sep_cancels/sep_orders*1000 AS sep_per_1000
  FROM wide w CROSS JOIN orders o
)
SELECT *,
       sep_per_1000-pre_per_1000 AS change_per_1000,
       (sep_per_1000-pre_per_1000)/1000*sep_orders AS implied_excess_cancellations
FROM calc
ORDER BY implied_excess_cancellations DESC;


-- 4. Root-cause change by cancellation type.
-- Same calculation as query 3, using cancellation_type instead of cancellation_reason.
WITH periods AS (
  SELECT
    CASE WHEN order_date < DATE '2026-09-01' THEN 'jul_aug' ELSE 'sep' END AS period,
    cancellation_type,
    COUNT(*) FILTER (WHERE cancelled = 1)::numeric AS cancellations
  FROM simulated_fulfillment_orders
  WHERE retailer = 'Retailer C'
  GROUP BY 1,2
),
orders AS (
  SELECT
    COUNT(*) FILTER (WHERE retailer='Retailer C' AND order_date < DATE '2026-09-01')::numeric AS pre_orders,
    COUNT(*) FILTER (WHERE retailer='Retailer C' AND order_date >= DATE '2026-09-01')::numeric AS sep_orders
  FROM simulated_fulfillment_orders
),
wide AS (
  SELECT cancellation_type,
         COALESCE(MAX(cancellations) FILTER (WHERE period='jul_aug'),0) AS pre_cancels,
         COALESCE(MAX(cancellations) FILTER (WHERE period='sep'),0) AS sep_cancels
  FROM periods
  GROUP BY 1
),
calc AS (
  SELECT w.*, o.*,
         pre_cancels/pre_orders*1000 AS pre_per_1000,
         sep_cancels/sep_orders*1000 AS sep_per_1000
  FROM wide w CROSS JOIN orders o
)
SELECT *,
       sep_per_1000-pre_per_1000 AS change_per_1000,
       (sep_per_1000-pre_per_1000)/1000*sep_orders AS implied_excess_cancellations
FROM calc
ORDER BY implied_excess_cancellations DESC;


-- 5. Retailer C September daypart rates.
SELECT
  daypart,
  COUNT(*) AS orders,
  SUM(cancelled) AS cancellations,
  AVG(cancelled::numeric) * 100 AS cancellation_rate_pct
FROM simulated_fulfillment_orders
WHERE retailer='Retailer C' AND order_date >= DATE '2026-09-01'
GROUP BY daypart
ORDER BY CASE daypart WHEN 'Morning' THEN 1 WHEN 'Afternoon' THEN 2 ELSE 3 END;


-- 6. Daypart-adjusted September store excess using Retailer C Jul-Aug rates.
WITH pre_rates AS (
  SELECT daypart, AVG(cancelled::numeric) AS baseline_rate
  FROM simulated_fulfillment_orders
  WHERE retailer='Retailer C' AND order_date < DATE '2026-09-01'
  GROUP BY daypart
),
store_daypart AS (
  SELECT store_id, daypart,
         COUNT(*)::numeric AS orders,
         SUM(cancelled)::numeric AS cancellations
  FROM simulated_fulfillment_orders
  WHERE retailer='Retailer C' AND order_date >= DATE '2026-09-01'
  GROUP BY store_id, daypart
),
stores AS (
  SELECT s.store_id,
         SUM(s.orders) AS orders,
         SUM(s.cancellations) AS cancellations,
         SUM(s.orders * p.baseline_rate) AS expected_cancellations
  FROM store_daypart s
  JOIN pre_rates p USING (daypart)
  GROUP BY s.store_id
)
SELECT *,
       cancellations-expected_cancellations AS adjusted_excess_cancellations,
       (cancellations-expected_cancellations)/NULLIF(SQRT(expected_cancellations),0) AS poisson_z,
       CASE WHEN (cancellations-expected_cancellations)/NULLIF(SQRT(expected_cancellations),0) >= 3
            THEN 1 ELSE 0 END AS flagged_z_ge_3
FROM stores
ORDER BY adjusted_excess_cancellations DESC;


-- 7. Monitoring rules.
-- Evaluation window: September 1-30, 2026. Minimum daily volume: 100 orders.
-- Legacy: current daily rate >= 2 SD above mean of the PRIOR 14 complete daily rates.
-- Fixed: current daily rate >= 2 SD above retailer-specific Jul-Aug daily mean.
-- Sustained: three consecutive eligible days above fixed Jul-Aug mean + 1 SD.
WITH daily AS (
  SELECT order_date, retailer,
         COUNT(*) AS orders,
         AVG(cancelled::numeric) AS cancellation_rate
  FROM simulated_fulfillment_orders
  GROUP BY order_date, retailer
),
fixed AS (
  SELECT retailer,
         AVG(cancellation_rate) AS baseline_rate,
         STDDEV_SAMP(cancellation_rate) AS baseline_sd
  FROM daily
  WHERE order_date < DATE '2026-09-01'
  GROUP BY retailer
),
scored AS (
  SELECT d.*, f.baseline_rate, f.baseline_sd,
         AVG(d.cancellation_rate) OVER (
           PARTITION BY d.retailer ORDER BY d.order_date
           ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
         ) AS rolling14_mean,
         STDDEV_SAMP(d.cancellation_rate) OVER (
           PARTITION BY d.retailer ORDER BY d.order_date
           ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
         ) AS rolling14_sd,
         COUNT(*) OVER (
           PARTITION BY d.retailer ORDER BY d.order_date
           ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING
         ) AS rolling14_n
  FROM daily d JOIN fixed f USING (retailer)
),
flags AS (
  SELECT *,
    CASE WHEN orders >= 100 AND rolling14_n=14
              AND (cancellation_rate-rolling14_mean)/NULLIF(rolling14_sd,0) >= 2
         THEN 1 ELSE 0 END AS rolling14_alert,
    CASE WHEN orders >= 100
              AND (cancellation_rate-baseline_rate)/NULLIF(baseline_sd,0) >= 2
         THEN 1 ELSE 0 END AS fixed_alert,
    CASE WHEN orders >= 100 AND cancellation_rate > baseline_rate+baseline_sd
         THEN 1 ELSE 0 END AS above_1sd
  FROM scored
),
sustained AS (
  SELECT *,
    CASE WHEN SUM(above_1sd) OVER (
      PARTITION BY retailer ORDER BY order_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) = 3 THEN 1 ELSE 0 END AS sustained_3day_alert
  FROM flags
)
SELECT retailer,
       SUM(rolling14_alert) AS rolling14_alert_days,
       SUM(fixed_alert) AS fixed_alert_days,
       SUM(sustained_3day_alert) AS sustained_alert_days
FROM sustained
WHERE order_date >= DATE '2026-09-01'
GROUP BY retailer
ORDER BY retailer;


-- 8. Province-level quality cut.
SELECT
  province,
  COUNT(*) AS orders,
  AVG(cancelled::numeric)*100 AS cancellation_rate_pct,
  AVG(late_delivery::numeric)*100 AS late_delivery_rate_pct,
  AVG(rescheduled::numeric)*100 AS reschedule_rate_pct
FROM simulated_fulfillment_orders
WHERE order_date >= DATE '2026-09-01'
GROUP BY province
ORDER BY orders DESC;
