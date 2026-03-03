"""
Authentication module for planning.gov.kz API
"""

import requests
import urllib3
from .config import BASE_URL, COMMON_HEADERS

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def login(iin, password):
    """
    Login to the API and return the Bearer token

    Returns:
        tuple: (token, user_data) if successful, (None, None) if failed
    """
    url = f"{BASE_URL}/sso/api/account/login"

    payload = {
        "username": iin,
        "password": password
    }

    headers = {
        **COMMON_HEADERS,
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
    }

    response = requests.post(url, json=payload, headers=headers, verify=False)

    if response.status_code == 200:
        data = response.json()
        token = data.get('token')
        return token, data
    else:
        return None, None
