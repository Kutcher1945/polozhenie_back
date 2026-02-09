import os
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
    "dbname": "zhancare_db",
    "user": "zhancare",
    "password": "4HPzQt2HyU",  # move to ENV in production
    "host": "localhost",
    "port": 5432,
}

MISTRAL_API_KEY = "QqkMxELY0YVGkCx17Vya04Sq9nGvCahu"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

RATE_LIMIT_SECONDS = 0.6

ALLOWED_TYPES = {
    "definition", "diagnosis", "classification",
    "differential", "treatment", "drugs",
    "algorithm", "complications",
    "indications", "contraindications",
    "metadata",
    "other"
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
  "confidence": number between 0 and 1
}
"""

# =========================================================
# MISTRAL CALL
# =========================================================
def classify_with_mistral(text: str) -> dict:
    if len(text.strip()) < 50:
        return {"content_type": "other", "confidence": 0.0}

    payload = {
        "model": "open-mistral-nemo",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text[:6000]}
        ],
        "temperature": 0.0,
        "max_tokens": 150
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

    try:
        raw = response.json()["choices"][0]["message"]["content"]
        result = json.loads(raw)
    except Exception:
        return {"content_type": "other", "confidence": 0.0}

    ct = result.get("content_type", "other")
    conf = float(result.get("confidence", 0))

    if ct not in ALLOWED_TYPES or conf < 0.6:
        return {"content_type": "other", "confidence": conf}

    return {"content_type": ct, "confidence": conf}

# =========================================================
# HEADING DETECTION
# =========================================================
NUM_HEADING_RE = re.compile(r"^(?:[IVX]+\.|\d+(?:\.\d+)*)\s+")

KEYWORD_HEADINGS = (
    "КЛИНИЧЕСКИЙ ПРОТОКОЛ",
    "ВВОДНАЯ ЧАСТЬ",
    "ДИАГНОСТ",
    "КЛАССИФ",
    "ЛЕЧЕНИ",
    "АЛГОРИТМ",
    "ОСЛОЖНЕНИ",
    "ПОКАЗАНИЯ",
    "ПРОТИВОПОКАЗАНИЯ",
    "ПРИЛОЖЕНИЕ",
)

def is_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False

    if NUM_HEADING_RE.match(s):
        return True

    if s.isupper() and len(s) < 120:
        return True

    u = s.upper()
    if any(u.startswith(k) for k in KEYWORD_HEADINGS) and (s.endswith(":") or s.isupper()):
        return True

    return False

# =========================================================
# SPLIT COLON HEADINGS (CRITICAL FIX)
# =========================================================
def split_heading_line(line: str):
    """
    Splits:
    '1.7 Определение [1,2]: HELLP-синдром – ...'
    into:
    title = '1.7 Определение [1,2]'
    spillover = 'HELLP-синдром – ...'
    """
    if ":" in line:
        left, right = line.split(":", 1)
        return left.strip(), right.strip()
    return line.strip(), None

# =========================================================
# METADATA DETECTION
# =========================================================
def is_metadata_block(title: str, content: str) -> bool:
    t = (title + " " + content).upper()

    METADATA_MARKERS = (
        "ОДОБРЕН",
        "КЛИНИЧЕСКИЙ ПРОТОКОЛ",
        "МКБ-10",
        "ДАТА РАЗРАБОТКИ",
        "СОКРАЩЕНИЯ",
        "СПИСОК РАЗРАБОТЧИКОВ",
        "РЕЦЕНЗЕНТЫ",
        "КОНФЛИКТА ИНТЕРЕСОВ",
        "СПИСОК ИСПОЛЬЗОВАННОЙ ЛИТЕРАТУРЫ",
        "IGO LICENCE",
        "CREATIVE COMMONS",
    )

    return any(m in t for m in METADATA_MARKERS)

# =========================================================
# PDF EXTRACTION (FINAL)
# =========================================================
def extract_pdf_blocks(path):
    blocks = []
    title_lines = []
    body_lines = []
    page_from = None
    last_page = None

    def flush():
        nonlocal title_lines, body_lines, page_from, last_page
        if not body_lines:
            title_lines.clear()
            body_lines.clear()
            page_from = None
            last_page = None
            return

        blocks.append({
            "page_from": page_from,
            "page_to": last_page,
            "title": " ".join(title_lines).strip(),
            "content": "\n".join(body_lines).strip()
        })

        title_lines.clear()
        body_lines.clear()
        page_from = None
        last_page = None

    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]

            for line in lines:
                line = (
                    line.replace("\uf0b7", "•")
                        .replace("￾", "-")
                        .replace("–", "-")
                )

                if is_heading(line):
                    if body_lines:
                        flush()

                    if page_from is None:
                        page_from = page_num

                    title_part, spillover = split_heading_line(line)
                    title_lines.append(title_part)

                    if spillover:
                        body_lines.append(spillover)
                else:
                    if page_from is None:
                        page_from = page_num
                    body_lines.append(line)

                last_page = page_num

    flush()
    return blocks

# =========================================================
# DB INSERT
# =========================================================
def insert_content(cur, protocol_id, block, result, order):
    cur.execute("""
        INSERT INTO clinical_protocols_content
        (protocol_id, content_type, title, content,
         page_from, page_to, source, confidence, "order", created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT DO NOTHING
    """, (
        protocol_id,
        result["content_type"],
        block["title"],
        block["content"],
        block["page_from"],
        block["page_to"],
        "pdf+mistral",
        result["confidence"],
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
        for idx, block in enumerate(tqdm(blocks, desc="Classifying blocks"), start=1):
            info(f"Block {idx}: pages {block['page_from']}-{block['page_to']}")

            if is_metadata_block(block["title"], block["content"]):
                result = {"content_type": "metadata", "confidence": 1.0}
            else:
                result = classify_with_mistral(block["content"])

            insert_content(
                cur,
                PROTOCOL_ID,
                block,
                result,
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
