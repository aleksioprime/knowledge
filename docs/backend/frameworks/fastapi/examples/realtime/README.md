# Уведомления в реальном времени

Учебный пример к заметке [Уведомления в реальном времени: WebSocket, SSE, long polling](../../realtime.md). Сервис уведомлений «Задачника»: пользователь подключается по WebSocket или SSE и сразу видит «вам назначили задачу» и «новый комментарий». Два экземпляра приложения связаны через Redis: уведомление, отправленное на любой из них, доходит до пользователя, подключённого к другому.

## Состав

| Путь | Что внутри |
|---|---|
| `app/main.py` | сборка приложения, `lifespan` запускает подписку на Redis, `POST /notify`, `GET /debug/connections` |
| `app/ws.py` | `/ws`: проверка `Origin`, токен из адреса или первого сообщения, лимит сообщений и размера |
| `app/sse.py` | `/events` (SSE с догрузкой по `Last-Event-ID`) и `/poll` (long polling) |
| `app/manager.py` | `ConnectionManager`: соединения и очереди по `user_id` |
| `app/bus.py` | `NotificationBus`: запись в Redis Stream, рассылка через pub/sub, чтение пропущенного |
| `app/limits.py` | корзина с токенами для лимита сообщений от клиента |
| `app/auth.py` | выпуск и проверка JWT |
| `nginx/default.conf` | балансировщик перед двумя экземплярами с настройками для WebSocket и SSE |
| `docker-compose.yaml` | Redis на `46379`, `app1` на `41801`, `app2` на `41802`, nginx на `41800` |
| `tests/unit/` | тесты без Docker: `TestClient` и fakeredis |
| `tests/integration/` | проверки на запущенном стенде |
| `scripts/many_clients.py` | открыть N соединений и разослать каждому по уведомлению |

## Протокол

| Запрос | Что делает |
|---|---|
| `WS /ws?token=...&last_id=...` | поток уведомлений; без `token` ждёт первое сообщение `{"type": "auth", "token": "..."}` |
| `GET /events?token=...` | то же через SSE; заголовок `Last-Event-ID` — догрузить пропущенное |
| `GET /poll?token=...&after=...&timeout=25` | long polling: ответ с первым событием или пустой список по таймауту |
| `POST /notify` | `{"user_id": "anna", "event": "task_assigned", "data": {...}}` — сохранить и разослать |
| `GET /debug/connections` | кто подключён к этому экземпляру |

Сообщения клиента по WebSocket: `{"type": "ping"}` → `{"type": "pong"}`, `{"type": "read", "id": "..."}` → `{"type": "ack", ...}`. Больше 5 сообщений в секунду (запас — 10) или сообщение длиннее 4 КиБ — соединение закрывается с кодом 1008 или 1009.

`POST /notify` открыт без авторизации: это внутренний эндпоинт для других сервисов. В настоящей системе его закрывают сетью или сервисным токеном.

## Запуск

```bash
cd docs/backend/frameworks/fastapi/examples/realtime
docker compose -p kb-ws up -d --build --wait
```

Токен для пользователя `anna` (секрет по умолчанию из `app/config.py`):

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
TOKEN=$(.venv/bin/python -c "from app.auth import create_token; from app.config import Settings; print(create_token('anna', Settings.jwt_secret))")
```

Поток SSE с первого экземпляра и уведомление через второй:

```bash
curl -N "localhost:41801/events?token=$TOKEN"
# в другом терминале
curl -X POST localhost:41802/notify -H 'Content-Type: application/json' \
  -d '{"user_id":"anna","event":"task_assigned","data":{"task_id":42,"title":"Подготовить отчёт"}}'
```

## Тесты

```bash
.venv/bin/pytest tests/unit -v          # без Docker
.venv/bin/pytest tests/integration -v -s  # на запущенном стенде
.venv/bin/python -m scripts.many_clients 2000
```

Интеграционные тесты пропускаются, если стенд не отвечает. Адреса меняются переменными `APP1_URL`, `APP2_URL`, `PROXY_URL`.

## Остановка

```bash
docker compose -p kb-ws down -v
```
