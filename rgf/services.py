"""
Service layer — all logic is self-contained within this Django app.
Views stay thin, all heavy work happens here.
"""
import json
import re
import time
import tempfile
from pathlib import Path
from typing import Optional

from .planning_api.docx_parser import parse_docx_universal
from .planning_api import org_mapping
from .planning_api.auth import login
from .planning_api.rgf_api import get_gu_list, create_position_department, delete_position_department
from .planning_api.config import IIN, PASSWORD, DEFAULT_POSITION_ID, DEFAULT_PARENT_ID


def save_import_record(result: dict, data: dict, was_edited: bool = False) -> None:
    """Persist an import result + document data to the DB. Silently swallows errors."""
    try:
        from .models import ImportRecord
        ImportRecord.objects.create(
            filename                     = result.get('filename', ''),
            gu_id                        = result.get('gu_id', ''),
            gu_name                      = result.get('gu_name', ''),
            record_id                    = result.get('record_id'),
            status                       = result.get('status', ''),
            skip_reason                  = result.get('skip_reason', ''),
            error                        = result.get('error', ''),
            url                          = result.get('url', ''),
            was_edited                   = was_edited,
            general_provisions           = data.get('general_provisions', ''),
            tasks                        = data.get('tasks', []),
            authorities_rights           = data.get('authorities_rights', []),
            authorities_responsibilities = data.get('authorities_responsibilities', []),
            functions                    = data.get('functions', []),
            additions                    = data.get('additions', ''),
            tasks_count                  = len(data.get('tasks', [])),
            rights_count                 = len(data.get('authorities_rights', [])),
            responsibilities_count       = len(data.get('authorities_responsibilities', [])),
            functions_count              = len(data.get('functions', [])),
        )
    except Exception:
        pass  # never let DB errors break the import flow

# Import reports are written by the bulk_import script into this data directory
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "polozhenia" / "parse_functioons" / "data"

# ─── Auth cache ──────────────────────────────────────────────────────────────
def get_cached_auth() -> tuple[str, list]:
    """Return (token, gu_list) — always fetches fresh from planning.gov.kz."""
    token, _ = login(IIN, PASSWORD)
    if not token:
        raise RuntimeError("Failed to authenticate with planning.gov.kz")
    gu_list = get_gu_list(token) or []
    return token, gu_list


# ─── Auth ────────────────────────────────────────────────────────────────────

def get_token() -> str:
    """Return a valid bearer token."""
    token, _ = get_cached_auth()
    return token


# ─── Organizations ────────────────────────────────────────────────────────────

def list_organizations() -> list[dict]:
    """Return all GU organizations from the API."""
    _, gu_list = get_cached_auth()
    return [{"id": o.get("id"), "name": o.get("nameRu", "")} for o in gu_list]


# ─── Preview ─────────────────────────────────────────────────────────────────

def preview_document(file_bytes: bytes, filename: str, gu_list: list) -> dict:
    """
    Parse a .docx file and return extracted data + auto-detected org.
    Does NOT import to API.
    """
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        data = parse_docx_universal(tmp_path)
        gu_id, gu_name, detected_source = org_mapping.suggest_gu_for_file(
            filename, gu_list, tmp_path
        )

        rights = len(data.get("authorities_rights", []))
        responsibilities = len(data.get("authorities_responsibilities", []))
        tasks = len(data.get("tasks", []))
        functions = len(data.get("functions", []))

        issues = []
        warnings = []
        if rights == 0 and responsibilities == 0:
            issues.append("missing_rights_and_responsibilities")
        elif rights == 0:
            issues.append("missing_rights")
        elif responsibilities == 0:
            issues.append("missing_responsibilities")
        if tasks == 0:
            warnings.append("missing_tasks")
        if functions == 0:
            warnings.append("missing_functions")

        confidence = data.get("confidence", 0.0)
        if confidence < 0.75:
            warnings.append("low_confidence")

        return {
            "filename": filename,
            "gu_id": gu_id,
            "gu_name": gu_name,
            "detected_source": detected_source,
            "stats": {
                "rights": rights,
                "responsibilities": responsibilities,
                "tasks": tasks,
                "functions": functions,
                "confidence": confidence,
            },
            "issues": issues,
            "warnings": warnings,
            "can_import": len(issues) == 0,
            "data": {
                "general_provisions": data.get("general_provisions", ""),
                "tasks": data.get("tasks", []),
                "authorities_rights": data.get("authorities_rights", []),
                "authorities_responsibilities": data.get("authorities_responsibilities", []),
                "functions": data.get("functions", []),
                "additions": data.get("additions", ""),
            },
        }
    finally:
        tmp_path.unlink(missing_ok=True)


# ─── AI Analysis ─────────────────────────────────────────────────────────────

_AI_CHUNK_SIZE = 6000   # chars per chunk sent to Mistral
_AI_OVERLAP    = 500    # chars of overlap between chunks so we don't cut mid-sentence


def _build_ai_prompt(chunk: str, chunk_index: int, total_chunks: int) -> str:
    header = (
        "Ты эксперт по анализу нормативных документов казахстанских государственных органов.\n"
        "Проанализируй следующий фрагмент Положения о государственном органе и извлеки структурированные данные.\n\n"
        "ВАЖНО:\n"
        '- "tasks" — основные задачи государственного органа (раздел "Задачи")\n'
        '- "authorities_rights" — что орган ВПРАВЕ делать (его права и полномочия)\n'
        '- "authorities_responsibilities" — что орган ОБЯЗАН делать (его обязательства)\n'
        '- "functions" — конкретные функции и виды деятельности органа\n'
        '- "general_provisions" — вводная часть документа\n'
        '- "additions" — прочие разделы (ответственность, имущество и т.д.)\n\n'
        "Верни ТОЛЬКО валидный JSON без пояснений:\n"
        '{"general_provisions":"текст","tasks":["задача 1",...],"authorities_rights":["право 1",...],'
        '"authorities_responsibilities":["обязанность 1",...],"functions":["функция 1",...],"additions":"текст"}\n\n'
        "Каждый элемент списка — это ОТДЕЛЬНЫЙ пункт без номера. Не объединяй несколько пунктов в один.\n"
    )
    if total_chunks > 1:
        header += f"(Фрагмент {chunk_index + 1} из {total_chunks} — если раздел не встречается в этом фрагменте, верни пустой список/строку)\n"
    return header + f"\nТЕКСТ:\n{chunk}"


def _merge_ai_chunks(chunks: list[dict], raw_data: dict) -> dict:
    """Merge results from multiple AI chunks, deduplicating list items."""
    def merge_lists(key: str) -> list[str]:
        seen = set()
        merged = []
        for chunk in chunks:
            for item in chunk.get(key, []):
                item = item.strip()
                if item and item not in seen:
                    seen.add(item)
                    merged.append(item)
        return merged or raw_data.get(key, [])

    return {
        "general_provisions":           next((c["general_provisions"] for c in chunks if c.get("general_provisions")), raw_data.get("general_provisions", "")),
        "tasks":                        merge_lists("tasks"),
        "authorities_rights":           merge_lists("authorities_rights"),
        "authorities_responsibilities": merge_lists("authorities_responsibilities"),
        "functions":                    merge_lists("functions"),
        "additions":                    " ".join(c.get("additions", "") for c in chunks if c.get("additions")).strip() or raw_data.get("additions", ""),
    }


def _call_mistral(client, model: str, prompt: str, retries: int = 3) -> dict:
    """Call Mistral with exponential backoff on 429. Returns parsed JSON dict."""
    for attempt in range(retries):
        try:
            response = client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "capacity" in err_str.lower()
            if is_rate_limit and attempt < retries - 1:
                time.sleep(2 ** attempt)  # 1 s, 2 s, 4 s
                continue
            raise


def ai_analyze_document(file_bytes: bytes, filename: str, gu_list: list) -> dict:
    """
    Parse a .docx file and use Mistral AI to re-categorize the content into
    the correct sections. Splits long documents into overlapping chunks so the
    full document is always analyzed. Returns the same structure as preview_document().
    """
    from django.conf import settings
    from mistralai import Mistral
    from docx import Document

    api_key = getattr(settings, 'MISTRAL_API_KEY', None)
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY not configured in settings")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        # Initial parse for org detection and fallback data
        raw_data = parse_docx_universal(tmp_path)
        gu_id, gu_name, detected_source = org_mapping.suggest_gu_for_file(
            filename, gu_list, tmp_path
        )

        # Extract raw paragraphs
        doc = Document(tmp_path)
        all_paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = '\n'.join(all_paragraphs)

        # Split into overlapping chunks so long documents are fully covered
        chunks: list[str] = []
        start = 0
        while start < len(full_text):
            end = start + _AI_CHUNK_SIZE
            chunks.append(full_text[start:end])
            if end >= len(full_text):
                break
            start = end - _AI_OVERLAP

        # Use the small model — higher rate limits, still very capable
        model = getattr(settings, 'MISTRAL_MODEL_SMALL', 'mistral-small-latest')
        client = Mistral(api_key=api_key)

        chunk_results: list[dict] = []
        for i, chunk in enumerate(chunks):
            prompt = _build_ai_prompt(chunk, i, len(chunks))
            ai_data = _call_mistral(client, model, prompt)
            # Ensure list fields are actually lists
            for key in ("tasks", "authorities_rights", "authorities_responsibilities", "functions"):
                if isinstance(ai_data.get(key), str):
                    ai_data[key] = [ai_data[key]] if ai_data[key].strip() else []
            chunk_results.append(ai_data)

        data = _merge_ai_chunks(chunk_results, raw_data)

        rights           = len(data["authorities_rights"])
        responsibilities = len(data["authorities_responsibilities"])
        tasks            = len(data["tasks"])
        functions        = len(data["functions"])

        issues = []
        warnings = []
        if rights == 0 and responsibilities == 0:
            issues.append("missing_rights_and_responsibilities")
        elif rights == 0:
            issues.append("missing_rights")
        elif responsibilities == 0:
            issues.append("missing_responsibilities")
        if tasks == 0:
            warnings.append("missing_tasks")
        if functions == 0:
            warnings.append("missing_functions")

        return {
            "filename":        filename,
            "gu_id":           gu_id,
            "gu_name":         gu_name,
            "detected_source": detected_source,
            "stats": {
                "rights":           rights,
                "responsibilities": responsibilities,
                "tasks":            tasks,
                "functions":        functions,
            },
            "issues":     issues,
            "warnings":   warnings,
            "can_import": len(issues) == 0,
            "data":       data,
        }
    finally:
        tmp_path.unlink(missing_ok=True)


# ─── Import ───────────────────────────────────────────────────────────────────

def import_parsed(gu_id: str, data: dict, token: str, gu_name: str = "") -> dict:
    """
    Import already-parsed (and possibly edited) data directly to the API.
    data keys: general_provisions, tasks, authorities_rights, authorities_responsibilities, functions, additions
    """
    rights = len(data.get("authorities_rights", []))
    responsibilities = len(data.get("authorities_responsibilities", []))
    tasks = len(data.get("tasks", []))
    functions = len(data.get("functions", []))

    if rights == 0 and responsibilities == 0:
        return {"status": "skipped", "skip_reason": "Отсутствуют права и обязанности",
                "stats": {"rights": 0, "responsibilities": 0, "tasks": tasks, "functions": functions}}
    if rights == 0:
        return {"status": "skipped", "skip_reason": "Отсутствуют права",
                "stats": {"rights": 0, "responsibilities": responsibilities, "tasks": tasks, "functions": functions}}
    if responsibilities == 0:
        return {"status": "skipped", "skip_reason": "Отсутствуют обязанности",
                "stats": {"rights": rights, "responsibilities": 0, "tasks": tasks, "functions": functions}}

    def _attempt(position_department_id=None):
        payload = _build_payload(gu_id, data, gu_name=gu_name, position_department_id=position_department_id)
        return create_position_department(token, payload)

    result = _attempt()

    # If duplicate (409 or DB constraint), retry as update using stored record_id
    if result and not result.get("success"):
        error_msg = result.get("errorMsg", "") or ""
        response_code = result.get("responseCode")
        is_duplicate = response_code == 409 or "constraint" in error_msg.lower() or "duplicate" in error_msg.lower()
        if is_duplicate:
            existing_id = _find_existing_record_id(gu_id)
            if existing_id:
                result = _attempt(position_department_id=existing_id)

    if result and result.get("success"):
        record_id = result.get("data")
        out = {
            "status": "success",
            "record_id": record_id,
            "gu_id": gu_id,
            "stats": {"rights": rights, "responsibilities": responsibilities, "tasks": tasks, "functions": functions},
            "warnings": _collect_warnings(tasks, functions),
            "url": f"https://planning.gov.kz/rgffront#/rgffront/filter/positions/department/{record_id}/edit",
        }
        save_import_record(out, data, was_edited=True)
        return out

    out = {
        "status": "error",
        "error": result.get("errorMsg", str(result)) if isinstance(result, dict) else str(result),
        "stats": {"rights": rights, "responsibilities": responsibilities, "tasks": tasks, "functions": functions},
    }
    save_import_record(out, data, was_edited=True)
    return out


def import_document(file_bytes: bytes, filename: str, gu_id: str, token: str) -> dict:
    """
    Parse and import a single .docx file to the API.
    Returns result dict with status, record_id, stats.
    """
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        data = parse_docx_universal(tmp_path)

        rights = len(data.get("authorities_rights", []))
        responsibilities = len(data.get("authorities_responsibilities", []))
        tasks = len(data.get("tasks", []))
        functions = len(data.get("functions", []))

        if rights == 0 and responsibilities == 0:
            return {
                "filename": filename,
                "status": "skipped",
                "skip_reason": "Missing both rights and responsibilities",
                "stats": {"rights": 0, "responsibilities": 0, "tasks": tasks, "functions": functions},
            }
        if rights == 0:
            return {
                "filename": filename,
                "status": "skipped",
                "skip_reason": "Missing rights",
                "stats": {"rights": 0, "responsibilities": responsibilities, "tasks": tasks, "functions": functions},
            }
        if responsibilities == 0:
            return {
                "filename": filename,
                "status": "skipped",
                "skip_reason": "Missing responsibilities",
                "stats": {"rights": rights, "responsibilities": 0, "tasks": tasks, "functions": functions},
            }

        def _attempt(position_department_id=None):
            payload = _build_payload(gu_id, data, position_department_id=position_department_id)
            return create_position_department(token, payload)

        result = _attempt()

        # If duplicate (409 or DB constraint), retry as update using stored record_id
        if result and not result.get("success"):
            error_msg = result.get("errorMsg", "") or ""
            response_code = result.get("responseCode")
            is_duplicate = response_code == 409 or "constraint" in error_msg.lower() or "duplicate" in error_msg.lower()
            if is_duplicate:
                existing_id = _find_existing_record_id(gu_id)
                if existing_id:
                    result = _attempt(position_department_id=existing_id)

        if result and result.get("success"):
            record_id = result.get("data")
            out = {
                "filename": filename,
                "status": "success",
                "record_id": record_id,
                "gu_id": gu_id,
                "stats": {"rights": rights, "responsibilities": responsibilities, "tasks": tasks, "functions": functions},
                "warnings": _collect_warnings(tasks, functions),
                "url": f"https://planning.gov.kz/rgffront#/rgffront/filter/positions/department/{record_id}/edit",
            }
            save_import_record(out, data, was_edited=False)
            return out

        out = {
            "filename": filename,
            "status": "error",
            "error": result.get("errorMsg", str(result)) if isinstance(result, dict) else str(result),
            "stats": {"rights": rights, "responsibilities": responsibilities, "tasks": tasks, "functions": functions},
        }
        save_import_record(out, data, was_edited=False)
        return out

    except Exception as e:
        return {"filename": filename, "status": "error", "error": str(e)}
    finally:
        tmp_path.unlink(missing_ok=True)


def _collect_warnings(tasks: int, functions: int) -> list[str]:
    warnings = []
    if tasks == 0:
        warnings.append("missing_tasks")
    if functions == 0:
        warnings.append("missing_functions")
    return warnings


def _build_payload(gu_id: str, data: dict, gu_name: str = "", position_department_id: int = None) -> dict:
    if position_department_id is None:
        position_department_id = DEFAULT_POSITION_ID  # same as positionId = create new record
    return {
        "positionId":           DEFAULT_POSITION_ID,
        "positionDepartmentId": position_department_id,
        "guId":                 gu_id,
        "guName":               gu_name,
        "parentId":             DEFAULT_PARENT_ID,
        "departmentId":         None,
        "committeeId":          None,
        "departmentGuid":       None,
        "type":                 4,
        "staffNumbers":         5,
        "legalEntity":          False,
        "status":               "",
        "approvals":            [],
        "generalProvisions":    data.get("general_provisions", ""),
        "additions":            data.get("additions", ""),
        "tasks":                [{"taskText": t} for t in data.get("tasks", [])],
        "functions":            [{"functionText": f} for f in data.get("functions", [])],
        "authoritiesLaw":       [{"authorityText": r} for r in data.get("authorities_rights", [])],
        "authoritiesResponsibilities": [{"authorityText": r} for r in data.get("authorities_responsibilities", [])],
    }


def _find_existing_record_id(gu_id: str) -> Optional[int]:
    """Look up a previously imported record_id for this GU from our local DB."""
    try:
        from .models import ImportRecord
        rec = ImportRecord.objects.filter(
            gu_id=gu_id, status='success', record_id__isnull=False
        ).order_by('-created_at').first()
        return rec.record_id if rec else None
    except Exception:
        return None


# ─── Records from reports ─────────────────────────────────────────────────────

def get_imported_records() -> list[dict]:
    """Return all records previously imported (from import_report_*.txt files)."""
    records = []
    if not DATA_DIR.exists():
        return records

    for report_file in sorted(DATA_DIR.glob("import_report_*.txt")):
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()

        for match in re.finditer(r"ID записи:\s*(\d+)", content):
            record_id = int(match.group(1))
            start = max(0, match.start() - 500)
            context = content[start:match.end() + 200]

            file_match = re.search(r"Положение.*?\.docx", context)
            org_match = re.search(r"Организация:\s*(.+?)(?:\n|$)", context)
            gu_id_match = re.search(r"GU ID:\s*(\S+)", context)

            records.append({
                "record_id": record_id,
                "org": org_match.group(1).strip() if org_match else "Unknown",
                "file": file_match.group(0) if file_match else "Unknown",
                "gu_id": gu_id_match.group(1).strip() if gu_id_match else None,
                "report": report_file.name,
                "url": f"https://planning.gov.kz/rgffront#/rgffront/filter/positions/department/{record_id}/edit",
            })

    return records


# ─── Delete ───────────────────────────────────────────────────────────────────

def delete_records(record_ids: list[int], token: str) -> dict:
    """Delete a list of record IDs. Returns {deleted, failed}."""
    deleted = []
    failed = []

    for record_id in record_ids:
        result = delete_position_department(token, record_id)
        if result is not None:
            deleted.append(record_id)
        else:
            failed.append(record_id)

    return {"deleted": deleted, "failed": failed}
