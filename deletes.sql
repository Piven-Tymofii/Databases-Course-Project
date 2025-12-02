USE numismatics_simple;

-- Conditional delete: delete a mint by api_mint_id (and cascade references)
DELETE FROM mints WHERE api_mint_id = '1319';

-- Conditional delete: remove coins that are test/dummy entries
DELETE FROM coins WHERE title LIKE 'TEST%';

-- Truncate small lookup table 
TRUNCATE TABLE related_types;
