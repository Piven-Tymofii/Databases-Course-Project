USE numismatics_simple;

-- Update 1: change coin title for a specific api_id
UPDATE coins SET title = '10 Cents (updated edition)' WHERE api_id = 66;

-- Update 2: mark demonetized flag for older coins by year (bulk)
UPDATE coins SET demonetized = 1 WHERE max_year < 1900 AND demonetized = 0;

-- Update 3: add a tag to all Gibraltar coins
UPDATE coins c
JOIN issuers i ON c.issuer_id = i.id
SET c.tags = CONCAT(IFNULL(c.tags, ''), CASE WHEN c.tags IS NULL OR c.tags = '' THEN '' ELSE ',' END, 'Commemorative')
WHERE i.api_code = 'gibraltar';
