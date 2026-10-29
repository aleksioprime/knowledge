# Kafka + FastAPI: события задач

Два сервиса:

- `tasks_service` (порт 8010) — создаёт задачи и публикует события `task.created` и `task.done` в топик `task-events`;
- `analytics_service` (порт 8011) — читает события в группе потребителей `analytics` и считает статистику по пользователям.

Объяснение кода — в заметке [Kafka в FastAPI](../../fastapi.md).

```bash
docker compose -p example-kafka-fastapi up -d --build
```

```bash
curl -X POST localhost:8010/tasks -H 'Content-Type: application/json' -d '{"title": "Сдать отчёт", "owner_id": 1}'
curl -X POST localhost:8010/tasks -H 'Content-Type: application/json' -d '{"title": "Починить кран", "owner_id": 2}'
curl -X POST localhost:8010/tasks/1/done

curl localhost:8011/stats
# {"1":{"created":1,"done":1},"2":{"created":1,"done":0}}

docker compose -p example-kafka-fastapi logs analytics-service
```

Удаление:

```bash
docker compose -p example-kafka-fastapi down -v
```
