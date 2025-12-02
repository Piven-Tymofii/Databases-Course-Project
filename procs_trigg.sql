USE numismatics_simple;

-- Stored procedure: mark coins demonetized by year (set demonetized = 1 for coins with max_year <= input)
CREATE PROCEDURE sp_mark_demonetized_by_year(IN yr SMALLINT)
BEGIN
  UPDATE coins
    SET demonetized = 1
    WHERE max_year <= yr;
END;

-- Function: computes coin span (years between max and min), returns INT (NULL if missing)
CREATE FUNCTION fn_coin_span(in_api_id INT) RETURNS INT
DETERMINISTIC
RETURN (
  SELECT CASE WHEN min_year IS NULL OR max_year IS NULL THEN NULL ELSE (max_year - min_year) END
  FROM coins WHERE api_id = in_api_id LIMIT 1
);

-- Audit table for trigger
CREATE TABLE IF NOT EXISTS coin_audit (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  coin_api_id INT,
  action VARCHAR(20),
  action_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  notes TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Trigger: after insert into coins, log to coin_audit
CREATE TRIGGER trg_after_coin_insert
AFTER INSERT ON coins
FOR EACH ROW
BEGIN
  INSERT INTO coin_audit (coin_api_id, action, notes) VALUES (NEW.api_id, 'INSERT', CONCAT('Inserted coin ', NEW.title));
END;


SHOW PROCEDURE STATUS WHERE Db = 'numismatics_simple';
SHOW FUNCTION STATUS WHERE Db = 'numismatics_simple';
-- start a transaction
START TRANSACTION;

-- sample change 1
UPDATE coins SET title = CONCAT(title, ' [TX]') WHERE api_id = 66;
INSERT coins (api_id, title, issuer_id) VALUES (999999, 'Test Coin TX', NULL);

-- sample change 2
INSERT INTO related_types (coin_id, related_api_id, note)
SELECT c.id, 999999, 'test tx' FROM coins c WHERE c.api_id = 66;

-- If everything OK:
COMMIT;

SELECT * FROM coin_audit ORDER BY action_time DESC LIMIT 5;

-- Show audit entries
SELECT * FROM coin_audit ORDER BY action_time DESC LIMIT 20;

-- Use the function
SELECT api_id, title, fn_coin_span(api_id) AS year_span FROM coins ORDER BY year_span DESC LIMIT 10;

-- Call stored procedure (marks coins with max_year <= 1900 as demonetized)
CALL sp_mark_demonetized_by_year(1900);

-- Check the view
SELECT * FROM vw_coin_overview WHERE issuer_name = 'Barbados' LIMIT 10;



