# Airflow: XCom, расписание и запуски за прошлые даты

В [первом DAG](first_dag.md) данные переходили из задачи в задачу как будто сами, а каждый запуск знал, за какой день он работает. За этим стоят два механизма Airflow: **XCom** передаёт небольшие данные между задачами, а **логическая дата** привязывает запуск к периоду. Без понимания обоих легко получить пайплайн, который тормозит из-за переданного гигабайта или перезаписывает не тот день.

## Минимальный пример

```python
@task
def extract() -> list[dict]:
    return httpx.get(API_URL, timeout=10).json()


@task
def transform(todos: list[dict]) -> list[dict]:
    ...


@task
def load(stats: list[dict], ds: str | None = None) -> int:
    ...  # ds — '2026-10-28', дата этого запуска


load(transform(extract()))
```

В логах видно, как результат каждой задачи сохраняется:

```text
Done. Returned value was: [{'user_id': 1, 'total': 20, 'done': 11}, ...]
Pushing xcom   task_id='transform'
```

## XCom: как задачи передают данные

Задачи выполняются в разных процессах, а при распределённом запуске — на разных машинах. Обычной переменной между ними не передать. Когда функция `@task` возвращает значение, Airflow сохраняет его в своей базе метаданных как **XCom** (cross-communication), а следующая задача получает его оттуда.

Поэтому через XCom передают **небольшие** данные: id, пути к файлам, итоговые цифры, короткие списки. 200 задач из учебного API — нормально. Миллион строк — нет: они раздуют базу Airflow и замедлят весь планировщик. Большие данные кладут в хранилище ([S3](../../../backend/databases/s3/README.md), таблицу в базе), а через XCom передают только ссылку:

```python
@task
def extract() -> str:
    key = f'raw/todos/{datetime.now():%Y-%m-%d}.json'
    upload_to_s3(key, httpx.get(API_URL).content)
    return key  # в XCom — только путь


@task
def transform(key: str) -> str:
    todos = read_from_s3(key)
    ...
```

Значения XCom должны сериализоваться в JSON. Объект SQLAlchemy или открытый файл вернуть нельзя.

## Логическая дата и `ds`

У каждого запуска есть **логическая дата** (logical date) — за какой момент он работает. Её можно получить, добавив параметр в функцию задачи:

- `ds` — дата в виде строки `'2026-10-28'`;
- `logical_date` — то же самое как `datetime`.

Задача должна брать дату из запуска, а не вызывать `datetime.now()`. Тогда перезапуск за 15 октября через неделю отработает именно за 15 октября.

**Что изменилось в Airflow 3.** В Airflow 2 запуск по расписанию `@daily` за 28 октября стартовал **после окончания** дня, 29-го в полночь: работа «за интервал данных». В Airflow 3 по умолчанию (`create_cron_data_intervals = False`) cron-расписание запускает DAG в указанный момент, и логическая дата — это момент запуска. Старые статьи и примеры часто описывают поведение Airflow 2, поэтому проверяйте, для какой версии написан материал.

## Расписание

```python
# Варианты параметра schedule в @dag(...)
schedule = '@daily'             # каждый день в полночь
schedule = '0 6 * * 1-5'        # по будням в 6:00 (cron)
schedule = timedelta(hours=4)   # каждые 4 часа
schedule = None                 # только вручную или через API
```

Время задаётся в UTC, если не настроен часовой пояс.

**По данным, а не по времени.** В Airflow 3 DAG может запускаться, когда другой DAG обновил данные — через **Asset**:

```python
from airflow.sdk import Asset

todo_stats_table = Asset('postgres://warehouse:5432/warehouse/public/todo_stats')

# в первом DAG задача объявляет, что обновляет таблицу
@task(outlets=[todo_stats_table])
def load(stats: list[dict]) -> int: ...

# второй DAG запускается каждый раз после её обновления
@dag(schedule=[todo_stats_table], start_date=datetime(2026, 10, 1))
def weekly_report(): ...
```

## Запуски за прошлые даты

`start_date` — с какой даты DAG вообще может работать. Если `catchup=True`, при включении DAG Airflow создаст запуски за **все** пропущенные периоды от `start_date` до сегодня. С `start_date` год назад и `@daily` это 365 запусков сразу. Поэтому в примере `catchup=False`: Airflow выполнит только ближайший запуск.

Пересчитать нужный период вручную можно командой **backfill**:

```bash
airflow backfill create --dag-id todo_stats --from-date 2026-10-01 --to-date 2026-10-07
```

Полезные параметры:

- `--dry-run` — показать, какие запуски будут созданы, ничего не запуская;
- `--reprocess-behavior completed` — пересчитать и уже успешные дни (по умолчанию пропускаются);
- `--max-active-runs 2` — сколько дней обрабатывать одновременно.

Именно здесь окупается идемпотентность: пересчёт дня перезаписывает его данные, а не дублирует их.

## Частые ошибки

- **Большие данные в XCom.** Пайплайн работает на тестовых данных и умирает на настоящих. Передавайте ссылки.
- **`datetime.now()` внутри задачи.** Перезапуск за прошлый день обработает сегодняшние данные.
- **Меняющийся `start_date`.** `start_date=datetime.now()` сбивает планировщик: дата сдвигается при каждом чтении файла. Указывайте фиксированную дату.
- **`catchup=True` по умолчанию.** Включили DAG с давним `start_date` — и получили сотни запусков, которые нагрузили и Airflow, и внешний API.
- **Неполный адрес Asset.** Провайдер PostgreSQL проверяет формат: `Asset('postgres://warehouse/todo_stats')` даст ошибку импорта DAG `URI format postgres:// must contain database, schema, and table names`. Нужен полный адрес: `postgres://хост:порт/база/схема/таблица`.
- **Примеры для Airflow 2.** Импорты `from airflow.decorators import dag, task`, параметр `schedule_interval` и смысл `execution_date` изменились. В Airflow 3: `from airflow.sdk import dag, task`, `schedule` и `logical_date`.

## Связанные темы

- [Первый DAG](first_dag.md)
- [S3](../../../backend/databases/s3/README.md) — где хранить большие промежуточные данные
- [Celery: расписание](../../../backend/frameworks/celery/retries_beat_canvas.md)
