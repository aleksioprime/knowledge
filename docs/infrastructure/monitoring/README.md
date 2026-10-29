# Мониторинг и аналитика

Сбор метрик, логов и трассировок, визуализация и алертинг — обязательные компоненты production-сервисов.

## Содержание

- [Prometheus](prometheus/README.md) — сбор и хранение метрик (pull-модель)
- [Grafana](grafana/README.md) — визуализация метрик и дашборды
- [Централизованное логирование](logging/README.md) — Loki, Grafana Alloy, LogQL
- [Логи в ELK](logging/elk.md) — JSON-логи с `request_id`, nginx в JSON, Filebeat → Elasticsearch → Kibana, ILM, KQL
- [Sentry](sentry/README.md) — ошибки в продакшене: группировка, контекст, релизы, вырезание персональных данных в `before_send`
- [Распределённая трассировка](tracing/README.md) — OpenTelemetry, Jaeger, `traceparent`, `X-Request-Id` в логах, семплирование

Метрики, логи и Grafana подключены к учебному проекту [«Задачник»](../../practice/projects/tasker/README.md): `docker compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d`.

Трассировка разобрана на отдельном стенде: [`tracing/example`](tracing/examples/) — nginx, два сервиса на FastAPI и Jaeger. Логи в ELK — на стенде [`logging/examples/elk`](logging/examples/elk/): nginx, сервис на Flask, Filebeat, Elasticsearch и Kibana.
