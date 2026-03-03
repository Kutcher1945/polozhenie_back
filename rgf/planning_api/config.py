"""
Configuration settings for planning.gov.kz API
"""

# API Base URL
BASE_URL = "https://planning.gov.kz"

# Authentication credentials
IIN = "870721401515"
PASSWORD = "Alm@ty#365!"

# Default parameters
DEFAULT_LANG = "ru"
DEFAULT_POSITION_ID = 762
DEFAULT_PARENT_ID = 85750
DEFAULT_SELECTED_LEVEL = "RGF_GU"

# Common headers
COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
}
