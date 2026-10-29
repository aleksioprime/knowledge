# Auth-сервис

Учебный пример к заметке [Сессии на JWT: refresh, выход, роли](../../docs/auth_sessions.md). Отдельный сервис, который регистрирует пользователей, выдаёт пару access + refresh, отзывает сессии и хранит роли. Другие сервисы «Задачника» только проверяют его токены, а [Django-админка](../../../django/docs/auth.md#вход-в-админку-через-auth-сервис) пускает пользователей через него.

## Состав

| Путь | Что внутри |
|---|---|
| `app/main.py` | сборка приложения; `lifespan` создаёт таблицы и роли |
| `app/core/security.py` | хэш паролей, выпуск и проверка access и refresh |
| `app/services/sessions.py` | refresh-сессии, ротация, denylist и версия токенов в Redis |
| `app/services/users.py` | пользователи, роли и права, история входов |
| `app/api/deps.py` | текущий пользователь и `require_permission` |
| `app/api/routers/` | `/auth/*`, назначение роли, демонстрационный `DELETE /tasks/{id}` |
| `app/cli.py` | создать пользователя с ролью из командной строки |
| `contracts/` | JSON Schema того, что потребитель (Django-админка) ждёт от `/auth/me` |
| `tests/unit/` | хранилище сессий на fakeredis |
| `tests/integration/` | сценарии через HTTP против PostgreSQL и Redis |

Таблицы создаются через `create_all` при старте, без миграций, чтобы пример оставался коротким. В рабочем сервисе схему ведут миграциями [Alembic](../../../../data/alembic/README.md), а приложение при старте таблиц не трогает. По той же причине в контейнере работает один процесс uvicorn: несколько воркеров одновременно начали бы создавать таблицы.

## Эндпоинты

| Запрос | Что делает |
|---|---|
| `POST /auth/register` | регистрация с ролью `user` |
| `POST /auth/login` | email и пароль → пара токенов, запись в историю входов |
| `POST /auth/refresh` | refresh → новая пара; старый refresh больше не работает |
| `POST /auth/logout` | закрыть текущую сессию |
| `POST /auth/logout/all` | закрыть все сессии пользователя |
| `POST /auth/password` | сменить пароль и закрыть все сессии |
| `GET /auth/me` | профиль, роли и права |
| `GET /auth/history?limit=20&offset=0` | история входов |
| `GET /auth/sessions` | активные сессии (устройства) |
| `PUT /users/{id}/roles/{role}` | назначить роль, нужно право `roles:manage` |
| `DELETE /tasks/{id}` | ничего не удаляет, нужно право `tasks:delete` |

Роли и права: `user` — `tasks:read`, `tasks:write`; `manager` — плюс `tasks:delete`; `admin` — плюс `roles:manage`.

## Запуск

```bash
cd framework/fast_api/examples/auth_service
docker compose -p kb-auth up -d --build --wait
docker compose -p kb-auth exec api python -m app.cli admin@example.com secret123 admin
# Создан пользователь 1 admin@example.com с ролью admin
```

PostgreSQL на порту `45432`, Redis — `46379`, API — `48000`, документация — http://localhost:48000/docs.

```bash
curl -s -X POST localhost:48000/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"anna@example.com","password":"secret123"}'
# {"id":2,"email":"anna@example.com","roles":["user"]}

curl -s -X POST localhost:48000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"anna@example.com","password":"secret123"}'
# {"access_token":"eyJhbGciOiJIUzI1NiIs...","refresh_token":"eyJhbGciOiJIUzI1NiIs...","token_type":"bearer"}
```

Что лежит в Redis, если один раз войти и выйти, а потом войти снова:

```bash
docker compose -p kb-auth exec redis redis-cli --scan
# denylist:6792c83e17824ed29b5c5ab970aa2b8a   ← access первой сессии, живёт до своего exp
# session:786077649a0d4ecebddb223dab1b104f    ← вторая сессия
# user:2:sessions

docker compose -p kb-auth exec redis redis-cli TTL session:786077649a0d4ecebddb223dab1b104f
# (integer) 2591999   ← 30 дней, срок жизни refresh
```

Остановить и удалить данные: `docker compose -p kb-auth down -v`.

## Тесты

Нужны запущенные PostgreSQL и Redis из `docker-compose.yml`: тесты работают с базой `auth_test` (её создаёт `docker/init-test-db.sql`) и Redis под номером 15, поэтому данные разработки не пострадают.

```bash
docker compose -p kb-auth up -d --wait postgres redis
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
# 13 passed
```

Адреса тестовых баз меняются переменными `TEST_DATABASE_URL` и `TEST_REDIS_URL`.
