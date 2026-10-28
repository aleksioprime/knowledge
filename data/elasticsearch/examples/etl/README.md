# ETL: PostgreSQL → Elasticsearch

Учебный пример к заметке [ETL из PostgreSQL в Elasticsearch](../../docs/etl.md). Скрипт забирает изменённые задачи из PostgreSQL пачками, собирает в один документ задачу вместе с её метками и загружает в индекс `tasks`. Он помнит, где остановился, переживает падение любой из баз и не запускается дважды.

## Состав

| Файл | Что внутри |
|---|---|
| `docker-compose.yml` | PostgreSQL 16 на порту `15432` и Elasticsearch 8 на порту `19200` |
| `schema.sql` | схема `content`: `task`, `tag`, `task_tag`, индексы по `(modified, id)`, 1000 тестовых задач |
| `etl.py` | сам ETL: курсоры, состояние в JSON-файле, `backoff`, `bulk`, advisory lock |

## Запуск

```bash
cd data/elasticsearch/examples/etl
docker compose up -d --wait
```

```bash
python -m venv .venv && .venv/bin/pip install "psycopg[binary]>=3.2,<4" "elasticsearch>=8,<9"
```

```bash
.venv/bin/python etl.py --once
```

Без `--once` скрипт работает в цикле и проверяет изменения каждые 10 секунд. Настройки задаются переменными окружения `PG_DSN`, `ES_URL`, `STATE_FILE`, `BATCH_SIZE`, `SLEEP_SECONDS`.

## Что попробовать

Поиск с учётом формы слова и фильтром по метке:

```bash
curl -s 'localhost:19200/tasks/_search?filter_path=hits.total.value,hits.hits._source.title' \
  -H 'Content-Type: application/json' \
  -d '{"size": 1, "query": {"bool": {"must": {"match": {"title": "отчёты"}}, "filter": {"term": {"tags": "работа"}}}}}'
# {"hits":{"total":{"value":250},"hits":[{"_source":{"title":"Подготовить отчёт №729"}}]}}
```

Переименовать метку: ETL переиндексирует все 250 задач с ней.

```bash
docker compose exec postgres psql -U app -d tasks -c "UPDATE content.tag SET name = 'офис', modified = now() WHERE name = 'работа'"
.venv/bin/python etl.py --once
```

Проверить устойчивость: остановить базу, запустить ETL и через несколько секунд вернуть базу. В логе видно, как растёт пауза между попытками, а потом загрузка продолжается.

```bash
docker compose stop postgres
.venv/bin/python etl.py --once &
sleep 5 && docker compose start postgres
```

Удалить `state.json`, чтобы загрузить всё заново. Остановить и удалить контейнеры:

```bash
docker compose down
```
