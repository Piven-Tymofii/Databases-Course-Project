CREATE DATABASE IF NOT EXISTS numismatics_simple
  DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
USE numismatics_simple;

-- 1) Issuers (countries)
CREATE TABLE issuers (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  api_code VARCHAR(100) NOT NULL,        -- e.g. "barbade"
  name VARCHAR(200) NOT NULL,
  wikidata_id VARCHAR(64) DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_issuers_api_code (api_code),
  INDEX idx_issuers_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Mints 
CREATE TABLE mints (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  api_mint_id VARCHAR(64) DEFAULT NULL, -- string in samples
  name VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_mints_api_mint_id (api_mint_id),
  INDEX idx_mints_name (name(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3) Coins (main table; stores most fields + raw JSON)
CREATE TABLE coins (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  api_id INT UNSIGNED NOT NULL,          -- original Numista id
  url VARCHAR(512),
  title VARCHAR(512),
  category VARCHAR(100),
  issuer_id INT UNSIGNED DEFAULT NULL,   -- FK -> issuers.id
  min_year SMALLINT DEFAULT NULL,
  max_year SMALLINT DEFAULT NULL,
  value_text VARCHAR(255),
  value_numeric DECIMAL(14,6) DEFAULT NULL,
  currency_name VARCHAR(200) DEFAULT NULL,
  weight DECIMAL(10,4) DEFAULT NULL,
  size DECIMAL(8,2) DEFAULT NULL,
  thickness DECIMAL(8,2) DEFAULT NULL,
  shape VARCHAR(80) DEFAULT NULL,
  composition VARCHAR(255) DEFAULT NULL,
  technique VARCHAR(255) DEFAULT NULL,
  orientation VARCHAR(50) DEFAULT NULL,
  demonetized TINYINT(1) DEFAULT 0,
  demonetization_date DATE DEFAULT NULL,
  obverse_picture VARCHAR(512) DEFAULT NULL,
  reverse_picture VARCHAR(512) DEFAULT NULL,
  comments MEDIUMTEXT,
  tags TEXT,                             -- comma-separated tags (simple)
  raw_json JSON,                         -- full source JSON for later needs
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_coins_api_id (api_id),
  INDEX idx_coins_title (title(200)),
  INDEX idx_coins_issuer (issuer_id),
  INDEX idx_coins_years (min_year, max_year),
  FOREIGN KEY (issuer_id) REFERENCES issuers(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4) Junction table: coin_mints (many-to-many: coins <-> mints)
CREATE TABLE coin_mints (
  coin_id INT UNSIGNED NOT NULL,
  mint_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (coin_id, mint_id),
  INDEX idx_coin_mints_mint (mint_id),
  FOREIGN KEY (coin_id) REFERENCES coins(id) ON DELETE CASCADE,
  FOREIGN KEY (mint_id) REFERENCES mints(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5) Related types (simple self-relation by API id)
CREATE TABLE related_types (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  coin_id INT UNSIGNED NOT NULL,        -- local coin PK
  related_api_id INT UNSIGNED NOT NULL, -- API id of related type
  note VARCHAR(255) DEFAULT NULL,
  INDEX idx_related_coin (coin_id),
  INDEX idx_related_api (related_api_id),
  FOREIGN KEY (coin_id) REFERENCES coins(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


USE numismatics_simple;

ALTER TABLE coins
  ADD COLUMN demonetization_year SMALLINT NULL AFTER demonetization_date;