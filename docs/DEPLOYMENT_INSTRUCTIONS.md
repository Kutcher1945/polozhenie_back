# 🚀 Telegram Bot Kubernetes Deployment - Quick Guide

## ✅ What Was Fixed

1. ✅ **Bot startup logic** - Now uses Django AppConfig instead of RUN_MAIN check
2. ✅ **Environment variables** - Bot token from env variable with fallback
3. ✅ **Production ready** - Works with both Gunicorn and runserver

## 📦 Files Updated

- `telegram_bot/apps.py` - Added bot startup in `ready()` method
- `telegram_bot/bot_instance.py` - Uses `TELEGRAM_BOT_TOKEN` env variable
- `telegram_bot/__init__.py` - Simplified (delegates to apps.py)

---

## 🔧 Deployment Steps

### Option 1: Quick Fix (Add Environment Variables)

Update your `.helm/values-main.yaml`:

```yaml
env:
  open:
    - name: TELEGRAM_BOT_ENABLED
      value: "true"
    - name: TELEGRAM_BOT_TOKEN
      value: "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw"  # Your production token
```

Then deploy:
```bash
helm upgrade --install experimental-admin .helm \
  -f .helm/values-main.yaml \
  --namespace your-namespace
```

### Option 2: Using Kubernetes Secrets (Recommended)

1. **Create secret:**
```bash
kubectl create secret generic telegram-bot-secret \
  --from-literal=bot-token='8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw' \
  -n your-namespace
```

2. **Update deployment.yaml** to use secret:
```yaml
# Add to .helm/templates/deployment.yaml under env section
- name: TELEGRAM_BOT_TOKEN
  valueFrom:
    secretKeyRef:
      name: telegram-bot-secret
      key: bot-token
- name: TELEGRAM_BOT_ENABLED
  value: "true"
```

3. **Deploy:**
```bash
helm upgrade --install experimental-admin .helm \
  -f .helm/values-main.yaml \
  --namespace your-namespace
```

---

## 🧪 Testing

### 1. Check if bot started:
```bash
# View pod logs
kubectl logs -f deployment/experimental-admin -n your-namespace | grep bot

# You should see:
# 🤖 Starting Telegram bot...
# 🚀 Starting Aiogram polling (handle_signals=False)...
# ✅ Telegram bot thread started successfully
```

### 2. Test bot in Telegram:
1. Open your bot in Telegram
2. Send `/start`
3. Should receive: "🤖 Bot is running with Django server!"

### 3. Verify environment variables:
```bash
kubectl exec -it deployment/experimental-admin -n your-namespace -- env | grep TELEGRAM
```

---

## 🛠️ For Production (Recommended)

Update your Dockerfile to use Gunicorn:

```dockerfile
FROM python:3.9

WORKDIR /app

# Install GDAL
RUN apt-get update && apt-get install -y libgdal-dev && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements
COPY requirements.txt .

# Install dependencies + gunicorn
RUN pip install -r requirements.txt gunicorn

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Use Gunicorn for production
CMD ["gunicorn", "mchs_back.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
```

Then rebuild and push:
```bash
docker build -t git-ci-cd.smartalmaty.kz:8443/opendata/experimental_admin_back:latest .
docker push git-ci-cd.smartalmaty.kz:8443/opendata/experimental_admin_back:latest
```

---

## ❓ Troubleshooting

### Bot not starting?

1. **Check logs:**
```bash
kubectl logs deployment/experimental-admin -n your-namespace | grep -i bot
```

2. **Check if telegram_bot app is in INSTALLED_APPS:**
```python
# In mchs_back/settings.py
INSTALLED_APPS = [
    # ...
    'telegram_bot',  # Must be here!
    # ...
]
```

3. **Verify token:**
```bash
# Test token with curl
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

4. **Check environment variable is set:**
```bash
kubectl exec deployment/experimental-admin -n your-namespace -- env | grep TELEGRAM_BOT_TOKEN
```

### Common Issues:

| Issue | Solution |
|-------|----------|
| "telegram_bot not in INSTALLED_APPS" | Add 'telegram_bot' to INSTALLED_APPS in settings.py |
| "Bot token invalid" | Check TELEGRAM_BOT_TOKEN env variable is correct |
| "Bot starts twice" | Normal in development (runserver auto-reload) |
| "Bot not starting" | Check TELEGRAM_BOT_ENABLED=true |

---

## 📋 Checklist

Before deploying, make sure:

- [ ] `telegram_bot` is in `INSTALLED_APPS` (settings.py)
- [ ] `TELEGRAM_BOT_TOKEN` environment variable is set
- [ ] `TELEGRAM_BOT_ENABLED=true` in deployment config
- [ ] Bot token is the **production** token (not development)
- [ ] Docker image is rebuilt and pushed
- [ ] Helm deployment is updated

---

## 🔒 Security Notes

1. **Never commit tokens to git!**
2. Use Kubernetes Secrets for production tokens
3. Rotate tokens regularly
4. Monitor bot access logs

---

## 📚 How It Works Now

```
Django Starts
    ↓
Apps Initialize
    ↓
telegram_bot/apps.py (TelegramBotConfig)
    ↓
ready() method called
    ↓
Check TELEGRAM_BOT_ENABLED
    ↓
Start bot in background thread
    ↓
Bot polls Telegram API
    ↓
✅ Bot Running!
```

**No more dependency on RUN_MAIN!** 🎉

---

## 🎯 Summary

**Before:** Bot only started with `RUN_MAIN=true` (development only)
**After:** Bot starts automatically via Django AppConfig (works everywhere!)

The bot will now start in:
- ✅ Kubernetes production (Gunicorn/uWSGI)
- ✅ Local development (`runserver`)
- ✅ Docker containers
- ✅ Any WSGI server

---

Need help? Check the full guide: `TELEGRAM_BOT_FIX.md`
