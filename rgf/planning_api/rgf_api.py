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
