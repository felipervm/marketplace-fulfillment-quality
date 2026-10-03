-- Marketplace Fulfillment Quality Diagnostic
-- All order-level data is simulated.

-- 1. Retailer C monthly trend
SELECT
  DATE_TRUNC('month', order_date) AS month,
  COUNT(*) AS orders,
  AVG(cancelled) * 100 AS cancellation_rate_pct
FROM simulated_fulfillment_orders
WHERE retailer = 'Retailer C'
GROUP BY 1
ORDER BY 1;

-- 2. September peer comparison excluding Retailer C
WITH peer AS (
  SELECT AVG(cancelled) AS peer_cancel_rate
  FROM simulated_fulfillment_orders
  WHERE order_date >= '2026-09-01'
    AND retailer <> 'Retailer C'
),
target AS (
  SELECT COUNT(*) AS orders,
         SUM(cancelled) AS cancellations,
         AVG(cancelled) AS cancellation_rate
  FROM simulated_fulfillment_orders
  WHERE order_date >= '2026-09-01'
    AND retailer = 'Retailer C'
)
SELECT
  t.orders,
  t.cancellations,
  t.cancellation_rate * 100 AS target_rate_pct,
  p.peer_cancel_rate * 100 AS peer_rate_pct,
  t.cancellations - (t.orders * p.peer_cancel_rate) AS excess_cancellations_vs_peers
FROM target t CROSS JOIN peer p;

-- 3. Fixed July-August baseline
WITH daily AS (
  SELECT order_date, retailer, COUNT(*) AS orders, AVG(cancelled) AS cancellation_rate
  FROM simulated_fulfillment_orders
  GROUP BY order_date, retailer
),
pre_period AS (
  SELECT retailer,
         AVG(cancellation_rate) AS baseline_rate,
         STDDEV_SAMP(cancellation_rate) AS baseline_sd
  FROM daily
  WHERE order_date < '2026-09-01'
  GROUP BY retailer
)
SELECT d.*, p.baseline_rate, p.baseline_sd,
       (d.cancellation_rate - p.baseline_rate) / NULLIF(p.baseline_sd,0) AS z_fixed_preperiod,
       CASE WHEN d.orders >= 100
             AND (d.cancellation_rate - p.baseline_rate) / NULLIF(p.baseline_sd,0) >= 2
            THEN 1 ELSE 0 END AS fixed_baseline_alert
FROM daily d JOIN pre_period p USING (retailer)
ORDER BY retailer, order_date;

-- 4. Root cause share
SELECT
  cancellation_reason,
  COUNT(*) AS cancellations,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS share_pct
FROM simulated_fulfillment_orders
WHERE retailer = 'Retailer C'
  AND order_date >= '2026-09-01'
  AND cancelled = 1
GROUP BY cancellation_reason
ORDER BY cancellations DESC;

-- 5. Province-level quality cut
SELECT
  province,
  COUNT(*) AS orders,
  AVG(cancelled)*100 AS cancellation_rate_pct,
  AVG(late_delivery)*100 AS late_delivery_rate_pct,
  AVG(rescheduled)*100 AS reschedule_rate_pct
FROM simulated_fulfillment_orders
WHERE order_date >= '2026-09-01'
GROUP BY province
ORDER BY orders DESC;