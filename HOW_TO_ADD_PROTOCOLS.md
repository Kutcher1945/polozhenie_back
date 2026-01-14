# How to Add More Clinical Protocols

## Current Status

✅ **Protocol ID 1 (HELLP-СИНДРОМ)** - Fully processed with 37 content sections
❌ **All other protocols** - Only metadata, no content extracted

---

## How to Add a New Protocol

### Method 1: Process Existing PDF (Recommended)

If you have the PDF file locally:

```bash
cd /home/corettaxkutcher/zhancare_group/zhancare_back_experiment

# 1. Copy or download the PDF file
# Example: wget <PDF_URL> -O "PROTOCOL_NAME.pdf"

# 2. Edit ml_pipeline_final.py to point to your PDF
# Change these lines:
PDF_PATH = "YOUR_PROTOCOL_NAME.pdf"
PROTOCOL_ID = 2  # Change to the ID from database

# 3. Run the pipeline
venv/bin/python ml_pipeline_final.py
```

### Method 2: Download and Process from Database URLs

Many protocols already have URLs in the database. You can download and process them:

```bash
# 1. Check available protocols with URLs
PGPASSWORD='4HPzQt2HyU' psql -h localhost -U zhancare -d zhancare_db -c \
  "SELECT id, name, url FROM clinical_protocols WHERE url IS NOT NULL ORDER BY id LIMIT 10;"

# 2. Download a PDF
wget -O "protocol.pdf" "URL_FROM_DATABASE"

# 3. Update ml_pipeline_final.py
PDF_PATH = "protocol.pdf"
PROTOCOL_ID = <ID_FROM_DATABASE>

# 4. Run the pipeline
venv/bin/python ml_pipeline_final.py
```

---

## Batch Processing Script

Create a script to process multiple protocols:

```python
# batch_process_protocols.py
import os
import subprocess
import requests
from ml_pipeline_final import main as process_protocol

# Get protocols that need processing
protocols = [
    {"id": 2, "name": "АТЕРОГЕННЫЕ НАРУШЕНИЯ", "url": "..."},
    {"id": 3, "name": "ВЕДЕНИЕ БЕРЕМЕННЫХ", "url": "..."},
    # Add more protocols here
]

for protocol in protocols:
    print(f"Processing: {protocol['name']}")

    # Download PDF
    pdf_path = f"{protocol['id']}_{protocol['name'][:20]}.pdf"
    response = requests.get(protocol['url'])
    with open(pdf_path, 'wb') as f:
        f.write(response.content)

    # Update config and process
    # (You'll need to modify ml_pipeline_final.py to accept arguments)
    # process_protocol(pdf_path, protocol['id'])

    print(f"✅ Completed: {protocol['name']}")
```

---

## Quick Test: Process Protocol #2

```bash
cd /home/corettaxkutcher/zhancare_group/zhancare_back_experiment

# Get the URL for protocol #2
PROTOCOL_URL=$(PGPASSWORD='4HPzQt2HyU' psql -h localhost -U zhancare -d zhancare_db -t -c \
  "SELECT url FROM clinical_protocols WHERE id = 2;")

# Download it
wget -O "protocol_2.pdf" "$PROTOCOL_URL"

# Update ml_pipeline_final.py
# Change:
# PDF_PATH = "protocol_2.pdf"
# PROTOCOL_ID = 2

# Run the pipeline
venv/bin/python ml_pipeline_final.py
```

---

## Verify Content Was Added

```bash
# Check how many sections were added
PGPASSWORD='4HPzQt2HyU' psql -h localhost -U zhancare -d zhancare_db -c \
  "SELECT protocol_id, COUNT(*) as sections
   FROM clinical_protocols_content
   GROUP BY protocol_id
   ORDER BY protocol_id;"
```

---

## Make Pipeline Accept Arguments

Update `ml_pipeline_final.py` to accept command-line arguments:

```python
import sys

# CONFIG
PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else "HELLP-СИНДРОМ.pdf"
PROTOCOL_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 1
```

Then run:
```bash
venv/bin/python ml_pipeline_final.py "protocol.pdf" 2
```

---

## Expected Results

After processing a protocol, you should see:
- ✅ ~20-50 content sections extracted
- ✅ Sections classified by type (diagnosis, treatment, etc.)
- ✅ Full medical text preserved
- ✅ Page numbers recorded
- ✅ Protocol appears in frontend dropdown

---

## Troubleshooting

### Problem: "No sections extracted"
**Solution:** PDF might have different structure. Check the PDF manually and adjust heading detection in ml_pipeline.py

### Problem: "Classification failed"
**Solution:** Check Mistral API key and quota. Pipeline will fall back to rule-based classification.

### Problem: "Database constraint error"
**Solution:** Protocol content already exists. Clear it first:
```sql
DELETE FROM clinical_protocols_content WHERE protocol_id = X;
```

---

## Performance Notes

| Protocols | Processing Time | API Calls | Cost (Est.) |
|-----------|----------------|-----------|-------------|
| 1 protocol | ~1 minute | 1 | $0.001 |
| 10 protocols | ~10 minutes | 10 | $0.01 |
| 100 protocols | ~2 hours | 100 | $0.10 |

---

## Recommended Priority

Process these protocols first (most commonly used):

1. ✅ HELLP-СИНДРОМ (Done)
2. ⬜ АТЕРОГЕННЫЕ НАРУШЕНИЯ ЛИПИДНОГО ОБМЕНА
3. ⬜ ГИПЕРТРОФИЧЕСКАЯ КАРДИОМИОПАТИЯ
4. ⬜ АБДОМИНАЛЬНАЯ ТРАВМА
5. ⬜ АЛЛЕРГИЧЕСКИЙ РИНИТ

---

Made with ❤️ by Claude Code
