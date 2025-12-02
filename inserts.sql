USE numismatics_simple;

-- Multi-row insert: issuers
INSERT INTO issuers (api_code, name, wikidata_id) VALUES
 ('barbade', 'Barbados', 'Q244'),
 ('hong_kong', 'Hong Kong', 'Q8646'),
 ('equateur', 'Ecuador', 'Q736'),
 ('gibraltar', 'Gibraltar', 'Q1481')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Multi-row insert: mints
INSERT INTO mints (api_mint_id, name) VALUES
 ('19','Royal Canadian Mint of Ottawa'),
 ('20','Royal Canadian Mint of Winnipeg'),
 ('17','Royal Mint (Tower Hill)'),
 ('18','Heaton and Sons / The Mint Birmingham'),
 ('26','Pobjoy Mint')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Multi-row insert: coins (minimal columns). Use subselect to resolve issuer_id
INSERT INTO coins (api_id, title, url, category, issuer_id, min_year, max_year, value_text, value_numeric, currency_name, weight, size, shape, composition, technique, orientation, obverse_picture, reverse_picture, comments, tags, raw_json)
VALUES
 (66, '10 Cents', 'https://en.numista.com/66', 'coin', (SELECT id FROM issuers WHERE api_code='barbade'), 1973, 2005, '10 Cents', 0.1, 'Dollar', 2.26, 17.78, 'Round', 'Copper-nickel (75% Copper, 25% Nickel)', 'Milled', 'medal', 'https://en.numista.com/catalogue/photos/barbade/311-original.jpg', 'https://en.numista.com/catalogue/photos/barbade/312-original.jpg', 'Sample comments for 10 Cents', 'Bird,Coat of Arms', JSON_OBJECT('sample','json')),
 (1066, '1 Dollar - Elizabeth II', 'https://en.numista.com/1066', 'coin', (SELECT id FROM issuers WHERE api_code='hong_kong'), 1960, 1970, '1 Dollar', 1.0, 'Dollar', 11.6638, 30, 'Round', 'Copper-nickel', 'Milled', 'medal', 'https://en.numista.com/catalogue/photos/hong_kong/67c43964e404f1-original.jpg', 'https://en.numista.com/catalogue/photos/hong_kong/67c43965a53e81-original.jpg', 'Sample comments for HK 1 Dollar', 'Cat or feline', JSON_OBJECT('sample','json')),
 (34815, '1 Centavo', 'https://en.numista.com/34815', 'coin', (SELECT id FROM issuers WHERE api_code='equateur'), 1872, 1890, '1 Centavo', 0.01, 'Peso', 5.9, 26, 'Round', 'Copper', 'Milled', 'variable', 'https://en.numista.com/catalogue/photos/equateur/286-original.jpg', 'https://en.numista.com/catalogue/photos/equateur/287-original.jpg', 'Sample comments for 1 Centavo', 'Laurel', JSON_OBJECT('sample','json'))
ON DUPLICATE KEY UPDATE title=VALUES(title), min_year=VALUES(min_year), max_year=VALUES(max_year);

-- Multi-row insert into coin_mints (many-to-many)
INSERT IGNORE INTO coin_mints (coin_id, mint_id)
SELECT c.id, m.id FROM coins c JOIN mints m ON m.api_mint_id='19' WHERE c.api_id=66
UNION
SELECT c.id, m.id FROM coins c JOIN mints m ON m.api_mint_id='17' WHERE c.api_id=66
UNION
SELECT c.id, m.id FROM coins c JOIN mints m ON m.api_mint_id='18' WHERE c.api_id=1066;
