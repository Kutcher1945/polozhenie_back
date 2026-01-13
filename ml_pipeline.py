import json
import psycopg2
import requests
import pdfplumber
import logging
import time
import re
from tqdm import tqdm
from colorama import Fore, Style, init

# =========================================================
# INIT
# =========================================================
init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def info(msg): logging.info(Fore.GREEN + msg + Style.RESET_ALL)
def warn(msg): logging.warning(Fore.YELLOW + msg + Style.RESET_ALL)
def error(msg): logging.error(Fore.RED + msg + Style.RESET_ALL)

# =========================================================
# CONFIG
# =========================================================
PDF_PATH = "HELLP-СИНДРОМ.pdf"
PROTOCOL_ID = 1

DB_CONFIG = {
    "dbname": "core_db",
    "user": "core",
    "password": "4HPzQt2HyU",
    "host": "10.100.200.151",
    "port": 5432,
}

MISTRAL_API_KEY = "QqkMxELY0YVGkCx17Vya04Sq9nGvCahu"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

RATE_LIMIT_SECONDS = 0.6

ALLOWED_TYPES = {
    "definition", "diagnosis", "classification",
    "differential", "treatment", "drugs",
    "algorithm", "complications",
    "indications", "contraindications", "other"
}

# =========================================================
# MISTRAL PROMPT
# =========================================================
SYSTEM_PROMPT = """
You are a medical clinical protocol classifier.

TASK:
Classify the given text block from a clinical protocol.

Choose ONE content_type from:
definition, diagnosis, classification, differential,
treatment, drugs, algorithm, complications,
indications, contraindications, other

RULES:
- DO NOT rewrite text
- DO NOT summarize
- DO NOT add interpretation
- DO NOT hallucinate
- Output ONLY valid JSON
- If unclear or mixed → "other"

OUTPUT:
{
  "content_type": "string",
  "title": "string or empty",
  "confidence": number between 0 and 1
}
"""

# =========================================================
# MISTRAL CALL
# =========================================================
def classify_with_mistral(text):
    payload = {
        "model": "open-mistral-nemo",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text[:6000]}
        ],
        "temperature": 0.0,
        "max_tokens": 200
    }

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        MISTRAL_URL,
        json=payload,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"]

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"content_type": "other", "title": "", "confidence": 0.0}

    if result.get("content_type") not in ALLOWED_TYPES:
        result["content_type"] = "other"

    if float(result.get("confidence", 0)) < 0.6:
        result["content_type"] = "other"

    return result

# =========================================================
# HEADING DETECTION
# =========================================================
HEADING_PATTERNS = [
    r"^[IVX]+\.",                  # I. II. III.
    r"^\d+(\.\d+)*\s",             # 1. 1.1 2.3
    r"^КЛИНИЧЕСКИЙ ПРОТОКОЛ",
    r"^ВВОДНАЯ ЧАСТЬ",
    r"^ДИАГНОСТ",
    r"^КЛАССИФ",
    r"^ЛЕЧЕНИ",
    r"^АЛГОРИТМ",
    r"^ОСЛОЖНЕНИ",
    r"^ПОКАЗАНИ",
    r"^ПРОТИВОПОКАЗАНИ",
]

def is_heading(line):
    if line.isupper() and len(line) < 120:
        return True
    for pattern in HEADING_PATTERNS:
        if re.match(pattern, line, re.IGNORECASE):
            return True
    return False

# =========================================================
# PDF EXTRACTION (CORRECT)
# =========================================================
def extract_pdf_blocks(path):
    blocks = []
    current_lines = []
    page_from = None

    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]

            for line in lines:
                if is_heading(line) and current_lines:
                    blocks.append((
                        page_from,
                        page_num,
                        "\n".join(current_lines)
                    ))
                    current_lines = []
                    page_from = page_num

                if page_from is None:
                    page_from = page_num

                current_lines.append(line)

        if current_lines:
            blocks.append((page_from, page_num, "\n".join(current_lines)))

    return blocks

# =========================================================
# DB INSERT
# =========================================================
def insert_content(cur, protocol_id, result, text, page_from, page_to, order):
    cur.execute("""
        INSERT INTO clinical_protocols_content
        (protocol_id, content_type, title, content,
         page_from, page_to, source, confidence, "order", created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT DO NOTHING
    """, (
        protocol_id,
        result["content_type"],
        result.get("title", ""),
        text,
        page_from,
        page_to,
        "pdf+mistral",
        float(result.get("confidence", 0)),
        order
    ))

# =========================================================
# MAIN
# =========================================================
def main():
    info("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    info("Extracting semantic blocks from PDF...")
    blocks = extract_pdf_blocks(PDF_PATH)
    info(f"Blocks detected: {len(blocks)}")

    try:
        for idx, (p_from, p_to, text) in enumerate(
            tqdm(blocks, desc="Classifying blocks"), start=1
        ):
            info(f"Block {idx}: pages {p_from}-{p_to}")

            result = classify_with_mistral(text)

            insert_content(
                cur,
                PROTOCOL_ID,
                result,
                text,
                p_from,
                p_to,
                idx
            )

            time.sleep(RATE_LIMIT_SECONDS)

        conn.commit()
        info("Ingestion completed successfully")

    except Exception as e:
        conn.rollback()
        error(f"FAILED: {e}")
        raise

    finally:
        cur.close()
        conn.close()
        info("Database connection closed.")

# =========================================================
if __name__ == "__main__":
    main()
