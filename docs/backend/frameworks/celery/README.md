# Celery

**Celery** — система фоновых задач для Python. Приложение ставит задачу в очередь (брокер — Redis или RabbitMQ) и сразу продолжает работу, а отдельные процессы-воркеры выполняют задачи. Есть повторы при сбоях, расписание (Celery Beat) и сборка задач в цепочки.

## Содержание

1. [Первая фоновая задача](first_task.md) — брокер, воркер, result backend, напоминания в «Задачнике», async-код внутри задачи
2. [Повторы, расписание и цепочки](retries_beat_canvas.md) — `autoretry_for` и `retry_backoff`, Celery Beat, `chain`, `group`, `chord`

## Связанные темы

- [Dramatiq](../dramatiq/README.md) — более простая альтернатива с похожими возможностями
- [Redis](../../databases/redis/README.md) — брокер в примерах
- [RabbitMQ](../../microservices/broker/rabbitmq/README.md)
- [Учебный проект «Задачник»](../../../practice/projects/tasker/README.md)
