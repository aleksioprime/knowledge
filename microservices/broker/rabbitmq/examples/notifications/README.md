# Пример: мини-система уведомлений на RabbitMQ

Стенд к заметкам [Надёжная обработка в RabbitMQ](../../docs/reliability.md) и [Разбор: система уведомлений](../../../../../design/docs/notifications.md). «Задачник» шлёт события «задачу назначили» и «новый комментарий», сервис уведомлений превращает их в письма.

```text
источник ──POST /events──► api.py ──confirm──► notifications.events (topic)
                                                   │ *.v1.*
scheduler.py digest ──────────────────────────────►│
scheduler.py release ─────────────────────────────►▼
                                       notifications.send-email (quorum)
                                                   │
                                            worker_email.py ──SMTP──► Mailpit
                                         │            │
                         retry.1 (2 с) ◄─┤            └─► PostgreSQL: история отправок,
                         retry.2 (5 с) ◄─┤                настройки, шаблоны, запуски
                         retry.3 (10 с)◄─┤
                                 dlq   ◄─┘
```

| Файл | Что делает |
|---|---|
| `docker-compose.yaml` | RabbitMQ, PostgreSQL, Mailpit |
| `init.sql` | данные «Задачника» (схема `tasker`) и сервиса уведомлений (схема `notify`) |
| `common.py` | настройки и объявление обменника и очередей |
| `api.py` | FastAPI: проверяет контракт события и публикует его с подтверждением |
| `worker_email.py` | обогащение, проверка актуальности, отписки, тихие часы, идемпотентность, повторы, DLQ |
| `scheduler.py` | `digest` — еженедельная сводка с ключом идемпотентности; `release` — вернуть отложенные письма |
| `check.py` | прогон сценариев |

## Порты

| Сервис | Адрес |
|---|---|
| RabbitMQ AMQP | `localhost:45672`, пользователь `notify` / `notify` |
| RabbitMQ UI | <http://localhost:41567> |
| PostgreSQL | `localhost:45433`, база, пользователь и пароль `notify` |
| Mailpit SMTP | `localhost:42025` |
| Mailpit UI и API | <http://localhost:48026> |
| API уведомлений | <http://localhost:48000/docs> |

## Запуск

```shell
docker compose -p kb-notify up -d --wait

python -m venv .venv
.venv/bin/pip install -r requirements.txt

# в отдельных терминалах
.venv/bin/uvicorn api:app --port 48000
.venv/bin/python worker_email.py

# сценарии
.venv/bin/python check.py
```

Отправить событие вручную:

```shell
curl -X POST localhost:48000/events -H 'content-type: application/json' -d '{
  "event_id": "8d4c1b5e-0f7a-4c3e-9a51-2b7f0c9d1e10",
  "type": "task.assigned",
  "occurred_at": "2026-10-29T10:00:00Z",
  "data": {"task_id": 1, "assignee_id": 2, "actor_id": 1}
}'
# {"status":"accepted","event_id":"8d4c1b5e-0f7a-4c3e-9a51-2b7f0c9d1e10"}
```

Без `assignee_id` API ответит 422, при остановленном RabbitMQ — 503: источник должен повторить отправку.

Планировщик:

```shell
.venv/bin/python scheduler.py digest              # сводка за текущую ISO-неделю
.venv/bin/python scheduler.py digest --force      # ещё раз: писем не прибавится
.venv/bin/python scheduler.py release             # вернуть отложенные, у кого закончились тихие часы
```

## Что показывает `check.py`

1. Событие → письмо в Mailpit.
2. То же событие дважды → одно письмо: второе сообщение видит `status = sent` в истории.
3. Mailpit остановлен → сообщение ходит через `retry.1`, `retry.2`; после запуска Mailpit письмо доставлено. Не-JSON сразу уходит в DLQ, событие о несуществующей задаче — после четырёх попыток.
4. Вера отписана от комментариев — ей письма нет, Борису есть. Событие о закрытой задаче пропущено. У Глеба ночь — письмо отложено до 08:00 по его времени, после `release` отправлено.
5. Планировщик запущен трижды за неделю (третий раз с `--force`) → четыре дайджеста, по одному на пользователя.
6. Сообщение с ключом, на который никто не подписан, с `mandatory=True` возвращается издателю.

Полный вывод — в заметке [Надёжная обработка в RabbitMQ](../../docs/reliability.md#прогон-примера).

## Остановка

```shell
docker compose -p kb-notify down -v
```
