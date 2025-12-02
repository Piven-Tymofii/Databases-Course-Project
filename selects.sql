USE numismatics_simple;

-- A) Aggregation example 1: count coins per issuer, average weight, sum of coins processed
SELECT i.name AS issuer_name,
       COUNT(c.id) AS coin_count,
       AVG(c.weight) AS avg_weight,
       SUM(CASE WHEN c.demonetized = 1 THEN 1 ELSE 0 END) AS demonetized_count
FROM coins c
JOIN issuers i ON c.issuer_id = i.id
GROUP BY i.id, i.name
ORDER BY coin_count DESC
LIMIT 50;

-- B) Aggregation example 2: overall stats (three aggregate functions)
SELECT COUNT(*) AS total_coins,
       AVG(value_numeric) AS avg_value,
       SUM(weight) AS total_weight
FROM coins
WHERE value_numeric IS NOT NULL;

-- C) Pagination example: list coins ordered by min_year with OFFSET / LIMIT
SELECT api_id, title, min_year, max_year
FROM coins
WHERE min_year IS NOT NULL 
AND max_year IS NOT NULL 
AND min_year > 0
AND max_year > 0
ORDER BY min_year ASC, title ASC;

-- D) Grouping by year ranges (example)
SELECT FLOOR(min_year/50)*50 AS decade_group,
       COUNT(*) AS cnt,
       AVG(weight) AS avg_wt
FROM coins
WHERE min_year IS NOT NULL
GROUP BY decade_group
ORDER BY decade_group DESC;
