import logging
import requests
import psycopg2
from psycopg2.extras import Json
from tqdm import tqdm
from colorama import Fore, Style, init
from datetime import datetime

# init colorama
init(autoreset=True)

# --------------------
# LOGGING CONFIG
# --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log_info(msg):
    logging.info(Fore.GREEN + msg + Style.RESET_ALL)

def log_warn(msg):
    logging.warning(Fore.YELLOW + msg + Style.RESET_ALL)

def log_error(msg):
    logging.error(Fore.RED + msg + Style.RESET_ALL)

# --------------------
# DATABASE CONFIG
# --------------------
DB_CONFIG = {
    "dbname": "zhancare_db",
    "user": "zhancare",
    "password": "4HPzQt2HyU",
    "host": "localhost",
    "port": 5432,
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.contrib.gis.db.backends.postgis',
#         'NAME': 'zhancare_db',
#         'USER': 'zhancare',
#         'PASSWORD': '4HPzQt2HyU',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# --------------------
# API CONFIG
# --------------------
API_URL = "https://nrchd.kz/api/clinical-protocols"
FOLDER = "Клинические протоколы/Поток клинические протоколы"

# --------------------
# SQL (UPSERT)
# --------------------
INSERT_SQL = """
INSERT INTO clinical_protocols (
    name,
    url,
    year,
    medicine,
    mkb,
    mkb_codes,
    size,
    extension,
    modified,
    created_at,
    updated_at
)
VALUES (
    %(name)s,
    %(url)s,
    %(year)s,
    %(medicine)s,
    %(mkb)s,
    %(mkb_codes)s,
    %(size)s,
    %(extension)s,
    %(modified)s,
    NOW(),
    NOW()
)
ON CONFLICT (url)
DO UPDATE SET
    name = EXCLUDED.name,
    year = EXCLUDED.year,
    medicine = EXCLUDED.medicine,
    mkb = EXCLUDED.mkb,
    mkb_codes = EXCLUDED.mkb_codes,
    size = EXCLUDED.size,
    extension = EXCLUDED.extension,
    modified = EXCLUDED.modified,
    updated_at = NOW();
"""

# --------------------
# MAIN
# --------------------
def main():
    log_info("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    log_info("Fetching data from NRCHD API...")
    response = requests.get(API_URL, params={"folder": FOLDER}, timeout=30)
    response.raise_for_status()
    documents = response.json().get("documents", [])

    log_info(f"Documents received: {len(documents)}")

    inserted = 0
    updated = 0

    try:
        for doc in tqdm(documents, desc="Importing protocols", unit="doc"):
            payload = {
                "name": doc["name"],
                "url": doc["url"],
                "year": int(doc["year"]),
                "medicine": doc["medicine"],
                "mkb": doc["mkb"],
                "mkb_codes": Json(doc.get("mkb_codes", [])),
                "size": doc["size"],
                "extension": doc["extension"],
                "modified": datetime.fromisoformat(doc["modified"]),
            }

            cur.execute(INSERT_SQL, payload)

            if cur.rowcount == 1:
                inserted += 1
            else:
                updated += 1

        conn.commit()
        log_info(f"Import finished: inserted={inserted}, updated={updated}")

    except Exception as e:
        conn.rollback()
        log_error(f"Import failed: {e}")
        raise

    finally:
        cur.close()
        conn.close()
        log_info("Database connection closed.")

# --------------------
# ENTRY POINT
# --------------------
if __name__ == "__main__":
    main()
