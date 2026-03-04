"""
RGF Module API functions for planning.gov.kz
"""

import requests
import urllib3
from .config import BASE_URL, DEFAULT_LANG, DEFAULT_POSITION_ID, DEFAULT_PARENT_ID, DEFAULT_SELECTED_LEVEL

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_rgf_headers(token):
    return {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "selectedlevel": DEFAULT_SELECTED_LEVEL,
        "Referer": f"{BASE_URL}/rgffront"
    }


def get_gu_list(token, parent_id=DEFAULT_PARENT_ID, has_not_ended=True, lang=DEFAULT_LANG):
    """Get GU (government units) list. Returns list or None."""
    url = f"{BASE_URL}/gateway/rgf-module/gu/get?parentId={parent_id}&hasNotEnded={has_not_ended}&lang={lang}"
    response = requests.get(url, headers=_get_rgf_headers(token), verify=False)
    if response.status_code == 200:
        return response.json()
    return None


def get_position_department(token, record_id, lang=DEFAULT_LANG):
    """Get a specific position-department record by ID. Returns dict or None."""
    url = f"{BASE_URL}/gateway/rgf-module/position-department/{record_id}?lang={lang}"
    response = requests.get(url, headers=_get_rgf_headers(token), verify=False)
    if response.status_code == 200:
        return response.json()
    return None


def delete_position_department(token, record_id, lang=DEFAULT_LANG):
    """Delete a position-department record by ID. Returns dict or None."""
    url = f"{BASE_URL}/gateway/rgf-module/position-department/{record_id}?lang={lang}"
    response = requests.delete(url, headers=_get_rgf_headers(token), verify=False)
    if response.status_code == 200:
        try:
            return response.json()
        except Exception:
            return {"success": True}
    return None


def create_position_department(token, payload, lang=DEFAULT_LANG):
    """Create a new position-department record. Returns API response dict or None."""
    url = f"{BASE_URL}/gateway/rgf-module/position-department?lang={lang}"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "selectedlevel": DEFAULT_SELECTED_LEVEL,
        "Referer": f"{BASE_URL}/rgffront",
        "Origin": BASE_URL
    }

    response = requests.post(url, json=payload, headers=headers, verify=False)

    try:
        return response.json()
    except Exception:
        return None


# ─── Department-functions registry ────────────────────────────────────────────

def _parse_list_response(data):
    """Normalise API responses that may be a plain list or a paged envelope."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('content', 'data', 'items', 'list', 'result'):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def get_position_department_tasks(token, position_department_id, lang=DEFAULT_LANG):
    """Return tasks stored on a position-department record (used to link functions)."""
    url = (f"{BASE_URL}/gateway/rgf-module/position-department/tasks"
           f"?lang={lang}&positionDepartmentId={position_department_id}")
    response = requests.get(url, headers=_get_rgf_headers(token), verify=False)
    if response.status_code == 200:
        return _parse_list_response(response.json())
    return []


def get_function_type_dict(token, lang=DEFAULT_LANG):
    url = f"{BASE_URL}/gateway/rgf-module/dictionary/function-type?lang={lang}&page=0&size=100"
    response = requests.get(url, headers=_get_rgf_headers(token), verify=False)
    if response.status_code == 200:
        return _parse_list_response(response.json())
    return []


def get_activity_areas_dict(token, lang=DEFAULT_LANG):
    url = f"{BASE_URL}/gateway/rgf-module/dictionary/activity-areas?lang={lang}&page=0&size=100"
    response = requests.get(url, headers=_get_rgf_headers(token), verify=False)
    if response.status_code == 200:
        return _parse_list_response(response.json())
    return []


def get_digital_maturity_dict(token, lang=DEFAULT_LANG):
    url = f"{BASE_URL}/gateway/rgf-module/dictionary/digital-maturity?lang={lang}&page=0&size=100"
    response = requests.get(url, headers=_get_rgf_headers(token), verify=False)
    if response.status_code == 200:
        return _parse_list_response(response.json())
    return []


def get_ebk_fkr_dict(token, lang=DEFAULT_LANG):
    """Return EBK functional classification groups (first page, 100 items)."""
    url = (f"{BASE_URL}/gateway/rgf-module/current_ebk/fkr/get/"
           f"?lang={lang}&page=1&limit=100&actual=true&dictType=10")
    response = requests.get(url, headers=_get_rgf_headers(token), verify=False)
    if response.status_code == 200:
        return _parse_list_response(response.json())
    return []


def create_department_function(token, payload, lang=DEFAULT_LANG):
    """Create one function registry entry. Returns API response dict or None."""
    url = f"{BASE_URL}/gateway/rgf-module/department-functions?lang={lang}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "selectedlevel": DEFAULT_SELECTED_LEVEL,
        "Referer": f"{BASE_URL}/rgffront",
        "Origin": BASE_URL,
    }
    response = requests.post(url, json=payload, headers=headers, verify=False)
    try:
        return response.json()
    except Exception:
        return None
