# Grafana

[Prometheus](../prometheus/README.md) хранит метрики и отвечает на запросы, но смотреть на систему через строку запроса неудобно. Grafana рисует по этим данным дашборды: запросы в секунду, время ответа, доля ошибок, рядом — логи из Loki. Открыли одну страницу — и видно, что происходит.

В [«Задачнике»](../../pet/tasker/README.md) Grafana запускается вместе с мониторингом и сразу показывает готовый дашборд:

```bash
docker compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d --build
```

http://localhost:3000 → Dashboards → «Задачник».

## Минимальный пример

Дашборд «Задачника» — пять панелей, и у каждой один запрос:

| Панель | Запрос |
|---|---|
| Запросы в секунду | `sum by (path) (rate(http_requests_total[1m]))` |
| Время ответа, 95-й перцентиль | `histogram_quantile(0.95, sum by (le, path) (rate(http_request_duration_seconds_bucket[1m])))` |
| Доля ошибок 5xx | `sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))` |
| Задач создано за час | `sum(increase(tasks_created_total[1h]))` |
| Логи API | `{service="app"}` — запрос к Loki |

Подпись `{{path}}` в легенде подставляет значение метки, поэтому на одном графике получается отдельная линия для каждого эндпоинта.

## Как это работает

Grafana сама ничего не хранит и не собирает. У неё есть **источники данных** (data sources) — Prometheus, Loki, PostgreSQL и другие. Каждая панель — это запрос к источнику и способ его показать: график, число, таблица, логи.

## Настройка файлами (provisioning)

Источники и дашборды можно накликать в интерфейсе, но тогда они живут только в базе Grafana и пропадут вместе с контейнером. Лучше описать их файлами, которые лежат в репозитории. При старте Grafana их подхватит сама:

```yaml
# monitoring/grafana/provisioning/datasources/datasources.yml
apiVersion: 1

datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    uid: loki
    type: loki
    url: http://loki:3100
```

```yaml
# monitoring/grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1

providers:
  - name: tasker
    folder: Задачник
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

Сам дашборд — JSON-файл [monitoring/grafana/dashboards/tasker.json](../../pet/tasker/monitoring/grafana/dashboards/tasker.json). Удобный способ получить такой JSON: собрать дашборд в интерфейсе, затем Share → Export → Save to file, и положить файл в репозиторий.

`uid` источника данных задан явно, потому что панели в JSON ссылаются на источник по `uid`. Если его не указать, Grafana придумает случайный, и импортированный дашборд не найдёт свои данные.

Проверить, что всё подключилось:

```bash
curl localhost:3000/api/datasources/uid/prometheus/health
# {"message":"Successfully queried the Prometheus API.","status":"OK"}
```

## Полезные возможности

- **Explore** — режим свободных запросов: удобно, когда разбираешься с проблемой и ещё не знаешь, какой график нужен. Можно поставить метрики и логи рядом за один и тот же отрезок времени;
- **переменные** — выпадающий список вверху дашборда (например, `$path` или `$instance`), который подставляется во все запросы. Один дашборд на все сервисы и окружения;
- **алерты** — в Grafana можно настроить правила прямо по запросам панелей и отправлять уведомления. В «Задачнике» правило живёт в Prometheus (`alerts.yml`), но для небольших систем алертов в Grafana часто хватает;
- **аннотации** — отметки на графиках: «здесь выкатили версию 1.4». Сразу видно, совпал ли рост ошибок с релизом.

## Частые ошибки

- **Анонимный вход с правами администратора.** В «Задачнике» включены `GF_AUTH_ANONYMOUS_ENABLED` и роль `Admin`, чтобы не вводить пароль на своей машине. На сервере так делать нельзя.
- **Дашборд, собранный только руками.** После пересоздания контейнера без тома его не будет. Храните JSON в репозитории.
- **`localhost` в адресе источника.** Grafana в контейнере ищет Prometheus по имени сервиса (`http://prometheus:9090`), а не по `localhost`.
- **Тяжёлые запросы на автообновлении.** Панель, которая каждые 5 секунд считает `increase(...[30d])`, нагружает Prometheus. Для долгих периодов уменьшайте частоту обновления.

## Связанные темы

- [Prometheus](../prometheus/README.md)
- [Централизованное логирование](../logging/README.md)
