"""
Service layer — all logic is self-contained within this Django app.
Views stay thin, all heavy work happens here.
"""
import re
import tempfile
from pathlib import Path

from .planning_api.docx_parser import parse_docx_universal
from .planning_api import org_mapping
from .planning_api.auth import login
from .planning_api.rgf_api import get_gu_list, create_position_department, delete_position_department
from .planning_api.config import IIN, PASSWORD, DEFAULT_POSITION_ID, DEFAULT_PARENT_ID

# Import reports are written by the bulk_import script into this data directory
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "polozhenia" / "parse_functioons" / "data"


# ─── Auth ────────────────────────────────────────────────────────────────────

def get_token() -> str:
    """Login and return a fresh bearer token."""
    token, _ = login(IIN, PASSWORD)
    if not token:
        raise RuntimeError("Failed to authenticate with planning.gov.kz")
    return token


# ─── Organizations ────────────────────────────────────────────────────────────

def list_organizations() -> list[dict]:
    """Return all GU organizations from the API."""
    token = get_token()
    orgs = get_gu_list(token)
    return [{"id": o.get("id"), "name": o.get("nameRu", "")} for o in (orgs or [])]


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
            },
            "issues": issues,
            "warnings": warnings,
            "can_import": len(issues) == 0,
        }
    finally:
        tmp_path.unlink(missing_ok=True)


# ─── Import ───────────────────────────────────────────────────────────────────

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

        payload = _build_payload(gu_id, data)
        result = create_position_department(token, payload)

        if result and result.get("success"):
            record_id = result.get("data")
            return {
                "filename": filename,
                "status": "success",
                "record_id": record_id,
                "gu_id": gu_id,
                "stats": {"rights": rights, "responsibilities": responsibilities, "tasks": tasks, "functions": functions},
                "warnings": _collect_warnings(tasks, functions),
                "url": f"https://planning.gov.kz/rgffront#/rgffront/filter/positions/department/{record_id}/edit",
            }

        return {
            "filename": filename,
            "status": "error",
            "error": str(result),
            "stats": {"rights": rights, "responsibilities": responsibilities, "tasks": tasks, "functions": functions},
        }

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


def _build_payload(gu_id: str, data: dict) -> dict:
    def fmt(items):
        return [{"name": item} for item in items]

    return {
        "positionId": DEFAULT_POSITION_ID,
        "positionDepartmentId": DEFAULT_POSITION_ID,
        "guId": gu_id,
        "parentId": DEFAULT_PARENT_ID,
        "generalProvisions": data.get("general_provisions", ""),
        "tasks": fmt(data.get("tasks", [])),
        "functions": fmt(data.get("functions", [])),
        "authoritiesLaw": fmt(data.get("authorities_rights", [])),
        "authoritiesResponsibilities": fmt(data.get("authorities_responsibilities", [])),
        "additions": data.get("additions", ""),
    }


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
