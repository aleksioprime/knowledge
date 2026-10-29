# Онлайн-кинотеатр

Бэкенд онлайн-кинотеатра из нескольких сервисов. Он нужен, чтобы увидеть вместе то, что в остальных заметках разобрано по отдельности: каталог с полнотекстовым поиском, учётные записи и роли, пользовательский контент, аналитику событий, подписки и рассылки писем. У каждого сервиса своё хранилище, а снаружи всё доступно через один nginx.

Код проекта хранится в отдельном приватном репозитории. Все сервисы поднимаются одной командой `docker compose up`. Сквозной сценарий проверяет скрипт: регистрация и вход, поиск фильма, оценка, событие просмотра в ClickHouse, оформление подписки с письмом, рассылка от администратора.

## Сервисы

| Сервис | Что делает | Стек | Хранилище |
|---|---|---|---|
| `auth` | Регистрация, вход, JWT, роли, история входов, вход через соцсети, проверка токенов для остальных сервисов | FastAPI, SQLAlchemy, Alembic, OpenTelemetry | Postgres (история входов разбита на секции), Redis |
| `admin` | Админка каталога: фильмы, жанры, персоны | Django | Postgres |
| `etl` | Переносит изменения каталога в поисковый индекс | Python | Postgres → Elasticsearch, состояние в Redis |
| `movie` | API каталога: списки, поиск, карточки с кэшем | FastAPI | Elasticsearch, Redis |
| `ugc` | Оценки, рецензии с лайками, закладки | FastAPI, motor | MongoDB |
| `events` | Приём событий просмотра и действий пользователя | FastAPI, aiokafka | Kafka |
| `events-etl` | Перекладывает события в аналитическое хранилище пачками | Python | Kafka → ClickHouse |
| `notifications-admin` | Шаблоны писем и рассылки, отложенная отправка | Django, Celery | Postgres, Redis |
| `notifications-api` | Приём уведомлений, рендер шаблона, защита от дублей | FastAPI, Jinja2 | RabbitMQ, Redis |
| `notifications-worker` | Отправка писем батчами, повторы с растущей задержкой, очередь недоставленных (DLQ) | aio-pika | RabbitMQ, SMTP |
| `subscriptions` | Тарифы, оформление, оплата (имитация), продление, отмена, покупка фильма | FastAPI, Alembic | Postgres |
| `subscriptions-worker` | Напоминания об окончании подписки, закрытие истёкших | APScheduler | — |
| `nginx` | Единая точка входа, маршрутизация по путям | nginx | — |

## Как сервисы связаны

```text
                            клиент
                              │
                            nginx
   ┌────────┬────────┬────────┼─────────┬──────────┬──────────┐
   ▼        ▼        ▼        ▼         ▼          ▼          ▼
 auth     movie     ugc    events   subscrip-  notifica-   админки
   │        │        │        │       tions    tions-api
Postgres  Elastic  MongoDB  Kafka       │          │
Redis     Redis              │      Postgres   RabbitMQ
            ▲                ▼                     │
           etl          events-etl                 ▼
            ▲                │              notifications-
            │                ▼                 worker
     Postgres каталога   ClickHouse                │
     (пишет админка)                               ▼
                                                  SMTP

 все API ──verify──▶ auth
 subscriptions ──роль subscriber──▶ auth
 subscriptions ──письма──▶ notifications-api ──получатели──▶ auth
```

Главные связи:

- **Проверка токена.** Каждый сервис отправляет токен пользователя в `auth` на ручку `verify` и получает текущие роли из базы, а не из самого токена. Если `auth` недоступен, сервисы проверяют подпись токена сами и продолжают работать (изящная деградация, graceful degradation). Каталог отвечает, даже когда `auth` остановлен.
- **Подписка → роль.** После оплаты `subscriptions` выдаёт пользователю роль `subscriber` через служебную ручку `auth`, а при отмене или истечении подписки отзывает её. Письма об оформлении и напоминания уходят через `notifications-api`.
- **Каталог → поиск.** Админка пишет в Postgres, `etl` пачками переносит изменения в Elasticsearch, `movie` ищет по индексу и кэширует ответы в Redis.
- **События → аналитика.** `events` только принимает событие и кладёт его в Kafka. `events-etl` читает топик и вставляет события в ClickHouse пачками, поэтому медленная аналитика не тормозит приём.
- **Уведомления.** API проверяет, не отправлялось ли уведомление раньше, рендерит шаблон с данными получателя из `auth` и публикует письма в RabbitMQ. Воркер отправляет их; при временной ошибке письмо возвращается в очередь с растущей задержкой, после лимита попыток — в DLQ.
- **Служебные пути** (`/internal/*`) снаружи закрыты: nginx отвечает на них 404, а сами ручки требуют внутренний ключ.

## Что упрощено

- MongoDB, ClickHouse, Kafka и Elasticsearch работают на одном узле: вся сборка из 25 контейнеров должна помещаться в 4–6 ГБ памяти Docker. Варианты с шардированным кластером MongoDB и кластером ClickHouse лежат отдельными compose-файлами.
- Оплата — имитация платёжного провайдера, без автосписаний.
- Уведомления — только email; письма перехватывает mailpit.

## Где разобраны темы

- Авторизация: [JWT в FastAPI](../../../backend/frameworks/fastapi/auth_jwt.md), [сессии и отзыв токенов](../../../backend/frameworks/fastapi/auth_sessions.md), [OAuth и OpenID Connect](../../../backend/web/security/oauth.md), [ограничение частоты запросов](../../../backend/design/rate_limiting.md), [секционирование в PostgreSQL](../../../backend/databases/postgres/partitioning.md), [трассировка](../../../infrastructure/monitoring/tracing/README.md)
- Каталог и поиск: [ETL из PostgreSQL в Elasticsearch](../../../backend/databases/elasticsearch/etl.md), [поиск в Elasticsearch](../../../backend/databases/elasticsearch/search.md), [проектирование API](../../../backend/web/http/api_design.md)
- Пользовательский контент: [MongoDB для оценок и рецензий](../../../backend/databases/mongodb/ugc.md), [шардирование MongoDB](../../../backend/databases/mongodb/sharding.md)
- Аналитика: [Kafka изнутри](../../../backend/microservices/broker/kafka/internals.md), [из Kafka в ClickHouse](../../../backend/databases/clickhouse/kafka.md), [выбор аналитического хранилища](../../../backend/databases/clickhouse/research.md)
- Уведомления: [система уведомлений](../../../backend/design/notifications.md), [надёжная доставка в RabbitMQ](../../../backend/microservices/broker/rabbitmq/reliability.md), [отправка email](../../../backend/web/email/README.md)
- Сборка: [Docker Compose](../../../infrastructure/devtools/docker/compose.md), [nginx](../../../backend/web/nginx/README.md), [требования и архитектура](../../../backend/design/requirements.md)

## Связанные темы

- [Задачник](../tasker/README.md) — небольшой проект, на котором темы базы показаны по одной
- [Pet-проекты](../README.md)
