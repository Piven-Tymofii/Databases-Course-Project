USE numismatics_simple;

CREATE OR REPLACE VIEW vw_coin_overview AS
SELECT c.id AS coin_pk, c.api_id, c.title, c.min_year, c.max_year,
       i.name AS issuer_name,
       GROUP_CONCAT(DISTINCT m.name SEPARATOR '; ') AS mints,
       c.value_text, c.value_numeric
FROM coins c
LEFT JOIN issuers i ON c.issuer_id = i.id
LEFT JOIN coin_mints cm ON cm.coin_id = c.id
LEFT JOIN mints m ON m.id = cm.mint_id
GROUP BY c.id, c.api_id, c.title, c.min_year, c.max_year, i.name, c.value_text, c.value_numeric;


SELECT * FROM vw_coin_overview LIMIT 50;
