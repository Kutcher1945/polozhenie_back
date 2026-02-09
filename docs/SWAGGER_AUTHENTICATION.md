# 🔐 SWAGGER/REDOC AUTHENTICATION GUIDE

## Overview

Swagger and ReDoc API documentation are now **protected** and require authentication.

**Only staff and superuser accounts can access the documentation.**

---

## 🔒 PROTECTION FEATURES

### ✅ What's Protected:
- `/swagger/` - Interactive Swagger UI
- `/redoc/` - ReDoc documentation
- `/swagger.json` - OpenAPI schema (JSON)
- `/swagger.yaml` - OpenAPI schema (YAML)

### ✅ Who Can Access:
- **Django Staff users** (`is_staff=True`)
- **Superusers** (`is_superuser=True`)

### ❌ Who Cannot Access:
- Anonymous users
- Regular users (patients, doctors, nurses without staff status)
- External unauthorized requests

---

## 🔑 AUTHENTICATION METHODS

The system supports **3 authentication methods**:

### 1️⃣ **Django Session (Browser)**
**Best for:** Manual browsing in web browser

**How to use:**
1. Login to Django admin: `http://localhost:8000/admin/`
2. Navigate to Swagger: `http://localhost:8000/swagger/`
3. ✅ Automatic access if you're staff/superuser

**Example:**
```bash
# 1. Login via browser
http://localhost:8000/admin/
# Username: admin
# Password: your_password

# 2. Open Swagger
http://localhost:8000/swagger/
# ✅ Authenticated automatically
```

---

### 2️⃣ **DRF Token Authentication**
**Best for:** API clients, scripts, automated tools

**How to use:**
```bash
# 1. Get your token from API
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}'

# Response:
{
  "access_token": "a1b2c3d4e5f6g7h8i9j0...",
  "user": {
    "is_staff": true,
    "is_superuser": true
  }
}

# 2. Use token to access Swagger
curl -H "Authorization: Token a1b2c3d4e5f6g7h8i9j0..." \
  http://localhost:8000/swagger.json
```

**In Postman:**
```
Method: GET
URL: http://localhost:8000/swagger/
Headers:
  Authorization: Token a1b2c3d4e5f6g7h8i9j0...
```

---

### 3️⃣ **Basic Authentication**
**Best for:** Simple scripts, curl commands, external tools

**How to use:**
```bash
# Direct access with username:password
curl -u admin:password http://localhost:8000/swagger.json

# Or with Authorization header
curl -H "Authorization: Basic YWRtaW46cGFzc3dvcmQ=" \
  http://localhost:8000/swagger.json
```

**In Browser:**
```
http://admin:password@localhost:8000/swagger/
```

**In Python:**
```python
import requests
from requests.auth import HTTPBasicAuth

response = requests.get(
    'http://localhost:8000/swagger.json',
    auth=HTTPBasicAuth('admin', 'password')
)
```

---

## 📝 EXAMPLES

### Example 1: Access via Browser (Django Session)

```bash
# 1. Open browser
http://localhost:8000/admin/

# 2. Login with staff/superuser account
Username: admin
Password: your_password

# 3. Navigate to Swagger
http://localhost:8000/swagger/

# ✅ You're in!
```

---

### Example 2: Access via cURL (Token Auth)

```bash
# 1. Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}' \
  | jq -r '.access_token')

# 2. Use token
curl -H "Authorization: Token $TOKEN" \
  http://localhost:8000/swagger.json
```

---

### Example 3: Access via Postman

**Method 1: Token Auth**
```
GET http://localhost:8000/swagger/
Headers:
  Authorization: Token a1b2c3d4e5f6g7h8i9j0...
```

**Method 2: Basic Auth**
```
GET http://localhost:8000/swagger/
Auth: Basic Auth
  Username: admin
  Password: your_password
```

---

### Example 4: Access via Python Script

```python
import requests

# Method 1: Token Auth
def get_swagger_with_token():
    # Login
    login_response = requests.post(
        'http://localhost:8000/api/v1/auth/login/',
        json={'email': 'admin@example.com', 'password': 'password'}
    )
    token = login_response.json()['access_token']

    # Get Swagger
    swagger_response = requests.get(
        'http://localhost:8000/swagger.json',
        headers={'Authorization': f'Token {token}'}
    )
    return swagger_response.json()

# Method 2: Basic Auth
def get_swagger_with_basic_auth():
    from requests.auth import HTTPBasicAuth

    swagger_response = requests.get(
        'http://localhost:8000/swagger.json',
        auth=HTTPBasicAuth('admin', 'password')
    )
    return swagger_response.json()
```

---

## 🚫 WHAT HAPPENS WITHOUT AUTH

### Anonymous Access:
```bash
curl http://localhost:8000/swagger/
```

**Response:**
```html
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Basic realm="Swagger API Documentation"

<h1>401 Unauthorized</h1>
<p>Access to API documentation requires authentication.</p>
<p>Please login as staff or superuser.</p>
```

### Non-Staff User:
```bash
# Login as regular patient/doctor (non-staff)
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "patient@example.com", "password": "password"}'

# Try to access Swagger with that token
curl -H "Authorization: Token <patient_token>" \
  http://localhost:8000/swagger/
```

**Response:**
```html
HTTP/1.1 401 Unauthorized

<h1>401 Unauthorized</h1>
<p>Access to API documentation requires authentication.</p>
<p>Please login as staff or superuser.</p>
```

---

## 🛠️ CREATING STAFF USERS

### Via Django Admin:
```bash
# 1. Login to admin
http://localhost:8000/admin/

# 2. Go to Users
http://localhost:8000/admin/common/user/

# 3. Edit user → Check "Staff status" → Save
```

### Via Django Shell:
```bash
python manage.py shell
```

```python
from common.models import User

# Make existing user staff
user = User.objects.get(email='doctor@example.com')
user.is_staff = True
user.save()

# Create new staff user
User.objects.create_user(
    email='staff@example.com',
    password='password123',
    first_name='Staff',
    last_name='User',
    is_staff=True
)

# Create superuser
python manage.py createsuperuser
```

---

## 🔧 CONFIGURATION

### File: `mchs_back/urls.py`

```python
from common.swagger_permissions import SwaggerAccessPermission, swagger_basic_auth_required

schema_view = get_schema_view(
    openapi.Info(
        title="ZhanCare API",
        default_version="v1",
        description="ZhanCare Medical Platform API Documentation",
    ),
    public=False,  # ✅ Requires authentication
    permission_classes=(SwaggerAccessPermission,),  # ✅ Custom permission
)

urlpatterns = [
    path("swagger/",
         swagger_basic_auth_required(schema_view.with_ui("swagger")),
         name="schema-swagger-ui"),
    # ...
]
```

### File: `common/swagger_permissions.py`

**SwaggerAccessPermission:**
- Checks if user is staff/superuser
- Supports Django session auth
- Supports DRF Token auth
- Supports Basic auth

---

## 🧪 TESTING

### Test 1: Anonymous Access (Should Fail)
```bash
curl -I http://localhost:8000/swagger/
# Expected: HTTP 401 Unauthorized
```

### Test 2: Staff Access with Token (Should Work)
```bash
# Get staff token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}' \
  | jq -r '.access_token')

# Access Swagger
curl -I -H "Authorization: Token $TOKEN" http://localhost:8000/swagger/
# Expected: HTTP 200 OK
```

### Test 3: Non-Staff Access (Should Fail)
```bash
# Get patient token (non-staff)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "patient@example.com", "password": "password"}' \
  | jq -r '.access_token')

# Try to access Swagger
curl -I -H "Authorization: Token $TOKEN" http://localhost:8000/swagger/
# Expected: HTTP 401 Unauthorized
```

---

## 🔒 SECURITY BENEFITS

### Before (Old System):
```
❌ Anyone could access documentation
❌ API endpoints visible to attackers
❌ No authentication required
❌ Security risk
```

### After (New System):
```
✅ Only staff can access documentation
✅ API structure hidden from attackers
✅ Multiple authentication methods
✅ Secure by default
```

---

## 📊 COMPARISON

| Feature | Old System | New System |
|---------|-----------|------------|
| **Access Control** | ❌ None (public) | ✅ Staff only |
| **Authentication** | ❌ None | ✅ Multiple methods |
| **Security** | ⚠️ Low | ✅ High |
| **API Exposure** | ❌ Public | ✅ Protected |
| **Best Practice** | ❌ No | ✅ Yes |

---

## 🚀 DEPLOYMENT

### Production Settings:

```python
# settings.py

# For production: disable Swagger entirely or keep protected
if not DEBUG:
    # Option 1: Disable Swagger in production
    SWAGGER_SETTINGS = {
        'SECURITY_DEFINITIONS': {
            'Token': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header'
            }
        },
        'USE_SESSION_AUTH': False,
    }

    # Option 2: Keep Swagger but only for staff
    # (Current implementation - recommended)
```

---

## 📞 TROUBLESHOOTING

### Issue 1: "401 Unauthorized" with staff account

**Solution:**
```bash
# Check if user is actually staff
python manage.py shell
```
```python
from common.models import User
user = User.objects.get(email='your@email.com')
print(f"Is staff: {user.is_staff}")
print(f"Is superuser: {user.is_superuser}")

# Make user staff if needed
user.is_staff = True
user.save()
```

### Issue 2: Token doesn't work

**Solution:**
```bash
# Verify token exists
python manage.py shell
```
```python
from rest_framework.authtoken.models import Token
token = Token.objects.get(key='your_token')
print(f"User: {token.user.email}")
print(f"Is staff: {token.user.is_staff}")
```

### Issue 3: Basic auth doesn't work

**Solution:**
- Ensure correct username format (email, not username)
- Check password is correct
- Verify user is staff

---

## 📝 SUMMARY

✅ **Swagger is now protected**
✅ **Only staff/superuser can access**
✅ **3 authentication methods supported**
✅ **Better security**
✅ **Production-ready**

---

**Last Updated:** December 5, 2025
**Status:** ✅ Active & Secure
