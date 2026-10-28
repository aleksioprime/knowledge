# Мониторинг и аналитика

Сбор метрик, логов и трассировок, визуализация и алертинг — обязательные компоненты production-сервисов.

## Содержание

- [Prometheus](prometheus/README.md) — сбор и хранение метрик (pull-модель)
- [Grafana](grafana/README.md) — визуализация метрик и дашборды
- [Централизованное логирование](logging/README.md) — Loki, Grafana Alloy, LogQL

Всё это подключено к учебному проекту [«Задачник»](../pet/tasker/README.md): `docker compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d`.
