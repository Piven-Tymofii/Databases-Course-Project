import os, json, glob, re
from altair import value
import mysql.connector
from datetime import datetime
from decimal import Decimal, InvalidOperation


# --- CONFIG ---
DB_CONFIG = {
  "host": "localhost",
  "port": 3306,
  "user": "root",
  "password": "0000timP;",
  "database": "numismatics_simple",
  "charset": "utf8mb4"
}
INPUT_DIR = "numista_data"   # directory containing JSON files
BATCH_COMMIT = 100
MAX_VALUE_NUMERIC = Decimal('99999999.999999')   # matches DECIMAL(14,6) max

# --- HELPERS ---
def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def upsert_issuer(cur, api_code, name, wikidata):
    cur.execute("""
      INSERT INTO issuers (api_code, name, wikidata_id)
      VALUES (%s,%s,%s)
      ON DUPLICATE KEY UPDATE name=VALUES(name), wikidata_id=VALUES(wikidata_id)
    """, (api_code, name, wikidata))
    cur.execute("SELECT id FROM issuers WHERE api_code=%s", (api_code,))
    return cur.fetchone()[0]

def upsert_mint(cur, api_mint_id, name):
    if api_mint_id is None and not name:
        return None
    cur.execute("""
      INSERT INTO mints (api_mint_id, name)
      VALUES (%s,%s)
      ON DUPLICATE KEY UPDATE name=VALUES(name)
    """, (api_mint_id, name))
    cur.execute("SELECT id FROM mints WHERE api_mint_id=%s OR name=%s LIMIT 1", (api_mint_id, name))
    row = cur.fetchone()
    return row[0] if row else None

def parse_demonetization_date(raw):
    """
    Accepts raw string (e.g. "1747-00-00", "1978-01-01", None, "")
    Returns (demonetization_date_for_db, demonetization_year_for_db)
      - demonetization_date_for_db: a Python date string 'YYYY-MM-DD' or None
      - demonetization_year_for_db: an int year or None
    """
    if not raw:
        return None, None
    raw = str(raw).strip()
    if raw in ("", "null", "None"):
        return None, None

    # Try full ISO date (YYYY-MM-DD or with optional time)
    # Accept also "1978-01-01T00:00:00" forms.
    m_full = re.match(r"^(-?\d{1,4})-(\d{2})-(\d{2})", raw)
    if m_full:
        year_s, mon_s, day_s = m_full.group(1), m_full.group(2), m_full.group(3)
        try:
            year = int(year_s)
        except:
            year = None

        # If month/day are zeros -> treat as year-only
        if mon_s == "00" or day_s == "00":
            return None, year
        # Try to build a valid date string for DB
        try:
            # Normalize to YYYY-MM-DD (MySQL DATE compatible)
            # datetime won't accept year <= 0, so guard:
            if year is not None and 1 <= year <= 9999:
                dt = datetime.strptime(f"{year_s}-{mon_s}-{day_s}", "%Y-%m-%d").date()
                return dt.isoformat(), year
            else:
                # year out of range for datetime (very old/BC) -> store only year if present
                return None, year
        except Exception:
            # if parsing fails, just store year if present
            return None, year

    # Fallback: try to extract year only (first signed/unsigned number)
    m_year = re.search(r"(-?\d{1,4})", raw)
    if m_year:
        try:
            return None, int(m_year.group(1))
        except:
            return None, None

    return None, None


def upsert_coin(cur, api_id, data, issuer_db_id):
    # map fields defensively
    url = data.get("url")
    title = data.get("title")
    category = data.get("category")
    min_year = data.get("min_year")
    max_year = data.get("max_year")
    value = data.get("value") or {}
    value_text = value.get("text")
    value_numeric = value.get("numeric_value")
    value_numeric_raw = value.get("numeric_value")
    value_numeric_db = None
    if value_numeric_raw is not None:
        try:
            # convert to Decimal via string to avoid float surprises
            val = Decimal(str(value_numeric_raw))
            # check range
            if abs(val) <= MAX_VALUE_NUMERIC:
                # optionally quantize to 6 decimal places if you want:
                # val = val.quantize(Decimal('0.000001'))
                value_numeric_db = val
            else:
                # out of range: set NULL in DB and log
                print(f"[WARN] numeric_value out of range for api_id={api_id}: {value_numeric_raw}")
                value_numeric_db = None
        except (InvalidOperation, ValueError) as e:
            # not a valid decimal: log and set NULL
            print(f"[WARN] could not parse numeric_value for api_id={api_id}: {value_numeric_raw} ({e})")
            value_numeric_db = None
    else:
        value_numeric_db = None
    currency_name = (value.get("currency") or {}).get("name")
    weight = data.get("weight")
    size = data.get("size")
    thickness = data.get("thickness")
    shape = data.get("shape")
    composition = (data.get("composition") or {}).get("text")
    technique = (data.get("technique") or {}).get("text")
    orientation = data.get("orientation")
    demon = data.get("demonetization") or {}
    demonetized = 1 if demon.get("is_demonetized") else 0
    demon_raw = demon.get("demonetization_date")
    demon_date_db, demon_year_db = parse_demonetization_date(demon_raw)

    obv = (data.get("obverse") or {}).get("picture")
    rev = (data.get("reverse") or {}).get("picture")
    comments = data.get("comments")
    tags = ",".join(data.get("tags") or [])
    raw_json = json.dumps(data, ensure_ascii=False)

    sql = """
      INSERT INTO coins
        (api_id, url, title, category, issuer_id, min_year, max_year,
         value_text, value_numeric, currency_name,
         weight, size, thickness, shape, composition, technique,
         orientation, demonetized, demonetization_date, demonetization_year,
         obverse_picture, reverse_picture, comments, tags, raw_json)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      ON DUPLICATE KEY UPDATE
        url=VALUES(url), title=VALUES(title), category=VALUES(category),
        issuer_id=VALUES(issuer_id), min_year=VALUES(min_year), max_year=VALUES(max_year),
        value_text=VALUES(value_text), value_numeric=VALUES(value_numeric),
        currency_name=VALUES(currency_name), weight=VALUES(weight), size=VALUES(size),
        thickness=VALUES(thickness), shape=VALUES(shape), composition=VALUES(composition),
        technique=VALUES(technique), orientation=VALUES(orientation),
        demonetized=VALUES(demonetized),
        demonetization_date=VALUES(demonetization_date),
        demonetization_year=VALUES(demonetization_year),
        obverse_picture=VALUES(obverse_picture), reverse_picture=VALUES(reverse_picture),
        comments=VALUES(comments), tags=VALUES(tags), raw_json=VALUES(raw_json)
    """

    params = (
        api_id, url, title, category, issuer_db_id, min_year, max_year,
        value_text, value_numeric_db, currency_name,
        weight, size, thickness, shape, composition, technique,
        orientation, demonetized, demon_date_db, demon_year_db,
        obv, rev, comments, tags, raw_json
    )

    # Sanity-check: number of %s placeholders vs number of params
    placeholder_count = sql.count("%s")
    if placeholder_count != len(params):
        # helpful debug output before raising
        print("PLACEHOLDER MISMATCH for api_id:", api_id)
        print("placeholders in SQL:", placeholder_count)
        print("len(params):", len(params))
        raise RuntimeError("SQL placeholders do not match number of parameters. Check the INSERT statement.")

    cur.execute(sql, params)
    cur.execute("SELECT id FROM coins WHERE api_id=%s", (api_id,))
    row = cur.fetchone()
    return row[0] if row else None

def insert_coin_mint(cur, coin_db_id, mint_db_id):
    if not mint_db_id:
        return
    cur.execute("INSERT IGNORE INTO coin_mints (coin_id, mint_id) VALUES (%s,%s)", (coin_db_id, mint_db_id))

def load_files():
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "type_*.json")))
    print("Found", len(files), "files.")
    cnx = get_conn()
    cur = cnx.cursor()
    processed = 0
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        api_id = data.get("id")
        issuer = data.get("issuer") or {}
        issuer_code = issuer.get("code")
        issuer_name = issuer.get("name")
        issuer_wd = issuer.get("wikidata_id")
        issuer_db_id = None
        if issuer_code and issuer_name:
            issuer_db_id = upsert_issuer(cur, issuer_code, issuer_name, issuer_wd)

        coin_db_id = upsert_coin(cur, api_id, data, issuer_db_id)

        # mints (array)
        for m in data.get("mints", []):
            mint_api_id = m.get("id")
            mint_name = m.get("name")
            mint_db_id = upsert_mint(cur, mint_api_id, mint_name)
            insert_coin_mint(cur, coin_db_id, mint_db_id)

        processed += 1
        if processed % BATCH_COMMIT == 0:
            cnx.commit()
            print("Committed", processed, "records.")
    cnx.commit()
    cur.close()
    cnx.close()
    print("Done. Processed", processed, "files.")

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

if __name__ == "__main__":
    load_files()
