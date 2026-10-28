# Централизованное логирование

Пока сервис один, логи можно читать через `docker compose logs`. Когда сервисов пять и каждый запущен в нескольких копиях, искать ошибку по логам отдельных контейнеров на разных машинах уже невозможно. Логи собирают в одно хранилище и ищут по ним через веб-интерфейс: «покажи все ошибки API за последние 15 минут».

Как писать логи в самом приложении — уровни, логгеры, форматы — описано в заметке [Логирование в Python](../../python/extra/logging.md).

В [«Задачнике»](../../pet/tasker/README.md) логи всех контейнеров проекта собираются в **Loki**, а смотрят их в **Grafana**:

```bash
docker compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d --build
```

## Минимальный пример

Grafana → Explore → источник Loki:

```logql
{service="app"} |= "/tasks"
```

```text
INFO:     192.168.65.1:25036 - "GET /tasks HTTP/1.1" 500 Internal Server Error
INFO:     192.168.65.1:50161 - "GET /tasks HTTP/1.1" 500 Internal Server Error
```

Сколько строк логов написал каждый сервис за 5 минут:

```logql
sum by (service) (count_over_time({service=~".+"}[5m]))
```

## Как это работает

Схема из двух частей:

- **агент** на каждой машине читает логи и отправляет их в хранилище. Здесь это **Grafana Alloy**: он подключается к Docker, находит контейнеры и читает их вывод. Раньше для этого использовали Promtail, но он больше не развивается, и Grafana рекомендует Alloy;
- **Loki** — хранилище. В отличие от Elasticsearch, Loki не индексирует текст логов целиком, а только **метки** (`service`, `container`). Поиск по тексту идёт уже внутри отобранных по меткам строк. Поэтому Loki намного легче, но запрос всегда должен начинаться с выбора меток.

```alloy
// monitoring/alloy.alloy
discovery.docker "containers" {
  host = "unix:///var/run/docker.sock"
}

discovery.relabel "containers" {
  targets = discovery.docker.containers.targets

  // Только контейнеры этого проекта, а не всё, что запущено в Docker
  rule {
    source_labels = ["__meta_docker_container_label_com_docker_compose_project"]
    regex         = sys.env("COMPOSE_PROJECT_NAME")
    action        = "keep"
  }

  // Имя сервиса из docker compose становится меткой service
  rule {
    source_labels = ["__meta_docker_container_label_com_docker_compose_service"]
    target_label  = "service"
  }
}

loki.source.docker "containers" {
  host          = "unix:///var/run/docker.sock"
  targets       = discovery.relabel.containers.output
  relabel_rules = discovery.relabel.containers.rules
  forward_to    = [loki.write.local.receiver]
}

loki.write "local" {
  endpoint {
    url = "http://loki:3100/loki/api/v1/push"
  }
}
```

Правило `keep` появилось после проверки: без него Alloy собрал логи **всех** контейнеров на машине, в том числе посторонних проектов.

## LogQL: основные запросы

```logql
{service="app"}                          # все логи API
{service=~"app|worker"}                  # API и воркер Celery
{service="app"} |= "500"                 # строки, содержащие «500»
{service="app"} != "/health"             # без проверок здоровья
{service="app"} |~ "(?i)error|exception" # регулярное выражение без учёта регистра
rate({service="app"} |= "500" [1m])      # сколько таких строк в секунду
```

Если приложение пишет логи в JSON, их можно разбирать и фильтровать по полям: `{service="app"} | json | level="ERROR"`.

## Частые ошибки

- **Высокая кардинальность меток.** id пользователя или запроса в метках Loki создают огромное количество потоков и тормозят поиск. В метках — сервис, окружение, уровень. Остальное ищется по тексту.
- **Логи без структуры.** По строке `Ошибка!` нельзя понять, у какого пользователя и в каком запросе. Пишите контекст: id задачи, id запроса, а ещё лучше — JSON.
- **Секреты в логах.** Централизованное хранилище читают многие. Пароли, токены и персональные данные не должны туда попадать.
- **Хранить всё вечно.** Логи быстро занимают место. Задайте срок хранения (retention) в Loki.

## ELK как альтернатива

**ELK** — Elasticsearch + Logstash + Kibana. Полнотекстовый поиск по любым словам в логах и сложная аналитика, но кластер Elasticsearch тяжелее в эксплуатации и требует много памяти. Подробнее о самом Elasticsearch — в заметке [Полнотекстовый поиск](../../data/elasticsearch/docs/search.md).

## Связанные темы

- [Логирование в Python](../../python/extra/logging.md)
- [Grafana](../grafana/README.md)
- [Prometheus](../prometheus/README.md)
