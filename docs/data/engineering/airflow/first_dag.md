# Airflow: первый DAG

Каждую ночь нужно забрать данные из внешнего API, посчитать статистику и положить её в базу для отчётов. Сначала хватает cron и скрипта. Потом шагов становится пять, один из них иногда падает из-за сети, а утром никто не знает, какой шаг сломался, за какой день и как его перезапустить. Airflow описывает такие цепочки на Python, сам запускает их по расписанию, повторяет упавшие шаги и показывает в интерфейсе, что и когда выполнилось.

Пример — в папке [example](examples/): Airflow 3 и PostgreSQL в Docker.

```bash
cd example
docker compose up -d
```

Интерфейс откроется на http://localhost:8080. В режиме `standalone` Airflow сам создаёт пользователя `admin` и записывает его пароль в файл внутри контейнера:

```bash
docker compose exec airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

## Минимальный пример

```python
# dags/todo_stats.py
from datetime import datetime, timedelta

import httpx
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task

API_URL = 'https://jsonplaceholder.typicode.com/todos'


@dag(
    schedule='@daily',
    start_date=datetime(2026, 10, 1),
    catchup=False,
    default_args={'retries': 3, 'retry_delay': timedelta(minutes=5)},
    tags=['учебный'],
)
def todo_stats():
    @task
    def extract() -> list[dict]:
        response = httpx.get(API_URL, timeout=10)
        response.raise_for_status()
        return response.json()

    @task
    def transform(todos: list[dict]) -> list[dict]:
        stats: dict[int, dict] = {}
        for todo in todos:
            user = stats.setdefault(todo['userId'], {'user_id': todo['userId'], 'total': 0, 'done': 0})
            user['total'] += 1
            user['done'] += todo['completed']
        return list(stats.values())

    @task
    def load(stats: list[dict], ds: str | None = None) -> int:
        hook = PostgresHook(postgres_conn_id='warehouse')
        ...  # CREATE TABLE IF NOT EXISTS и INSERT ... ON CONFLICT для каждой строки
        return len(stats)

    load(transform(extract()))


todo_stats()
```

Проверить DAG, не дожидаясь расписания:

```bash
docker compose exec airflow airflow dags test todo_stats 2026-10-28
```

```text
Done. Returned value was: [{'userId': 1, 'id': 1, 'title': 'delectus aut autem', 'completed': False}, ...
Done. Returned value was: [{'user_id': 1, 'total': 20, 'done': 11}, {'user_id': 2, 'total': 20, 'done': 8}, ...
Done. Returned value was: 10
DagRun Finished: dag_id=todo_stats, ... state=success
```

```bash
docker compose exec warehouse psql -U warehouse -c "SELECT * FROM todo_stats ORDER BY user_id LIMIT 3"
```

```text
    day     | user_id | total | done
------------+---------+-------+------
 2026-10-28 |       1 |    20 |   11
 2026-10-28 |       2 |    20 |    8
 2026-10-28 |       3 |    20 |    7
```

## Как это работает

**DAG** (Directed Acyclic Graph) — граф задач: какие шаги есть и в каком порядке их выполнять. «Ацикличный» значит, что задача не может зависеть сама от себя через цепочку других.

**Задача** (task) — один шаг. Декоратор `@task` превращает обычную функцию в задачу. Вызов `load(transform(extract()))` задаёт не выполнение, а **порядок**: сначала `extract`, его результат — в `transform`, результат `transform` — в `load`. Сами функции Airflow вызовет позже, когда придёт время.

**Планировщик** (scheduler) читает файлы из папки `dags/`, решает, какие запуски пора начать, и отдаёт задачи на выполнение. В интерфейсе видно каждый запуск, каждую задачу, её статус и логи.

**Подключения** (connections) хранят адреса и пароли внешних систем отдельно от кода. Здесь подключение задано переменной окружения:

```yaml
AIRFLOW_CONN_WAREHOUSE: postgresql://warehouse:warehouse@warehouse:5432/warehouse
```

В коде оно используется по имени: `PostgresHook(postgres_conn_id='warehouse')`. Подключения можно создавать и в интерфейсе: Admin → Connections.

**Повторы** настраиваются в `default_args`: если `extract` упадёт из-за сети, Airflow повторит его до трёх раз с паузой 5 минут, а остальные шаги подождут.

## Повторный запуск не должен ломать данные

Запуск за один и тот же день может выполниться несколько раз: после повтора, после ручного перезапуска, после исправления ошибки. Поэтому `load` пишет данные так, чтобы повтор перезаписал строки за этот день, а не добавил их ещё раз:

```sql
INSERT INTO todo_stats (day, user_id, total, done) VALUES (%s, %s, %s, %s)
ON CONFLICT (day, user_id) DO UPDATE SET total = EXCLUDED.total, done = EXCLUDED.done
```

После второго запуска за 2026-10-28 в таблице по-прежнему 10 строк. Такая **идемпотентность** — главное правило для задач Airflow.

## Частые ошибки

- **Новый DAG не запускается.** Новые DAG по умолчанию стоят на паузе (`is_paused: True`). Включите его переключателем в интерфейсе или командой `airflow dags unpause todo_stats`.
- **Тяжёлый код на верхнем уровне файла.** Планировщик перечитывает файлы DAG постоянно. Запрос к API или базе вне функции `@task` будет выполняться при каждом чтении файла. Всё тяжёлое — только внутри задач.
- **Задача, которая дописывает данные.** `INSERT` без защиты от повторов задублирует статистику при каждом перезапуске.
- **Пароль в коде DAG.** Код лежит в репозитории. Адреса и пароли — в подключениях или переменных окружения.
- **Airflow как обработчик данных.** Задачи должны управлять работой, а не перемалывать гигабайты в своём процессе. Тяжёлую обработку отдают базе, Spark или отдельному сервису, а задача только запускает её и ждёт результата.

## Связанные темы

- [XCom, расписание и запуски за прошлые даты](schedule_xcom.md)
- [HTTPX](../../../backend/microservices/httpx/basics.md)
- [Celery](../../../backend/frameworks/celery/README.md) — для фоновых задач внутри приложения, а не пайплайнов данных
