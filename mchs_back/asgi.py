"""
ASGI config for mchs_back project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mchs_back.settings')

application = get_asgi_application()
