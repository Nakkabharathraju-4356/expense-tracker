-- Reusable analytical queries (run in VS Code with the SQLite extension
-- or:  sqlite3 data/expenses.db < sql/analytics_queries.sql)

-- 1. Monthly spend with month-over-month change (window function)
WITH monthly AS (
    SELECT substr(expense_date, 1, 7) AS month, SUM(amount) AS total
    FROM expenses
    GROUP BY month
)
SELECT month,
       ROUND(total, 2)                                         AS total_spend,
       ROUND(total - LAG(total) OVER (ORDER BY month), 2)      AS mom_change,
       ROUND(100.0 * (total - LAG(total) OVER (ORDER BY month))
             / LAG(total) OVER (ORDER BY month), 1)            AS mom_pct
FROM monthly
ORDER BY month;

-- 2. Category share of total spend, ranked
SELECT c.name AS category,
       ROUND(SUM(e.amount), 2) AS total,
       ROUND(100.0 * SUM(e.amount) / (SELECT SUM(amount) FROM expenses), 1) AS pct_of_total,
       RANK() OVER (ORDER BY SUM(e.amount) DESC) AS spend_rank
FROM expenses e
JOIN categories c ON c.id = e.category_id
GROUP BY c.name;

-- 3. Budget vs actual per category and month, with status flag
SELECT b.month,
       c.name                                   AS category,
       b.amount                                 AS budget,
       ROUND(COALESCE(SUM(e.amount), 0), 2)     AS actual,
       ROUND(b.amount - COALESCE(SUM(e.amount), 0), 2) AS remaining,
       CASE WHEN COALESCE(SUM(e.amount), 0) > b.amount THEN 'OVER BUDGET' ELSE 'OK' END AS status
FROM budgets b
JOIN categories c ON c.id = b.category_id
LEFT JOIN expenses e
       ON e.category_id = b.category_id
      AND substr(e.expense_date, 1, 7) = b.month
GROUP BY b.month, c.name, b.amount
ORDER BY b.month, actual DESC;

-- 4. Running (cumulative) spend within each month
SELECT expense_date,
       amount,
       ROUND(SUM(amount) OVER (
             PARTITION BY substr(expense_date, 1, 7)
             ORDER BY expense_date, id), 2) AS month_to_date
FROM expenses
ORDER BY expense_date, id;

-- 5. Savings rate per month (income vs expenses)
WITH i AS (SELECT substr(income_date, 1, 7) AS month, SUM(amount) AS income  FROM income   GROUP BY month),
     e AS (SELECT substr(expense_date, 1, 7) AS month, SUM(amount) AS expense FROM expenses GROUP BY month)
SELECT i.month,
       ROUND(i.income, 2)  AS income,
       ROUND(e.expense, 2) AS expense,
       ROUND(100.0 * (i.income - e.expense) / i.income, 1) AS savings_rate_pct
FROM i JOIN e USING (month)
ORDER BY i.month;

-- 6. Weekend vs weekday spending
SELECT CASE WHEN strftime('%w', expense_date) IN ('0','6') THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       ROUND(AVG(amount), 2) AS avg_transaction,
       COUNT(*)              AS transactions
FROM expenses
GROUP BY day_type;

-- 7. Top 10 largest single expenses
SELECT e.expense_date, c.name AS category, e.amount, e.description
FROM expenses e JOIN categories c ON c.id = e.category_id
ORDER BY e.amount DESC
LIMIT 10;
