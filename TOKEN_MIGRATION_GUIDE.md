# Миграция с CustomToken на стандартный DRF Token

## Что изменилось?

Мы переходим с кастомной модели `CustomToken` на стандартную модель `rest_framework.authtoken.models.Token`.

### Преимущества:
✅ Меньше кастомного кода для поддержки
✅ Лучшая совместимость с DRF экосистемой
✅ Встроенная документация
✅ Автоматическая регистрация в admin

## Измененные файлы:

1. **settings.py** - Использует стандартный `TokenAuthentication`
2. **common/models.py** - CustomToken закомментирован
3. **common/views.py** - Использует `rest_framework.authtoken.models.Token`
4. **common/consumers.py** - Обновлены импорты
5. **common/admin.py** - Убрана регистрация CustomToken
6. **common/authentication.py** - Файл больше не используется (можно удалить)

## Шаги миграции:

### 1. Создать резервную копию базы данных (ВАЖНО!)

```bash
pg_dump -h 10.100.200.151 -U core -d core_db > backup_before_token_migration.sql
```

### 2. Запустить миграции Django

```bash
cd /home/adilannister/zhancare_group/experimental_admin_back
python manage.py makemigrations
python manage.py migrate
```

Это создаст стандартную таблицу `authtoken_token`.

### 3. Мигрировать существующие токены

```bash
python manage.py shell < migrate_tokens.py
```

Этот скрипт:
- Проверит наличие таблицы `common_authtoken`
- Скопирует все токены в таблицу `authtoken_token`
- Сохранит те же ключи токенов (пользователи продолжат работать без переаутентификации)

### 4. Протестировать аутентификацию

Проверьте что API работает с существующими токенами:

```bash
# Получить токен пользователя
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'

# Проверить что токен работает
curl -X GET http://localhost:8000/api/v1/user-profile/me/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### 5. Удалить старую таблицу (опционально)

После успешного тестирования можно удалить старую таблицу:

```sql
-- Подключиться к БД
python manage.py dbshell

-- Удалить таблицу
DROP TABLE IF EXISTS common_authtoken CASCADE;
```

### 6. Удалить неиспользуемые файлы (опционально)

```bash
rm /home/adilannister/zhancare_group/experimental_admin_back/common/authentication.py
```

## Откат изменений (если что-то пошло не так)

### Откат кода:

```bash
git checkout HEAD -- common/models.py common/views.py common/admin.py common/consumers.py mchs_back/settings.py
```

### Откат базы данных:

```bash
psql -h 10.100.200.151 -U core -d core_db < backup_before_token_migration.sql
```

## Проверка успешной миграции:

1. **API работает** - все эндпоинты отвечают корректно
2. **Аутентификация работает** - пользователи могут логиниться
3. **Существующие токены работают** - старые клиенты продолжают работать
4. **WebSocket работает** - соединения устанавливаются корректно

## Таблица токенов:

| До миграции | После миграции |
|-------------|----------------|
| `common_authtoken` | `authtoken_token` |
| CustomToken модель | rest_framework.authtoken.models.Token |
| custom_auth_token relation | auth_token relation |

## Поддержка:

Если возникнут проблемы:
1. Проверьте логи: `tail -f /var/log/django/error.log`
2. Проверьте миграции: `python manage.py showmigrations`
3. Откатите изменения по инструкции выше
