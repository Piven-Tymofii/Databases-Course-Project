USE numismatics_simple;

-- 2-table join: coins with issuers
SELECT c.api_id, c.title, i.name AS issuer_name
FROM coins c
INNER JOIN issuers i ON c.issuer_id = i.id
WHERE i.api_code = 'barbade';

-- 3-table join: coins -> coin_mints -> mints (which mints struck a coin)
SELECT c.api_id, c.title, i.name AS issuer, m.name AS mint_name
FROM coins c
LEFT JOIN issuers i ON c.issuer_id = i.id
LEFT JOIN coin_mints cm ON cm.coin_id = c.id
LEFT JOIN mints m ON m.id = cm.mint_id
WHERE c.api_id IN (66, 1066);

-- Right join example: show mints even if they have no coins
SELECT m.name AS mint_name, c.title
FROM mints m
LEFT JOIN coin_mints cm ON cm.mint_id = m.id
LEFT JOIN coins c ON c.id = cm.coin_id
ORDER BY m.name;
