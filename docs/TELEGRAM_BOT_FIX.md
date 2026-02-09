# Telegram Bot Not Running in Kubernetes - Diagnosis & Fix

## 🔍 **Problem Analysis**

Your Telegram bot is not running in Kubernetes production because of several issues:

### **Issue 1: RUN_MAIN Environment Variable**
```python
# telegram_bot/__init__.py
if os.environ.get("RUN_MAIN") == "true":
    print("🤖 Starting Aiogram bot in background thread...")
    threading.Thread(target=start_bot, daemon=True).start()
```

**Problem**: The bot only starts when `RUN_MAIN=true`, but this environment variable is:
- ❌ NOT set in your Kubernetes deployment
- ✅ Only set by Django's `runserver` in development (auto-reload feature)

### **Issue 2: Using `runserver` in Production**
```dockerfile
# Dockerfile line 30
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**Problems**:
- ❌ `runserver` is development-only (not for production)
- ❌ Single-threaded, not scalable
- ❌ Sets `RUN_MAIN=true` only on auto-reload
- ❌ Can't handle production traffic

### **Issue 3: Bot Token Hardcoded**
```python
# telegram_bot/bot_instance.py
BOT_TOKEN = "8586849826:AAG4bdQGrXgTW7LhH5U_s2b1sx3XRug6gJQ" # DEVELOPMENT
# BOT_TOKEN = "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw" # PRODUCTION (commented)
```

**Problems**:
- ❌ Using DEVELOPMENT token in production
- ❌ Hardcoded secrets in code (security risk)
- ❌ Production token is commented out

---

## ✅ **Solution**

### **Step 1: Fix Bot Startup Logic**

**Option A: Use Django AppConfig (Recommended)**

Create: `telegram_bot/apps.py`
```python
from django.apps import AppConfig
import threading
import asyncio
import os

class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram_bot'

    def ready(self):
        """Start bot when Django is ready (production-safe)"""
        # Prevent duplicate startup in development
        if os.environ.get('RUN_MAIN') != 'true' and os.environ.get('DJANGO_SETTINGS_MODULE'):
            return

        # Only start if bot is enabled
        if os.environ.get('TELEGRAM_BOT_ENABLED', 'false').lower() == 'true':
            print("🤖 Starting Telegram bot...")
            from telegram_bot.bot_instance import run_polling

            def start_bot():
                asyncio.run(run_polling())

            bot_thread = threading.Thread(target=start_bot, daemon=True)
            bot_thread.start()
            print("✅ Telegram bot thread started")
```

Update: `telegram_bot/__init__.py`
```python
default_app_config = 'telegram_bot.apps.TelegramBotConfig'
```

**Register in settings.py:**
```python
INSTALLED_APPS = [
    # ... other apps
    'telegram_bot',  # Add this
]
```

**Option B: Use Gunicorn/Uvicorn Startup Hook**

Create: `start_bot.py` (in project root)
```python
#!/usr/bin/env python
import os
import threading
import asyncio

def on_starting(server):
    """Gunicorn hook: called before server starts"""
    if os.environ.get('TELEGRAM_BOT_ENABLED', 'false').lower() == 'true':
        print("🤖 Starting Telegram bot...")
        from telegram_bot.bot_instance import run_polling

        def start_bot():
            asyncio.run(run_polling())

        bot_thread = threading.Thread(target=start_bot, daemon=True)
        bot_thread.start()
        print("✅ Telegram bot started")
```

---

### **Step 2: Fix Production Server**

**Update Dockerfile:**
```dockerfile
FROM python:3.9

WORKDIR /app

# Install GDAL
RUN apt-get update && apt-get install -y libgdal-dev && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Install production server
RUN pip install gunicorn

# Copy project
COPY . .

# Collect static files (for production)
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Use Gunicorn for production
CMD ["gunicorn", "mchs_back.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "120"]
```

---

### **Step 3: Add Environment Variables**

**Update `.helm/templates/deployment.yaml`:**
```yaml
env:
  {{- range .Values.env.open }}
  - name: {{ .name }}
    value: {{ .value | quote }}
  {{- end }}
  # Add Telegram bot configuration
  - name: TELEGRAM_BOT_ENABLED
    value: "true"
  - name: TELEGRAM_BOT_TOKEN
    valueFrom:
      secretKeyRef:
        name: telegram-bot-secret
        key: bot-token
```

**Create Kubernetes Secret:**
```bash
kubectl create secret generic telegram-bot-secret \
  --from-literal=bot-token='8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw' \
  -n your-namespace
```

**OR add to values-main.yaml:**
```yaml
env:
  open:
    - name: TELEGRAM_BOT_ENABLED
      value: "true"
    - name: TELEGRAM_BOT_TOKEN
      value: "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw"
```

---

### **Step 4: Update Bot to Use Environment Variable**

**Update `telegram_bot/bot_instance.py`:**
```python
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

logging.basicConfig(level=logging.INFO)

# Get token from environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable not set!")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Handlers ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Open Web App",
                    web_app=WebAppInfo(url="https://www.zhan.care/telegram-auth")
                )
            ]
        ]
    )

    await message.answer(
        "🤖 Bot is running with Django server!\n\nClick below to open the web app 👇",
        reply_markup=keyboard
    )

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"You said: {message.text}")

# === Run polling safely ===
async def run_polling():
    """Start bot polling (safe for threads)."""
    try:
        print("🚀 Starting Aiogram polling...")
        await dp.start_polling(bot, handle_signals=False)
    except Exception as e:
        print(f"❌ Bot polling error: {e}")
        raise
```

---

## 📋 **Deployment Steps**

### 1. **Update Code**
```bash
# Apply all the changes above
git add .
git commit -m "Fix: Telegram bot startup in Kubernetes production"
git push
```

### 2. **Create Secret (if using secrets)**
```bash
kubectl create secret generic telegram-bot-secret \
  --from-literal=bot-token='YOUR_PRODUCTION_TOKEN' \
  -n your-namespace
```

### 3. **Update Helm Values**
```yaml
# .helm/values-main.yaml
env:
  open:
    - name: TELEGRAM_BOT_ENABLED
      value: "true"
    - name: TELEGRAM_BOT_TOKEN
      value: "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw"
```

### 4. **Deploy to Kubernetes**
```bash
# Build and push new image
docker build -t git-ci-cd.smartalmaty.kz:8443/opendata/experimental_admin_back:latest .
docker push git-ci-cd.smartalmaty.kz:8443/opendata/experimental_admin_back:latest

# Deploy with Helm
helm upgrade --install experimental-admin .helm \
  -f .helm/values-main.yaml \
  --namespace your-namespace
```

### 5. **Verify Bot is Running**
```bash
# Check pod logs
kubectl logs -f deployment/experimental-admin -n your-namespace

# You should see:
# 🤖 Starting Telegram bot...
# 🚀 Starting Aiogram polling...
# ✅ Telegram bot started
```

---

## 🧪 **Testing**

### Test Bot in Telegram:
1. Open Telegram and find your bot
2. Send `/start` command
3. You should receive the response with "Open Web App" button

### Check Logs:
```bash
# View real-time logs
kubectl logs -f <pod-name> -n your-namespace | grep bot

# Check if bot is polling
kubectl logs <pod-name> -n your-namespace | grep "polling"
```

---

## 🔒 **Security Best Practices**

1. **Never commit tokens to git**:
   ```bash
   # Add to .gitignore
   echo "*.env" >> .gitignore
   echo ".env.*" >> .gitignore
   ```

2. **Use Kubernetes Secrets** (recommended for production):
   ```yaml
   # In deployment.yaml
   - name: TELEGRAM_BOT_TOKEN
     valueFrom:
       secretKeyRef:
         name: telegram-bot-secret
         key: bot-token
   ```

3. **Rotate tokens regularly**

---

## 📊 **Monitoring**

Add health check endpoint in Django:
```python
# In urls.py
from django.http import JsonResponse

def bot_health(request):
    from telegram_bot.bot_instance import bot
    try:
        # Check if bot is responsive
        bot_info = asyncio.run(bot.get_me())
        return JsonResponse({
            'status': 'healthy',
            'bot_username': bot_info.username,
            'bot_id': bot_info.id
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)

urlpatterns = [
    path('health/bot/', bot_health),
    # ... other urls
]
```

---

## ❓ **Troubleshooting**

### Bot still not starting?

1. **Check environment variable**:
   ```bash
   kubectl exec -it <pod-name> -- env | grep TELEGRAM
   ```

2. **Check app is registered**:
   ```python
   # In settings.py
   INSTALLED_APPS = [
       # ...
       'telegram_bot',  # Must be here!
   ]
   ```

3. **Check logs for errors**:
   ```bash
   kubectl logs <pod-name> | grep -A 10 "bot"
   ```

4. **Verify token is correct**:
   ```bash
   curl -X GET "https://api.telegram.org/bot<TOKEN>/getMe"
   ```

---

## 📚 **Why This Fixes It**

| Issue | Before | After |
|-------|--------|-------|
| **Startup** | Only runs with `RUN_MAIN=true` | Runs via Django AppConfig (always) |
| **Server** | Development `runserver` | Production Gunicorn |
| **Token** | Hardcoded DEVELOPMENT token | Environment variable (PRODUCTION) |
| **Security** | Token in code | Token in Kubernetes Secret |
| **Scalability** | Single-threaded | Multi-worker (Gunicorn) |

---

## 🎯 **Quick Fix (Minimal Changes)**

If you want the quickest fix without changing much:

**Just add to `.helm/values-main.yaml`:**
```yaml
env:
  open:
    - name: RUN_MAIN
      value: "true"
    - name: TELEGRAM_BOT_TOKEN
      value: "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw"
```

**And update `bot_instance.py` to use env variable for token.**

But I **strongly recommend** using the full solution with Gunicorn for production!
