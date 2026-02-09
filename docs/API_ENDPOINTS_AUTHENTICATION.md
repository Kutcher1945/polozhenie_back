# 🔐 API ENDPOINTS AUTHENTICATION GUIDE

## Формат токена авторизации

```
Authorization: Token <access_token>
```

**Пример:**
```bash
Authorization: Token a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

---

## 📋 ПУБЛИЧНЫЕ ЭНДПОИНТЫ (БЕЗ ТОКЕНА)

### **AUTHENTICATION** (`/api/v1/auth/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/` | Регистрация нового пользователя |
| POST | `/api/v1/auth/login/` | Вход в систему (получение токена) |
| POST | `/api/v1/auth/forgot-password/` | Запрос сброса пароля |
| POST | `/api/v1/auth/verify-reset-code/` | Проверка кода восстановления |
| POST | `/api/v1/auth/reset-password/` | Сброс пароля |
| GET | `/api/v1/auth/doctor/available/` | Список доступных врачей |
| GET | `/api/v1/auth/nurse/available/` | Список доступных медсестер |
| GET | `/api/v1/auth/profile/choices/` | Опции для профиля (выборки) |
| GET | `/api/v1/auth/csrf/` | Получение CSRF токена |

**Response (Login):**
```json
{
  "access_token": "a1b2c3d4e5f6...",
  "refresh_token": "z9y8x7w6v5u4...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "patient"
  }
}
```

---

### **CLINICS** (`/api/v1/clinics/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/clinics/` | Список всех клиник (публично) |
| GET | `/api/v1/clinics/{id}/` | Детали клиники |
| GET | `/api/v1/clinics/?search=<query>` | Поиск клиник |
| GET | `/api/v1/clinics/?lat=<lat>&lng=<lng>&radius=<km>` | Клиники рядом (GIS) |
| POST | `/api/v1/clinics/ai-search/` | AI-поиск клиник |
| GET | `/api/v1/countries/` | Список стран |
| GET | `/api/v1/regions/` | Список регионов |
| GET | `/api/v1/cities/` | Список городов |
| GET | `/api/v1/districts/` | Список районов |

**Все эндпоинты clinics ПУБЛИЧНЫЕ!** ✅

---

### **AI GAME** (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions/generate_nickname/` | Генерация никнейма |
| POST | `/api/v1/sessions/generate_question/` | Генерация вопроса |
| POST | `/api/v1/sessions/submit/` | Отправка ответа |
| GET | `/api/v1/sessions/leaderboard/` | Таблица лидеров |

**AI Game эндпоинты ПУБЛИЧНЫЕ!** ✅

---

### **CSRF** (`/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/csrf/` | Получение CSRF токена (consultations) |

---

## 🔒 ЗАЩИЩЕННЫЕ ЭНДПОИНТЫ (ТРЕБУЕТСЯ ТОКЕН)

### **USER PROFILE** (`/api/v1/auth/`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/v1/auth/profile/` | Получить свой профиль | IsAuthenticated |
| PATCH | `/api/v1/auth/profile/` | Обновить свой профиль | IsAuthenticated |
| PUT | `/api/v1/auth/profile/` | Полное обновление профиля | IsAuthenticated |
| GET | `/api/v1/auth/profile/<user_id>/` | Профиль другого пользователя | IsAuthenticated |
| PATCH | `/api/v1/auth/profile/<user_id>/` | Обновить профиль пользователя | IsAuthenticated |
| PUT | `/api/v1/auth/profile/<user_id>/` | Полное обновление пользователя | IsAuthenticated |
| POST | `/api/v1/auth/logout/` | Выход (удаление токена) | IsAuthenticated |
| POST | `/api/v1/auth/refresh/` | Обновление токена | IsAuthenticated |

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/api/v1/auth/profile/ \
  -H "Authorization: Token a1b2c3d4e5f6..."
```

---

### **AVAILABILITY STATUS** (Врачи и Медсестры)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| PATCH | `/api/v1/auth/update-availability/` | Обновить статус доступности | IsAuthenticated |
| GET | `/api/v1/auth/doctor-dashboard/` | Дашборд врача | IsDoctor |
| GET | `/api/v1/auth/admin-dashboard/` | Дашборд админа | IsAdmin |
| GET | `/api/v1/auth/nurse-dashboard/` | Дашборд медсестры | IsNurse |

---

### **CONSULTATIONS** (`/api/v1/consultations/`)

**Все эндпоинты consultations требуют токена!** 🔒

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/consultations/` | Список консультаций (свои) |
| POST | `/api/v1/consultations/` | Создать консультацию |
| GET | `/api/v1/consultations/<meeting_id>/` | Детали консультации |
| PATCH | `/api/v1/consultations/<meeting_id>/` | Обновить консультацию |
| DELETE | `/api/v1/consultations/<meeting_id>/` | Удалить консультацию |
| PATCH | `/api/v1/consultations/<meeting_id>/save-consultation-form/` | Сохранить форму консультации |
| POST | `/api/v1/consultations/<meeting_id>/generate-livekit-token/` | Получить LiveKit токен |
| POST | `/api/v1/consultations/<meeting_id>/update-status/` | Обновить статус |
| POST | `/api/v1/consultations/<meeting_id>/reject/` | Отклонить консультацию |
| POST | `/api/v1/consultations/ai-recommend/` | AI рекомендация врача |
| POST | `/api/v1/consultations/start/` | Начать видеоконсультацию |

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/api/v1/consultations/ \
  -H "Authorization: Token a1b2c3d4e5f6..."
```

---

### **CONSULTATION TIMESLOTS** (`/api/v1/consultations/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/consultations/ai-process/` | AI обработка симптомов → врач |
| POST | `/api/v1/consultations/book-scheduled/` | Забронировать плановую консультацию |
| GET | `/api/v1/consultations/timeslots/available/` | Доступные временные слоты |
| GET | `/api/v1/consultations/my-consultations/` | Мои консультации (пациент) |
| POST | `/api/v1/consultations/<id>/cancel/` | Отменить консультацию |
| POST | `/api/v1/consultations/<id>/reschedule/` | Перенести консультацию |
| GET | `/api/v1/consultations/doctor-consultations/` | Консультации врача |
| POST | `/api/v1/consultations/generate-timeslots/` | Генерация слотов (врач) |

---

### **DYNAMIC SLOTS** (`/api/v1/consultations/doctor/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/consultations/doctor/<id>/booked-slots/` | Занятые слоты врача |
| POST | `/api/v1/consultations/book-dynamic-slot/` | Забронировать динамический слот |
| GET | `/api/v1/consultations/doctor/<id>/availability/` | Правила доступности врача |

---

### **APPOINTMENTS** (`/api/v1/appointments/`)

**Все эндпоинты appointments требуют токена!** 🔒

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/appointments/` | Список вызовов на дом |
| POST | `/api/v1/appointments/` | Создать вызов на дом |
| GET | `/api/v1/appointments/<id>/` | Детали вызова |
| PATCH | `/api/v1/appointments/<id>/` | Обновить вызов |
| DELETE | `/api/v1/appointments/<id>/` | Удалить вызов |
| GET | `/api/v1/appointments/my-appointments/` | Мои вызовы (пациент) |
| GET | `/api/v1/appointments/my-nurse-appointments/` | Мои вызовы (медсестра) |
| GET | `/api/v1/appointments/nurse-available/` | Доступные медсестры |

**Пример запроса:**
```bash
curl -X GET http://localhost:8000/api/v1/appointments/ \
  -H "Authorization: Token a1b2c3d4e5f6..."
```

---

### **USER PROFILE VIEWSET** (`/api/v1/user-profile/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/user-profile/me/` | Мой расширенный профиль |
| PATCH | `/api/v1/user-profile/me/` | Обновить мой профиль |

---

### **PAYMENTS** (`/api/v1/kaspi-payments/`)

**Все эндпоинты payments требуют токена!** 🔒

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/kaspi-payments/` | Список платежей |
| POST | `/api/v1/kaspi-payments/` | Создать платеж |
| GET | `/api/v1/kaspi-payments/<id>/` | Детали платежа |

---

## 📱 FRONTEND: Какие запросы используют токен?

### ✅ Автоматически добавляется токен (через interceptor):

Файл: `src/utils/api.ts`

```typescript
axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});
```

**Все запросы через `api.*` автоматически включают токен!**

### Используемые эндпоинты на фронтенде:

**БЕЗ ТОКЕНА (Публичные):**
- `/api/v1/auth/login/` - Логин
- `/api/v1/auth/register/` - Регистрация
- `/api/v1/auth/forgot-password/` - Забыл пароль
- `/api/v1/auth/verify-reset-code/` - Проверка кода
- `/api/v1/auth/reset-password/` - Сброс пароля
- `/api/v1/clinics/` - Список клиник
- `/api/v1/clinics/ai-search/` - AI поиск клиник
- `/api/v1/sessions/generate_nickname/` - Игра (никнейм)
- `/api/v1/sessions/generate_question/` - Игра (вопрос)
- `/api/v1/sessions/submit/` - Игра (ответ)
- `/api/v1/sessions/leaderboard/` - Игра (лидеры)

**С ТОКЕНОМ (Защищенные):**
- `/api/v1/auth/profile/` - Профиль пользователя
- `/api/v1/auth/logout/` - Выход
- `/api/v1/auth/doctor/available/` - Доступные врачи
- `/api/v1/consultations/` - Консультации
- `/api/v1/consultations/<meeting_id>/` - Детали консультации
- `/api/v1/consultations/start/` - Начать консультацию
- `/api/v1/consultations/ai-recommend/` - AI рекомендация
- `/api/v1/consultations/<meeting_id>/generate-livekit-token/` - LiveKit токен
- `/api/v1/consultations/<meeting_id>/save-consultation-form/` - Сохранить форму
- `/api/v1/appointments/` - Вызовы на дом
- `/api/v1/appointments/my-appointments/` - Мои вызовы
- `/api/v1/appointments/my-nurse-appointments/` - Вызовы медсестры

---

## 🔄 TOKEN REFRESH MECHANISM

### Автоматическое обновление токена:

```typescript
// src/utils/api.ts - Response Interceptor
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refresh_token = localStorage.getItem("refresh_token");

      const { data } = await axios.post('/api/v1/auth/refresh/', {
        refresh_token
      });

      localStorage.setItem("access_token", data.access_token);
      originalRequest.headers.Authorization = `Token ${data.access_token}`;

      return axiosInstance(originalRequest);
    }
  }
);
```

**Работает автоматически при 401 ошибке!** ✅

---

## 🛡️ SECURITY BEST PRACTICES

### 1. **Хранение токенов:**
- ✅ `access_token` в `localStorage`
- ✅ `refresh_token` в `localStorage`
- ⚠️ **Альтернатива (более безопасно):** HttpOnly cookies

### 2. **Формат заголовка:**
```
Authorization: Token <access_token>
```
❌ **НЕ `Bearer`!** Это DRF Token, а не JWT!

### 3. **Время жизни токенов:**
- `access_token` - действует до явного удаления
- `refresh_token` - используется для получения нового access_token

### 4. **Logout:**
```typescript
POST /api/v1/auth/logout/
Headers: Authorization: Token <access_token>
```
- Удаляет токен из БД
- Очищает localStorage на клиенте

---

## 🧪 ТЕСТИРОВАНИЕ

### Получить токен:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

**Response:**
```json
{
  "access_token": "a1b2c3d4e5f6g7h8i9j0...",
  "refresh_token": "z9y8x7w6v5u4t3s2r1...",
  "user": { ... }
}
```

### Использовать токен:
```bash
curl -X GET http://localhost:8000/api/v1/consultations/ \
  -H "Authorization: Token a1b2c3d4e5f6g7h8i9j0..."
```

### Обновить токен:
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "z9y8x7w6v5u4t3s2r1..."}'
```

---

## 📊 СВОДКА

| Категория | Публичные | Защищенные | Всего |
|-----------|-----------|------------|-------|
| **Auth** | 8 | 12 | 20 |
| **Clinics** | 10 | 0 | 10 |
| **Consultations** | 0 | 25+ | 25+ |
| **Appointments** | 0 | 8+ | 8+ |
| **AI Game** | 4 | 0 | 4 |
| **Payments** | 0 | 3+ | 3+ |
| **ИТОГО** | ~22 | ~48 | ~70 |

---

**Последнее обновление:** 5 декабря 2025
