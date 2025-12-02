"""
Multi-strategy Numista fetcher (robust & diverse sampling)
- Put your API key into API_KEY
- It will collect a pool of unique type IDs using year/q/issuer searches,
  then fetch detailed /types/{id} JSON for as many as budget allows.
- Respects MAX_REQUESTS budget and uses a small delay between requests.
"""

import os
import time
import json
import random
import requests

# ------------- CONFIG -------------
API_KEY = "NN1OXlKwAsw2t5aoFw3hNcLOOzqabYPYge7cAuIT"
MAX_REQUESTS = 2000
OUTPUT_DIR = "numista_data"
REQUEST_DELAY = 0.35          # polite delay between calls (seconds)
TARGET_DETAIL_COUNT = 1800    # how many full /types/{id} details we'd like to attempt
MAX_LIST_CALLS = 350          # max number of list (search) calls we will perform
LIST_PAGE_LIMIT = 100         # number of items per page (max 100)
# ----------------------------------

BASE = "https://api.numista.com/api/v3"
HEADERS = {"Numista-API-Key": API_KEY, "Accept": "application/json"}

os.makedirs(OUTPUT_DIR, exist_ok=True)

request_count = 0
REQUEST_DELAY = 0.35
MAX_RETRY = 6

def api_get(path, params=None):
    """GET with Retry-After handling, exponential backoff + jitter, and limited retries."""
    global request_count
    url = BASE + path
    attempt = 0
    while True:
        if request_count >= MAX_REQUESTS:
            raise RuntimeError("Request budget exhausted")
        try:
            time.sleep(REQUEST_DELAY)   # polite spacing
            r = requests.get(url, headers=HEADERS, params=params, timeout=30)
            request_count += 1
        except requests.RequestException as e:
            attempt += 1
            if attempt > MAX_RETRY:
                print("Network error (giving up):", e)
                return None, None
            backoff = min(60, 2 ** attempt) + random.random()
            print(f"Network error, sleeping {backoff:.1f}s then retrying...")
            time.sleep(backoff)
            continue

        if r.status_code == 200:
            try:
                return 200, r.json()
            except ValueError:
                return 200, None

        if r.status_code == 429:
            # prefer server-provided hint
            retry_after = r.headers.get("Retry-After")
            if retry_after:
                try:
                    ra = int(retry_after)
                except:
                    try:
                        ra = float(retry_after)
                    except:
                        ra = None
                if ra:
                    sleep_for = ra + random.uniform(0.5, 2.0)
                    print(f"[429] Server asked to retry after {ra}s — sleeping {sleep_for:.1f}s")
                    time.sleep(sleep_for)
                    attempt = 0
                    continue
            # fallback exponential backoff with jitter
            attempt += 1
            if attempt > MAX_RETRY:
                print("[429] Too many retries, skipping this call.")
                return r.status_code, None
            backoff = min(120, (2 ** attempt)) + random.uniform(0.5, 2.0)
            print(f"[429] Rate limited. Backing off for {backoff:.1f}s (attempt {attempt}/{MAX_RETRY})")
            time.sleep(backoff)
            continue

        if 500 <= r.status_code < 600:
            attempt += 1
            if attempt > MAX_RETRY:
                print(f"[{r.status_code}] Server error, giving up.")
                return r.status_code, None
            backoff = min(60, 2 ** attempt) + random.random()
            print(f"[{r.status_code}] Server error — sleeping {backoff:.1f}s then retrying...")
            time.sleep(backoff)
            continue

        # any other client error, return with code so caller can decide
        return r.status_code, None


def safe_types_list(resp):
    """Return the list of type objects from common response shapes."""
    if not resp:
        return []
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for k in ("types", "data", "results", "items"):
            if k in resp and isinstance(resp[k], list):
                return resp[k]
    return []

def extract_type_id(tobj):
    """Return numeric type id from a type object (looks for 'id')."""
    if not isinstance(tobj, dict):
        return None
    tid = tobj.get("id") or tobj.get("type_id") or tobj.get("typeId")
    if isinstance(tid, int):
        return tid
    try:
        return int(tid)
    except Exception:
        return None

def fetch_issuers_codes():
    """Fetch issuers and return list of 'code' strings (useful for issuer-based queries)."""
    status, data = api_get("/issuers", params={"lang":"en", "limit":100})
    if status != 200 or not data:
        return []
    issuers = data.get("issuers") if isinstance(data, dict) else data
    codes = [i.get("code") for i in issuers if isinstance(i, dict) and i.get("code")]
    return codes

def sample_list_calls(issuer_codes):
    """
    Sample /types using multiple strategies:
      - years (recent and historical)
      - q (search terms and single letters)
      - issuer (issuer codes)
    Returns a set of collected type IDs.
    """
    type_ids = set()
    list_calls = 0
    consecutive_no_new = 0

    # prepare search pools
    years = [2024, 2023, 2020, 2010, 2000, 1990, 1980, 1970, 1950, 1900, 1800, 1600, 100, 0]
    q_keywords = ["eagle","king","queen","cent","dollar","franc","penny","crown","sovereign",
                  "rupee","dinar","lei","lira","real","centavo","rand","yen","won","shilling",
                  "imperial","empire","republic"]
    letters = list("abcdefghijklmnopqrstuvwxyz")
    search_pool = []

    # build a pool of candidate queries (mix of strategies)
    for y in years:
        search_pool.append(("year", y))
    for kw in q_keywords:
        search_pool.append(("q", kw))
    for ch in letters:
        search_pool.append(("q", ch))
    # incorporate some issuer codes if available
    if issuer_codes:
        # sample a subset to avoid too many issuer calls
        sample_issuers = random.sample(issuer_codes, min(len(issuer_codes), 200))
        for c in sample_issuers:
            search_pool.append(("issuer", c))

    random.shuffle(search_pool)

    while list_calls < MAX_LIST_CALLS and request_count < MAX_REQUESTS and search_pool:
        strat, value = search_pool.pop(0)
        params = {"lang":"en", "limit": LIST_PAGE_LIMIT, "page": 1}

        if strat == "year":
            params["year"] = value
        elif strat == "q":
            params["q"] = value
        elif strat == "issuer":
            # We try 'issuer' param with the issuer code (API sometimes accepts string codes)
            params["issuer"] = value
        else:
            continue

        status, resp1 = api_get("/types", params=params)
        list_calls += 1
        if status != 200 or not resp1:
            # skip if call failed
            continue

        types_page = safe_types_list(resp1)
        total = resp1.get("count") if isinstance(resp1, dict) else len(types_page)
        if not total:
            continue
        pages = max(1, (int(total) + LIST_PAGE_LIMIT - 1) // LIST_PAGE_LIMIT)
        # choose a random page in range to increase diversity
        page = random.randint(1, pages)

        # fetch that random page
        params["page"] = page
        status, resp2 = api_get("/types", params=params)
        list_calls += 1
        if status != 200 or not resp2:
            continue

        types_list = safe_types_list(resp2)
        before = len(type_ids)
        for t in types_list:
            tid = extract_type_id(t)
            if tid:
                type_ids.add(tid)
        after = len(type_ids)

        if after == before:
            consecutive_no_new += 1
        else:
            consecutive_no_new = 0

        if list_calls % 10 == 0 or after % 200 == 0:
            print(f"[list] calls={list_calls}, collected type_ids={after}, requests_used={request_count}")

        # break early if many searches produce nothing
        if consecutive_no_new > 40 and list_calls > 40:
            print("[list] many consecutive queries produced no new ids — stopping sampling early")
            break

    # fallback: sample global /types pages if still small pool
    if len(type_ids) < 200 and request_count < MAX_REQUESTS:
        print("[fallback] sampling global /types pages")
        for pg in range(1, 21):
            if request_count >= MAX_REQUESTS:
                break
            status, resp = api_get("/types", params={"lang":"en", "limit":LIST_PAGE_LIMIT, "page":pg})
            if status != 200 or not resp:
                continue
            for t in safe_types_list(resp):
                tid = extract_type_id(t)
                if tid:
                    type_ids.add(tid)
            print(f"[fallback] page {pg} -> pool {len(type_ids)}")
            if len(type_ids) > 1000:
                break

    return type_ids

def fetch_and_save_details(type_ids):
    """Fetch /types/{id} JSON for each id until budget or target reached, save to disk."""
    saved = 0
    ids = list(type_ids)
    random.shuffle(ids)
    remaining_budget = MAX_REQUESTS - request_count - 2
    to_fetch = min(len(ids), remaining_budget, TARGET_DETAIL_COUNT)

    print(f"[detail] will fetch up to {to_fetch} details (requests used so far: {request_count})")
    for i, tid in enumerate(ids[:to_fetch], start=1):
        status, resp = api_get(f"/types/{tid}", params={"lang":"en"})
        if status == 200 and resp:
            fname = os.path.join(OUTPUT_DIR, f"type_{tid}.json")
            try:
                with open(fname, "w", encoding="utf-8") as fh:
                    json.dump(resp, fh, indent=2, ensure_ascii=False)
                saved += 1
            except Exception as e:
                print("Error saving", tid, e)
        if i % 20 == 0:
            print(f"[detail] processed {i}/{to_fetch} detail calls — saved {saved} — requests_used={request_count}")

    print("[detail] finished. saved:", saved, "requests_used:", request_count)
    return saved

def main():
    print("Starting multi-strategy fetcher. MAX_REQUESTS =", MAX_REQUESTS)
    # fetch issuer codes (best-effort)
    try:
        issuer_codes = fetch_issuers_codes()
        print("Issuer codes found:", len(issuer_codes))
    except Exception as e:
        print("Could not fetch issuers (continuing without issuer sampling):", e)
        issuer_codes = []

    # sample list calls to build pool of type IDs
    type_ids = sample_list_calls(issuer_codes)
    print("Unique type_ids collected:", len(type_ids))

    if not type_ids:
        print("No type IDs collected. Try running a single manual query (year or q) and paste the /types result for troubleshooting.")
        return
    # build set of already-saved type ids
    saved_ids = set()
    for fname in os.listdir(OUTPUT_DIR):
        if fname.startswith("type_") and fname.endswith(".json"):
            try:
                saved_ids.add(int(fname.split("_",1)[1].split(".")[0]))
            except:
                pass

    # filter type_ids to only the ones we still need
    pending_ids = [tid for tid in type_ids if tid not in saved_ids]
    random.shuffle(pending_ids)
    print(f"{len(saved_ids)} already saved, {len(pending_ids)} pending to fetch.")

    # fetch details for collected ids
    saved = fetch_and_save_details(pending_ids)
    print("Done. JSON files saved in:", OUTPUT_DIR)
    print("Total saved:", saved)

if __name__ == "__main__":
    main()
